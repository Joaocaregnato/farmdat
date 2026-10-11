"""
Auditoria dos Excel do Atlas do Mercado de Terras (2023 / 2025) e comparação
estrutural dos clusters (MRTs) do Atlas com as regiões FNP.

Uso:
    python3 -I analysis/atlas_fnp_clusters.py ATLAS.xlsx FNP.xlsx analysis/atlas_clusters_vs_fnp.xlsx

O que ESTE script consegue fazer (só com os Excel):
  - checagens de consistência interna dos dados 2023 e 2025;
  - listar os MRTs do Atlas (código, nome, UF);
  - listar as regiões FNP com seus municípios;
  - comparar a granularidade por UF.

O que NÃO consegue: o Excel do Atlas não traz a lista de municípios de cada MRT
(ela está nos PDFs). Por isso a coluna "Municípios" dos MRTs sai como pendente.
"""
import sys

import pandas as pd

ATLAS_XLSX, FNP_XLSX, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

sheets = pd.read_excel(ATLAS_XLSX, sheet_name=None, header=1)
a23, a25 = sheets["Dados 2023 Completo"], sheets["Dados 2025 Completo"]

fnp = pd.read_excel(FNP_XLSX, sheet_name="Base")
fnp = fnp.iloc[:, :5]
fnp.columns = ["chave", "Município", "UF", "Nº Região FNP", "Região FNP"]
fnp = fnp.dropna(subset=["Município"])

UF_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}

# ---------------------------------------------------------------- Atlas 2025
a25["UF"] = a25["Código MRT"].str.extract(r"^([A-Z]{2})")[0]
a25["num"] = a25["Código MRT"].str.extract(r"-(\d+)$")[0].astype(int)
geral = a25[a25["Nível"] == 0]
mrt25 = geral[["UF", "Código MRT", "MRT Nome", "VTI (R$/ha)", "VTN (R$/ha)"]].copy()
mrt25["Nº tipologias"] = mrt25["Código MRT"].map(a25.groupby("Código MRT").size())
mrt25["Municípios"] = "PENDENTE — lista de municípios está só no PDF do Atlas"
mrt25 = mrt25.sort_values(["UF", "Código MRT"])

# ---------------------------------------------------------------------- FNP
reg = (
    fnp.groupby(["UF", "Nº Região FNP", "Região FNP"])["Município"]
    .agg(["size", lambda s: ", ".join(sorted(s))])
    .reset_index()
)
reg.columns = ["UF", "Nº Região FNP", "Região FNP", "Nº municípios", "Municípios"]
reg_multi_uf = fnp.groupby("Nº Região FNP")["UF"].nunique().gt(1).sum()

# -------------------------------------------------------- comparação por UF
cmp_ = pd.DataFrame(
    {
        "MRTs Atlas 2025": mrt25.groupby("UF").size(),
        "Regiões FNP": reg.groupby("UF").size(),
        "Municípios na base FNP": fnp.groupby("UF").size(),
    }
).fillna(0).astype(int)
cmp_["Municípios por MRT (média)"] = (cmp_["Municípios na base FNP"] / cmp_["MRTs Atlas 2025"].replace(0, float("nan"))).round(1)
cmp_["Municípios por região FNP (média)"] = (cmp_["Municípios na base FNP"] / cmp_["Regiões FNP"].replace(0, float("nan"))).round(1)
cmp_["Diferença (Atlas − FNP)"] = cmp_["MRTs Atlas 2025"] - cmp_["Regiões FNP"]
cmp_ = cmp_.reset_index().rename(columns={"index": "UF"})

# ---------------------------------------------------------- achados de 2023
a23 = a23.copy()
a23["num"] = a23["Código MRT"].astype(int)
code_state = a25.drop_duplicates("num").set_index("num")["Estado"]
chk = a23[["Estado", "num", "MRT Nome"]].drop_duplicates().rename(columns={"Estado": "Estado na planilha 2023"})
chk["Estado pelo código (2025)"] = chk["num"].map(code_state)
chk["Estado diverge?"] = (chk["Estado pelo código (2025)"].notna()) & (chk["Estado na planilha 2023"] != chk["Estado pelo código (2025)"])
chk["Nº blocos 'Geral'"] = chk["num"].map(a23[a23["Tipologia"] == "Geral"].groupby("num").size())
chk = chk.rename(columns={"num": "Código MRT"}).sort_values("Código MRT")

g25 = a25[a25["Nível"] == 0].drop_duplicates("num").set_index("num")["VTI (R$/ha)"]
g23 = a23[a23["Nível"] == 0].groupby("num")["VTI Média (R$/ha)"].apply(list)
chk["VTI Geral 2023 (cada bloco)"] = chk["Código MRT"].map(g23).map(lambda l: " | ".join(f"{v:,.0f}" for v in l) if isinstance(l, list) else "")
chk["VTI Geral 2025"] = chk["Código MRT"].map(g25)

# tipologias iguais 2023 x 2025: razão VTI
m = a23.drop_duplicates(["num", "Tipologia"]).merge(
    a25.drop_duplicates(["num", "Tipologia"]), on=["num", "Tipologia"]
)
m["razão VTI 25/23"] = (m["VTI (R$/ha)"] / m["VTI Média (R$/ha)"]).round(4)
razoes = m["razão VTI 25/23"].value_counts().head(6).rename_axis("Razão 2025/2023").reset_index(name="Nº de linhas")

# --------------------------------------------------------------- resumo
g_child = a25[a25["Nível"] == 1].groupby("Código MRT")["VTI (R$/ha)"].agg(["min", "max"])
gj = geral.set_index("Código MRT").join(g_child)
geral_fora = int(((gj["VTI (R$/ha)"] < gj["min"] - 1) | (gj["VTI (R$/ha)"] > gj["max"] + 1)).sum())

resumo = pd.DataFrame(
    [
        ("2023", "Linhas / MRTs distintos / estados", f"{len(a23)} / {a23['num'].nunique()} / {a23['Estado'].nunique()}"),
        ("2023", "MRTs com UF divergente do código", int(chk["Estado diverge?"].sum())),
        ("2023", "MRTs com 2+ blocos 'Geral' (dados de MRTs vizinhos misturados)", int((chk["Nº blocos 'Geral'"] > 1).sum())),
        ("2023", "Linhas com VTN média > VTI média", int((a23["VTN Média (R$/ha)"] > a23["VTI Média (R$/ha)"]).sum())),
        ("2023", "Linhas com média fora de [mín, máx] (VTI / VTN)",
         f"{int(((a23['VTI Média (R$/ha)'] < a23['VTI Mínimo (R$/ha)']) | (a23['VTI Média (R$/ha)'] > a23['VTI Máximo (R$/ha)'])).sum())} / "
         f"{int(((a23['VTN Média (R$/ha)'] < a23['VTN Mínimo (R$/ha)']) | (a23['VTN Média (R$/ha)'] > a23['VTN Máximo (R$/ha)'])).sum())}"),
        ("2025", "Linhas / MRTs distintos / estados", f"{len(a25)} / {a25['Código MRT'].nunique()} / {a25['UF'].nunique()}"),
        ("2025", "MRTs com exatamente 1 linha 'Geral'", int((geral.groupby('Código MRT').size() == 1).sum())),
        ("2025", "Linhas com VTN > VTI", int((a25["VTN (R$/ha)"] > a25["VTI (R$/ha)"]).sum())),
        ("2025", "Pares (MRT, tipologia) duplicados", int(a25.duplicated(["Código MRT", "Tipologia"]).sum())),
        ("2025", "MRTs cujo 'Geral' fica fora do intervalo das tipologias nível 1", geral_fora),
        ("FNP", "Municípios / regiões / UFs", f"{len(fnp)} / {fnp['Nº Região FNP'].nunique()} / {fnp['UF'].nunique()}"),
        ("FNP", "Regiões que cruzam mais de uma UF", int(reg_multi_uf)),
    ],
    columns=["Base", "Verificação", "Resultado"],
)

with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
    resumo.to_excel(xw, sheet_name="Resumo", index=False)
    mrt25.to_excel(xw, sheet_name="Atlas 2025 - clusters (MRT)", index=False)
    reg.to_excel(xw, sheet_name="FNP - regiões e municípios", index=False)
    cmp_.to_excel(xw, sheet_name="Comparação por UF", index=False)
    chk.to_excel(xw, sheet_name="Achados Atlas 2023", index=False)
    razoes.to_excel(xw, sheet_name="Razão 2025 sobre 2023", index=False)
    for ws in xw.book.worksheets:
        ws.freeze_panes = "A2"
        for col in ws.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)

print(resumo.to_string(index=False))
print(cmp_.to_string(index=False))
