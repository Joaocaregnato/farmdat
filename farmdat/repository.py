from loguru import logger
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from .db import get_session, Imovel, Transacao, BenchmarkPreco


def upsert_imovel(dados: dict) -> None:
    with get_session() as session:
        stmt = sqlite_upsert(Imovel).values(**dados)
        stmt = stmt.on_conflict_do_update(
            index_elements=["codigo_incra"],
            set_={k: v for k, v in dados.items() if k != "codigo_incra"},
        )
        session.execute(stmt)
        session.commit()


def upsert_transacao(dados: dict) -> None:
    with get_session() as session:
        stmt = sqlite_upsert(Transacao).values(**dados)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={k: v for k, v in dados.items() if k != "id"},
        )
        session.execute(stmt)
        session.commit()


def upsert_benchmark(dados: dict) -> None:
    with get_session() as session:
        obj = BenchmarkPreco(**dados)
        session.merge(obj)
        session.commit()


def listar_transacoes_validas(municipio: str = None, uf: str = "MT"):
    with get_session() as session:
        q = session.query(Transacao).filter(
            Transacao.dados_validos == True,
            Transacao.outlier_flag == False,
            Transacao.uf == uf,
        )
        if municipio:
            q = q.filter(Transacao.municipio == municipio)
        return q.all()


def estatisticas_municipio(municipio: str, uf: str = "MT") -> dict:
    """Returns summary statistics for a municipality."""
    transacoes = listar_transacoes_validas(municipio=municipio, uf=uf)
    if not transacoes:
        return {"municipio": municipio, "total": 0}

    precos = [t.preco_por_hectare for t in transacoes if t.preco_por_hectare]
    areas = [t.area_hectares for t in transacoes if t.area_hectares]

    return {
        "municipio": municipio,
        "uf": uf,
        "total_transacoes": len(transacoes),
        "preco_medio_ha": round(sum(precos) / len(precos), 2) if precos else 0,
        "preco_mediano_ha": round(sorted(precos)[len(precos) // 2], 2) if precos else 0,
        "preco_min_ha": min(precos) if precos else 0,
        "preco_max_ha": max(precos) if precos else 0,
        "area_media_ha": round(sum(areas) / len(areas), 2) if areas else 0,
        "area_total_ha": round(sum(areas), 2) if areas else 0,
    }
