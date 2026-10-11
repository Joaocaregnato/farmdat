# Atlas do Mercado de Terras (2023/2025) × Regiões FNP — relatório parcial

> **Status:** os dois PDFs do Atlas **não estavam disponíveis** nesta sessão (não vieram
> anexados e `gov.br` está bloqueado pela política de rede do ambiente). Por isso:
> - o comando 1 (conferir Excel × PDF) **não foi feito**; só foi possível auditar a consistência
>   *interna* dos Excel;
> - o comando 2 (municípios de cada cluster do Atlas) **não pôde ser feito**: o Excel do Atlas não
>   tem municípios — a lista fica nas páginas de cada MRT dos PDFs.
>
> Tudo abaixo vem apenas dos dois Excel. Detalhes em `atlas_clusters_vs_fnp.xlsx`
> (gerado por `atlas_fnp_clusters.py`).

## 1. Auditoria interna dos Excel

### Atlas 2025 (1.954 linhas) — estruturalmente sólido
- 239 MRTs, 27 UFs, exatamente 1 linha "Geral" por MRT (bate com o título da planilha).
- Pontos a conferir no PDF: 18 linhas com **VTN > VTI** (ex.: PB-1803, GO-401 Pecuária, MS-1605
  Pecuária, SE-2304/2305 Geral) — pode ser fiel à fonte ou erro de extração; 3 pares
  (MRT, tipologia) duplicados (RS-1106 "Agrícola", DF-2808 / GO-2808) — provável perda do
  sufixo da tipologia; 38 MRTs cujo "Geral" fica fora do intervalo das tipologias de nível 1;
  outliers extremos (MG-606 Varginha "Não Agrícola" R$ 1,15 mi/ha; PI-2405 R$ 320/ha).

### Atlas 2023 (827 linhas) — **não confiável como está**
- **UF errada em 9 MRTs** (+1 interestadual ambíguo, 2802 Formoso), pelo código: 1501 Sul Amazonense (rotulado Acre; é AM), 1205
  Metropolitano (Amapá; é MA), 3001 Baixo Amazonas (Amazonas; é PA), 1905 (Ceará; é RN), 611
  Timóteo (Maranhão; é MG), 701 Vale do Paraíba (Paraíba; é RJ), 803 Mogiana (rotulado Espírito Santo; pelo código 8xx parece SP, mas o código não existe em 2025),
  e **1601 Corumbá, 1607 Paranaíba, 1613 Ivinhema rotulados como Mato Grosso — são Mato Grosso do Sul**.
  Consequência: o "Mato Grosso 2023" da planilha tem 7 MRTs, 3 deles de outro estado.
- **Blocos de MRTs vizinhos misturados**: 48 dos 51 MRTs têm 2–3 linhas "Geral". Só o 1º bloco
  casa com o MRT nomeado (razão 2025/2023 ≈ 1,28); os demais são de MRTs que ficaram sem cabeçalho
  (ex.: 1205 "Metropolitano": VTI 233 mil e 4,9 mil/ha no mesmo MRT; MT Pantanal com
  "Agricultura" a R$ 50–87 mil/ha, tipologia que nem existe no Pantanal em 2025).
  Isso é consistente com o aviso da própria planilha (só ~50 de 184 MRTs em formato tabular).
- 4 linhas com VTN média > VTI média; 1 com VTI média fora de [mín, máx]; 3 com VTN fora.
- Tipologias truncadas ("Pecuária -", "Agricultura" repetida sem subtipo).

### Achado para a comparação 2023 → 2025
Entre as 193 linhas com mesma (MRT, tipologia) nos dois anos, **100 têm razão 2025/2023 idêntica**:
×1,2836 (53), ×1,1200 (25), ×1,3124 (22). Ou seja, boa parte dos valores 2025 é o valor de 2023
**corrigido por um índice**, não preço novo de mercado. Se isso estiver igual no PDF, não use a
variação 2023→2025 desses MRTs como sinal de mercado. (Confirmar no PDF/metodologia.)

## 2. Clusters do Atlas (MRTs) × regiões FNP

**Membros dos MRTs: pendente** (depende dos PDFs). A lista de MRTs (UF, código, nome, VTI/VTN Geral)
está na aba `Atlas 2025 - clusters (MRT)`; a das regiões FNP com municípios, em
`FNP - regiões e municípios`.

O que já dá para dizer só com granularidade:

| | Atlas 2025 | FNP |
|---|---|---|
| Clusters | 239 MRTs (inclusive DF) | 133 regiões (sem DF) |
| Cobertura | 27 UFs | 26 UFs, 5.494 municípios |
| Cruza UF? | Sim — alguns MRTs (ex.: Unaí/Cristalina GO+MG, Mambaí/Formoso GO+MG, "Distrito Federal" GO+DF) | Nunca (0 regiões em 2+ UFs) |

- O Atlas é ~1,8× mais granular, mas **de forma desigual**: SC (16 vs 4), GO (18 vs 7), ES (13 vs 3),
  TO (13 vs 3), CE/PE/PI/PA (≈ 8 a mais cada). **SP é o inverso**: FNP tem 14 regiões; Atlas, 6.
  PR também (8 vs 9). **MT: 11 vs 11 e RR: 2 vs 2** — só a contagem coincide.
- Nomes não são comparáveis: Atlas-MT (Pantanal, Sudoeste, Parecis, Capital, Médio Araguaia, Sul,
  Norte Araguaia, Norte, Centro, Oeste, Noroeste) × FNP-MT (Cáceres, Cuiabá, Rondonópolis, Alto
  Araguaia, Pontes e Lacerda, Tangará da Serra, Sinop, Barra do Garças, Aripuanã, Alta Floresta, Vila Rica).
  Os recortes parecem ter lógicas diferentes (Atlas: zonas homogêneas de valor da terra/uso;
  FNP: polos/áreas de influência de cidades). Não dá para afirmar equivalência sem os municípios.
- **Resposta provisória: não misturar** os dois sistemas diretamente. A viabilidade de cruzá-los
  (ex.: mapear município → MRT e → região FNP, e medir sobreposição) só pode ser testada com a lista
  de municípios dos MRTs.

## 3. Problemas na base FNP (leves)
Grafias com erro de digitação, ex.: "AAntônio João" (MS), "CanaBrava do Norte" (MT); ao cruzar por
nome, usar a chave normalizada e checar contra o código IBGE. DF fora da base; SP com 590 municípios
(de 645).

## 4. O que falta para fechar
1. PDFs do Atlas 2023 e 2025 (anexar no chat, ou liberar `www.gov.br` na rede do ambiente).
2. Com eles: (a) conferir as linhas do Excel contra as tabelas do PDF — prioridade MT, as 18 linhas
   VTN>VTI de 2025 e os MRTs de 2023; (b) extrair "municípios por MRT"; (c) calcular sobreposição
   MRT × região FNP (% de municípios em comum, pureza, Jaccard).
