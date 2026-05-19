import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from farmdat.db import Base, Transacao, Imovel


@pytest.fixture
def in_memory_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_tables_created(in_memory_engine):
    table_names = in_memory_engine.dialect.get_table_names(in_memory_engine.connect())
    assert "transacoes" in table_names
    assert "imoveis" in table_names
    assert "benchmark_precos" in table_names


def test_insert_and_query_transacao(in_memory_engine):
    with Session(in_memory_engine) as session:
        t = Transacao(
            id="test-001",
            codigo_incra="9501140384721",
            municipio="Sorriso",
            uf="MT",
            area_hectares=450.75,
            valor_declarado=24791250.0,
            preco_por_hectare=55000.0,
            fonte="ITBI",
            dados_validos=True,
            outlier_flag=False,
        )
        session.add(t)
        session.commit()

        result = session.query(Transacao).filter_by(id="test-001").first()
        assert result is not None
        assert result.municipio == "Sorriso"
        assert result.preco_por_hectare == 55000.0
