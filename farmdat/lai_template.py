"""
Generates LAI (Lei de Acesso à Informação - Law 12.527/2011) request templates
for municipal ITBI data. This is the most reliable and legally clean way to
obtain transaction price data for academic research.
"""
from datetime import date


LAI_TEMPLATE = """
REQUERIMENTO DE ACESSO À INFORMAÇÃO
(Lei Federal nº 12.527/2011 - Lei de Acesso à Informação)

Ao Excelentíssimo Senhor
Secretário Municipal de Fazenda e Tributação
Prefeitura Municipal de {municipio}/{uf}

Prezado Senhor,

{nome_pesquisador}, portador do CPF nº {cpf}, pesquisador vinculado ao
programa de {programa} da {universidade}, vem, respeitosamente, requerer
acesso às seguintes informações, nos termos do art. 10 da Lei nº 12.527/2011:

OBJETO DO PEDIDO:

Solicito a disponibilização de base de dados estruturada (formato CSV, XLSX
ou JSON) contendo os registros de ITBI (Imposto sobre Transmissão de Bens
Imóveis) relativos a imóveis rurais, compreendendo o período de {ano_inicio}
a {ano_fim}, com os seguintes campos:

1. Número da guia ou protocolo de pagamento
2. Data da transação (fato gerador)
3. Código do imóvel no INCRA (13 dígitos) ou Matrícula no CRI
4. Área total do imóvel em hectares
5. Valor declarado da transação (R$)
6. Valor venal de referência / VTN utilizado como base de cálculo (R$)
7. Valor do imposto recolhido (R$)
8. Tipo do transmitente (pessoa física / pessoa jurídica)
9. Tipo do adquirente (pessoa física / pessoa jurídica)
10. UF de domicílio do adquirente

ESCLARECIMENTOS:

- Não solicito dados que identifiquem individualmente as partes (CPF, CNPJ
  ou nomes), em respeito à LGPD (Lei nº 13.709/2018).
- Os dados serão utilizados exclusivamente para fins acadêmicos, conforme
  Projeto de Pesquisa aprovado pelo Comitê de Ética da {universidade}.
- Os resultados da pesquisa estarão disponíveis publicamente e poderão ser
  compartilhados com o município como contrapartida.

Requeiro resposta no prazo de 20 (vinte) dias úteis, conforme art. 11 da
Lei de Acesso à Informação.

{municipio}, {data_hoje}

Atenciosamente,

{nome_pesquisador}
{programa} — {universidade}
E-mail: {email}
Telefone: {telefone}
"""


def gerar_pedido_lai(
    municipio: str,
    uf: str,
    nome_pesquisador: str,
    cpf: str,
    universidade: str,
    programa: str,
    email: str,
    telefone: str,
    ano_inicio: int = 2015,
    ano_fim: int = None,
) -> str:
    """Generates a formatted LAI request text."""
    return LAI_TEMPLATE.format(
        municipio=municipio,
        uf=uf,
        nome_pesquisador=nome_pesquisador,
        cpf=cpf,
        universidade=universidade,
        programa=programa,
        email=email,
        telefone=telefone,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim or date.today().year,
        data_hoje=date.today().strftime("%d de %B de %Y"),
    )
