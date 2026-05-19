from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.sql import func
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./farmdat.db")
engine = create_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass

class Imovel(Base):
    __tablename__ = "imoveis"

    codigo_incra = Column(String(13), primary_key=True)
    nome = Column(String(255))
    municipio = Column(String(100))
    uf = Column(String(2))
    area_hectares = Column(Float)
    status_certificacao = Column(String(50))
    geometry_wkt = Column(Text)  # WKT polygon from SIGEF
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(String(64), primary_key=True)
    codigo_incra = Column(String(13))
    municipio = Column(String(100))
    uf = Column(String(2))
    data_transacao = Column(DateTime)
    area_hectares = Column(Float)
    valor_declarado = Column(Float)      # R$
    valor_venal_vtn = Column(Float)      # R$ (prefeitura estimate)
    preco_por_hectare = Column(Float)    # R$/ha (calculated)
    fonte = Column(String(50))           # 'ITBI', 'LAI', 'CEPEA', 'IMEA'
    vendedor_tipo = Column(String(2))    # 'PF' or 'PJ'
    comprador_tipo = Column(String(2))
    comprador_uf = Column(String(2))
    tem_benfeitorias = Column(Boolean)
    texto_descricao = Column(Text)
    dados_validos = Column(Boolean, default=True)
    outlier_flag = Column(Boolean, default=False)
    raw_json = Column(Text)              # original payload stored as JSON string
    created_at = Column(DateTime, server_default=func.now())

class BenchmarkPreco(Base):
    __tablename__ = "benchmark_precos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    municipio = Column(String(100))
    uf = Column(String(2))
    ano = Column(Integer)
    trimestre = Column(Integer)          # 1-4
    preco_mediano_ha = Column(Float)     # R$/ha
    preco_minimo_ha = Column(Float)
    preco_maximo_ha = Column(Float)
    fonte = Column(String(50))           # 'CEPEA', 'IMEA', 'FGV'
    tipo_uso = Column(String(50))        # 'agricultura', 'pecuaria', 'misto'

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return Session(engine)
