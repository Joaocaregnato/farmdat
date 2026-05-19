"""
Base interface for all municipal ITBI scrapers.
Each municipality gets its own scraper that implements this interface.
"""
from abc import ABC, abstractmethod
from typing import Iterator


class BaseScraper(ABC):
    """
    Contract for all municipal scrapers.
    Implement one scraper per municipality in this directory.
    """

    municipio: str
    uf: str = "MT"
    ibge_code: str  # 7-digit IBGE municipality code

    def __init__(self, delay_seconds: float = 3.0):
        self.delay = delay_seconds

    @abstractmethod
    def iter_transacoes(self, ano_inicio: int, ano_fim: int) -> Iterator[dict]:
        """
        Yields raw transaction dicts, one per rural property transfer.
        Each dict must include at minimum:
            - area_total_texto (str)
            - valor_transacao_texto (str)
            - data_transacao (str: YYYY-MM-DD)
            - codigo_incra or matricula (str)

        The processor.validar_e_processar_transacao() function handles
        cleaning and type conversion.
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Returns True if the target portal is reachable and responding."""
        raise NotImplementedError
