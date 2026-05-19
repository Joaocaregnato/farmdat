"""
SIGEF (Sistema de Gestão Fundiária) - INCRA public data API.
Docs: https://certificacao.incra.gov.br
"""
import re
import time
import json
from typing import Optional
import requests
from loguru import logger

SIGEF_PARCELAS_URL = "https://certificacao.incra.gov.br/csv_shp/export_shp.py"
SNCI_SEARCH_URL = "https://sncr.serpro.gov.br/sncr-web/consultar/imovelPorCodigo"

HEADERS = {
    "User-Agent": "FarmDat-Research/1.0 (mestrado academico; contact: pesquisa@universidade.br)",
    "Accept": "application/json, text/plain, */*",
}


def buscar_imovel_por_codigo_incra(codigo_incra: str, session: requests.Session = None) -> Optional[dict]:
    """
    Searches for a rural property by its INCRA code (13 digits).
    Uses SIGEF public search endpoint.
    Returns a dict with property metadata or None if not found.
    """
    if not re.match(r"^\d{13}$", codigo_incra.strip()):
        logger.warning(f"Invalid INCRA code format: {codigo_incra}")
        return None

    s = session or requests.Session()
    s.headers.update(HEADERS)

    try:
        resp = s.get(
            SIGEF_PARCELAS_URL,
            params={"municipio_id": "", "codigo_imovel": codigo_incra, "tipo_municipio": ""},
            timeout=30,
        )
        resp.raise_for_status()

        # SIGEF returns CSV-like or JSON depending on accept header
        # Parse the response (adapt based on real response format)
        data = _parse_sigef_response(resp, codigo_incra)
        return data

    except requests.RequestException as e:
        logger.error(f"SIGEF request failed for {codigo_incra}: {e}")
        return None


def buscar_imoveis_por_municipio(municipio_id: str, uf: str = "MT", delay: float = 2.0) -> list[dict]:
    """
    Fetches all certified rural properties in a given municipality.
    municipio_id: IBGE 7-digit code (e.g. '5107909' for Sorriso/MT)
    """
    s = requests.Session()
    s.headers.update(HEADERS)
    results = []

    # SIGEF public export endpoint for certified parcels
    params = {
        "municipio_id": municipio_id,
        "tipo_municipio": "municipio",
        "situacao_imovel": "AT",  # AT = Ativo
    }

    logger.info(f"Fetching SIGEF data for municipio_id={municipio_id}")

    try:
        resp = s.get(SIGEF_PARCELAS_URL, params=params, timeout=60)
        resp.raise_for_status()
        results = _parse_sigef_list_response(resp)
        logger.info(f"Found {len(results)} properties in municipio {municipio_id}")
        time.sleep(delay)

    except requests.RequestException as e:
        logger.error(f"SIGEF batch request failed for municipio {municipio_id}: {e}")

    return results


def _parse_sigef_response(resp: requests.Response, codigo_incra: str) -> Optional[dict]:
    """Parse individual property response from SIGEF."""
    content_type = resp.headers.get("content-type", "")

    try:
        if "json" in content_type:
            data = resp.json()
            if isinstance(data, list) and data:
                return _normalize_sigef_record(data[0])
            if isinstance(data, dict):
                return _normalize_sigef_record(data)
        else:
            # Attempt JSON parse anyway (some endpoints return JSON with wrong content-type)
            data = resp.json()
            if isinstance(data, list) and data:
                return _normalize_sigef_record(data[0])
    except (ValueError, KeyError):
        pass

    logger.debug(f"Could not parse SIGEF response for {codigo_incra}, status={resp.status_code}")
    return None


def _parse_sigef_list_response(resp: requests.Response) -> list[dict]:
    """Parse batch property list response from SIGEF."""
    try:
        data = resp.json()
        if isinstance(data, list):
            return [_normalize_sigef_record(r) for r in data if r]
        if isinstance(data, dict) and "features" in data:
            # GeoJSON FeatureCollection
            return [_normalize_geojson_feature(f) for f in data["features"]]
    except (ValueError, KeyError):
        pass
    return []


def _normalize_sigef_record(raw: dict) -> dict:
    """Normalize a SIGEF record to our internal schema."""
    return {
        "codigo_incra": str(raw.get("codigo_imovel", raw.get("cod_imovel", ""))).strip(),
        "nome": raw.get("nome_imovel", raw.get("denominacao", "")),
        "municipio": raw.get("municipio", ""),
        "uf": raw.get("uf", raw.get("estado", "MT")),
        "area_hectares": _safe_float(raw.get("area_total", raw.get("area", 0))),
        "status_certificacao": raw.get("situacao", raw.get("status", "")),
        "geometry_wkt": raw.get("geometry_wkt", raw.get("geom", "")),
    }


def _normalize_geojson_feature(feature: dict) -> dict:
    """Normalize a GeoJSON feature from SIGEF."""
    props = feature.get("properties", {})
    geom = feature.get("geometry")
    return {
        "codigo_incra": str(props.get("codigo_imovel", "")).strip(),
        "nome": props.get("nome_imovel", ""),
        "municipio": props.get("municipio", ""),
        "uf": props.get("uf", "MT"),
        "area_hectares": _safe_float(props.get("area_total", 0)),
        "status_certificacao": props.get("situacao", ""),
        "geometry_wkt": json.dumps(geom) if geom else "",
    }


def _safe_float(val) -> float:
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0
