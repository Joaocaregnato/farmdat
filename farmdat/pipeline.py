"""
Main pipeline: fetch SIGEF property data + process transactions + persist.
"""
from loguru import logger
from .db import init_db
from .sigef import buscar_imoveis_por_municipio
from .processor import validar_e_processar_transacao
from .repository import upsert_imovel, upsert_transacao, estatisticas_municipio

# IBGE 7-digit codes for key agricultural municipalities in Mato Grosso
MUNICIPIOS_MT = {
    "Sorriso":          "5107925",
    "Nova Mutum":       "5106224",
    "Sinop":            "5107206",
    "Tangará da Serra": "5107958",
    "Diamantino":       "5103007",
    "Lucas do Rio Verde": "5105259",
    "Campo Novo do Parecis": "5102637",
}


def run_sigef_sync(municipio: str = "Sorriso", uf: str = "MT") -> int:
    """Fetches and persists SIGEF property data for a municipality."""
    ibge_code = MUNICIPIOS_MT.get(municipio)
    if not ibge_code:
        logger.error(f"Municipality not configured: {municipio}")
        return 0

    logger.info(f"Starting SIGEF sync for {municipio}/{uf} (IBGE: {ibge_code})")
    imoveis = buscar_imoveis_por_municipio(ibge_code, uf=uf)

    for imovel in imoveis:
        if imovel.get("codigo_incra"):
            upsert_imovel(imovel)

    logger.info(f"Synced {len(imoveis)} properties for {municipio}")
    return len(imoveis)


def process_and_save_transaction(dados_brutos: dict) -> bool:
    """Validates, cleans, and persists a single transaction dict."""
    processed = validar_e_processar_transacao(dados_brutos)

    if not processed["dados_validos"]:
        logger.warning(f"Skipping invalid transaction: id={processed['id']}")
        return False

    upsert_transacao(processed)
    return True


def print_stats(municipio: str = "Sorriso"):
    stats = estatisticas_municipio(municipio)
    logger.info(f"Stats for {municipio}: {stats}")
    return stats


def main():
    init_db()
    logger.info("FarmDat pipeline initialized.")

    # Sync property registry from SIGEF
    n = run_sigef_sync("Sorriso")
    logger.info(f"SIGEF sync complete: {n} properties loaded")

    # Stats
    print_stats("Sorriso")


if __name__ == "__main__":
    main()
