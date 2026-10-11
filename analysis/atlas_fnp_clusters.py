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

RELATORIO = [
    ("Status", "PDFs indisponíveis",
     "Os PDFs do Atlas 2023/2025 não estavam disponíveis (não anexados; gov.br bloqueado pela rede do ambiente). "
     "A conferência Excel x PDF NÃO foi feita e os municípios de cada MRT NÃO foram extraídos (o Excel do Atlas não os contém). "
     "Tudo abaixo vem apenas dos dois Excel."),
    ("Atlas 2025", "Estrutura", "239 MRTs, 27 UFs, 1.954 linhas, 1 linha 'Geral' por MRT: bate com o título da planilha."),
    ("Atlas 2025", "A conferir no PDF",
     "18 linhas com VTN > VTI (ex.: PB-1803, GO-401 Pecuária, MS-1605 Pecuária, SE-2304/2305 Geral); 3 pares (MRT, tipologia) duplicados "
     "(RS-1106 Agrícola, DF-2808/GO-2808); 38 MRTs com 'Geral' fora do intervalo das tipologias nível 1; "
     "outliers extremos (MG-606 Varginha Não Agrícola R$ 1,15 mi/ha; PI-2405 R$ 320/ha)."),
    ("Atlas 2023", "UF errada", "9 MRTs com UF divergente do código (+1 interestadual ambíguo, 2802 Formoso): 1501 Sul Amazonense (rotulado Acre; é AM), "
     "1205 Metropolitano (Amapá; é MA), 3001 Baixo Amazonas (Amazonas; é PA), 1905 (Ceará; é RN), 611 Timóteo (Maranhão; é MG), "
     "701 Vale do Paraíba (Paraíba; é RJ), e 1601 Corumbá, 1607 Paranaíba, 1613 Ivinhema rotulados como Mato Grosso (são MS). "
     "803 Mogiana está como Espírito Santo, mas o código 8xx parece SP (código inexistente em 2025)."),
    ("Atlas 2023", "Blocos misturados",
     "48 dos 51 MRTs têm 2-3 linhas 'Geral'. Só o 1º bloco casa com o MRT nomeado (razão 2025/2023 ~1,28); os demais parecem de MRTs vizinhos sem cabeçalho "
     "(ex.: 1205 Metropolitano com VTI 233 mil e 4,9 mil/ha; MT Pantanal com Agricultura a R$ 50-87 mil/ha). "
     "Consistente com o aviso da planilha (só ~50 de 184 MRTs em formato tabular). Os dados de MT 2023 estão contaminados."),
    ("Atlas 2023", "Outros", "4 linhas com VTN média > VTI média; 1 com VTI média fora de [mín, máx]; 3 com VTN fora; tipologias truncadas."),
    ("2023 -> 2025", "Valores indexados",
     "Em 100 de 193 linhas comparáveis a razão 2025/2023 é idêntica (x1,2836: 53; x1,1200: 25; x1,3124: 22). Parece correção por índice, "
     "não preço novo de mercado. Se confirmado no PDF, não usar essa variação como sinal de mercado nesses MRTs."),
    ("Clusters", "Granularidade",
     "Atlas 2025: 239 MRTs (inclui DF), 27 UFs. FNP: 133 regiões, 26 UFs, 5.494 municípios (sem DF). "
     "Atlas é ~1,8x mais granular, mas desigual: SC 16 x 4, GO 18 x 7, ES 13 x 3, TO 13 x 3; SP é o inverso (6 x 14); PR 8 x 9; MT 11 x 11; RR 2 x 2."),
    ("Clusters", "Divisas de UF",
     "Alguns MRTs do Atlas cruzam UFs (Unaí/Cristalina GO+MG, Mambaí/Formoso GO+MG, 'Distrito Federal' GO+DF). Regiões FNP nunca cruzam UF."),
    ("Clusters", "Nomes (exemplo MT)",
     "Atlas-MT: Pantanal, Sudoeste, Parecis, Capital, Médio Araguaia, Sul, Norte Araguaia, Norte, Centro, Oeste, Noroeste. "
     "FNP-MT: Cáceres, Cuiabá, Rondonópolis, Alto Araguaia, Pontes e Lacerda, Tangará da Serra, Sinop, Barra do Garças, Aripuanã, Alta Floresta, Vila Rica. "
     "Lógicas aparentemente diferentes (Atlas: zonas homogêneas de valor/uso; FNP: polos/áreas de influência)."),
    ("Clusters", "Conclusão provisória",
     "Não misturar os dois sistemas diretamente. A viabilidade de cruzar (município -> MRT e -> região FNP, medir sobreposição) "
     "só pode ser testada com a lista de municípios dos MRTs, que está nos PDFs."),
    ("FNP", "Qualidade da base", "Erros de grafia ('AAntônio João' MS, 'CanaBrava do Norte' MT); DF ausente; SP com 590 municípios (de 645). "
     "Cruzar por chave normalizada e validar com código IBGE."),
    ("Próximos passos", "O que falta",
     "1) PDFs do Atlas 2023 e 2025 (anexar ou liberar www.gov.br na rede). 2) Conferir Excel x PDF (prioridade MT, 18 linhas VTN>VTI de 2025, MRTs de 2023). "
     "3) Extrair municípios por MRT. 4) Calcular sobreposição MRT x região FNP (% em comum, pureza, Jaccard)."),
]
relatorio = pd.DataFrame(RELATORIO, columns=["Seção", "Tema", "Detalhe"])

with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
    relatorio.to_excel(xw, sheet_name="Relatório", index=False)
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
            ws.column_dimensions[col[0].column_letter].width = min(width + 2, 110 if ws.title == "Relatório" else 60)
        if ws.title == "Relatório":
            from openpyxl.styles import Alignment
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    c.alignment = Alignment(wrap_text=True, vertical="top")

print(resumo.to_string(index=False))
print(cmp_.to_string(index=False))
