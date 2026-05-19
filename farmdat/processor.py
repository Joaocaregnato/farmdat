"""
Cleans and validates raw ITBI/LAI transaction data before persisting.
"""
import re
import hashlib
import json
from datetime import datetime
from typing import Optional
from loguru import logger


# Rough R$/ha bounds for Mato Grosso agricultural land (2024 reference)
PRECO_MIN_HA = 5_000.0
PRECO_MAX_HA = 250_000.0


def limpar_numero_br(valor_str: Optional[str]) -> float:
    """Converts Brazilian-formatted number strings to float.
    Handles: '24.791.250,00', 'R$ 450,75', '1.200 ha', etc.
    """
    if not valor_str:
        return 0.0
    txt = str(valor_str).strip()
    txt = re.sub(r"[^\d.,-]", "", txt)
    if not txt:
        return 0.0
    # Brazilian format: dots as thousand separators, comma as decimal
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return 0.0


def calcular_preco_ha(valor_total: float, area_ha: float) -> float:
    """Safely calculates price per hectare."""
    if area_ha <= 0 or valor_total <= 0:
        return 0.0
    return round(valor_total / area_ha, 2)


def gerar_id_transacao(municipio: str, codigo_incra: str, data_str: str, valor: float) -> str:
    """Deterministic ID so re-runs don't create duplicates."""
    raw = f"{municipio}|{codigo_incra}|{data_str}|{valor}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def validar_e_processar_transacao(dados_brutos: dict) -> dict:
    """
    Takes a raw dict (from ITBI portal, LAI spreadsheet, or manual entry)
    and returns a clean, typed dict ready for DB insertion.

    Expected raw keys (all optional, best-effort parsing):
        id_guia, codigo_incra, municipio, uf,
        area_total_texto, valor_transacao_texto, valor_vtn_texto,
        data_transacao, vendedor_tipo, comprador_tipo, comprador_uf,
        tem_benfeitorias, texto_descricao
    """
    area_ha = limpar_numero_br(dados_brutos.get("area_total_texto"))
    valor_transacao = limpar_numero_br(dados_brutos.get("valor_transacao_texto"))
    valor_vtn = limpar_numero_br(dados_brutos.get("valor_vtn_texto"))
    preco_ha = calcular_preco_ha(valor_transacao, area_ha)

    municipio = dados_brutos.get("municipio", "")
    codigo_incra = str(dados_brutos.get("codigo_incra", "")).strip()
    data_str = str(dados_brutos.get("data_transacao", ""))

    transaction_id = dados_brutos.get("id_guia") or gerar_id_transacao(
        municipio, codigo_incra, data_str, valor_transacao
    )

    dados_validos = area_ha > 0 and valor_transacao > 0
    outlier = preco_ha > PRECO_MAX_HA or (preco_ha > 0 and preco_ha < PRECO_MIN_HA)

    if outlier:
        logger.warning(f"Outlier detected: id={transaction_id}, preco_ha={preco_ha:.0f}")

    # Parse date
    data_transacao = None
    if data_str:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                data_transacao = datetime.strptime(data_str.strip(), fmt)
                break
            except ValueError:
                continue

    return {
        "id": transaction_id,
        "codigo_incra": codigo_incra,
        "municipio": municipio,
        "uf": dados_brutos.get("uf", "MT"),
        "data_transacao": data_transacao,
        "area_hectares": area_ha,
        "valor_declarado": valor_transacao,
        "valor_venal_vtn": valor_vtn,
        "preco_por_hectare": preco_ha,
        "fonte": dados_brutos.get("fonte", "ITBI"),
        "vendedor_tipo": dados_brutos.get("vendedor_tipo"),
        "comprador_tipo": dados_brutos.get("comprador_tipo"),
        "comprador_uf": dados_brutos.get("comprador_uf"),
        "tem_benfeitorias": bool(dados_brutos.get("tem_benfeitorias", False)),
        "texto_descricao": dados_brutos.get("texto_descricao", ""),
        "dados_validos": dados_validos,
        "outlier_flag": outlier,
        "raw_json": json.dumps(dados_brutos, ensure_ascii=False, default=str),
    }
