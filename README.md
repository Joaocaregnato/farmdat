# FarmDat — Mato Grosso Farm Land Price Database

A Python MVP for collecting, processing, and analyzing rural farm transaction price data (R$/hectare) in Mato Grosso, Brazil.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐   │
│  │  SIGEF/  │  │  ITBI Portal │  │  LAI     │  │ CEPEA/   │   │
│  │  INCRA   │  │  (Municipal) │  │  Request │  │ IMEA     │   │
│  │  API     │  │  Scraper     │  │  Template│  │ Benchmark│   │
│  └────┬─────┘  └──────┬───────┘  └────┬─────┘  └────┬─────┘   │
└───────┼───────────────┼───────────────┼──────────────┼─────────┘
        │               │               │              │
        ▼               ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING PIPELINE                          │
│                                                                 │
│   sigef.py      scrapers/        processor.py                  │
│   (property     base.py          (clean, validate,             │
│   geometry)     (per-city)        detect outliers)             │
│        │               │               │                       │
│        └───────────────┴───────────────┘                       │
│                         │                                       │
│                    pipeline.py                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                             │
│                                                                 │
│   db.py (SQLAlchemy models)    repository.py (upserts/queries) │
│                                                                 │
│   ┌───────────┐  ┌────────────┐  ┌──────────────────────┐     │
│   │  imoveis  │  │ transacoes │  │   benchmark_precos   │     │
│   │ (SIGEF    │  │ (ITBI/LAI  │  │ (CEPEA/IMEA/FGV      │     │
│   │  parcels) │  │  records)  │  │  price benchmarks)   │     │
│   └───────────┘  └────────────┘  └──────────────────────┘     │
│                   SQLite (dev) / PostgreSQL (prod)              │
└─────────────────────────────────────────────────────────────────┘
```

## Data Sources

| Source | Type | Data | Access |
|--------|------|------|--------|
| SIGEF/INCRA | Public API | Property geometry, area, certification status | Free, no auth |
| ITBI portals | Municipal web portals | Transfer values, dates, parties | Scraping (unreliable) |
| LAI requests | Legal (Law 12.527/2011) | Full ITBI datasets | 20-day response SLA |
| CEPEA/IMEA | Public price surveys | R$/ha benchmarks by region | Public website |

## Project Structure

```
farmdat/
├── farmdat/
│   ├── db.py           — SQLAlchemy models (Imovel, Transacao, BenchmarkPreco)
│   ├── sigef.py        — SIGEF/INCRA public API integration
│   ├── processor.py    — Data cleaning, validation, outlier detection
│   ├── repository.py   — DB persistence layer (upserts, queries, stats)
│   ├── lai_template.py — LAI (freedom of information) request generator
│   ├── itbi_inspector.py — Guide to identify real ITBI portal endpoints
│   ├── pipeline.py     — Orchestration: SIGEF sync + transaction processing
│   └── scrapers/
│       ├── base.py     — Abstract scraper interface
│       └── (municipio)_scraper.py  — one per city (add as needed)
├── tests/
│   ├── test_processor.py
│   └── test_db.py
├── .env.example
└── requirements.txt
```

## Setup

```bash
# Clone and install
git clone <repo>
cd farmdat
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env as needed

# Initialize the database
python -c "from farmdat.db import init_db; init_db()"

# Run SIGEF sync for Sorriso/MT
python -m farmdat.pipeline

# Generate a LAI request
python -c "
from farmdat.lai_template import gerar_pedido_lai
print(gerar_pedido_lai(
    municipio='Sorriso', uf='MT',
    nome_pesquisador='Dr. João Silva',
    cpf='000.000.000-00',
    universidade='UFMT',
    programa='PPG Agronegócio',
    email='joao@ufmt.br',
    telefone='(65) 99999-9999',
))
"

# Inspect an ITBI portal before scraping
python -m farmdat.itbi_inspector --url https://prefsorriso-mt.agilicloud.com.br/portal/sorriso/

# Run tests
pytest tests/ -v
```

## Key Municipalities (Mato Grosso)

| Municipality | IBGE Code | Notes |
|--------------|-----------|-------|
| Sorriso | 5107925 | Largest soy producer in Brazil |
| Nova Mutum | 5106224 | Major agricultural hub |
| Sinop | 5107206 | Regional capital of northern MT |
| Tangará da Serra | 5107958 | Sugarcane + soy |
| Lucas do Rio Verde | 5105259 | High-value agricultural land |
| Campo Novo do Parecis | 5102637 | Soy belt |
| Diamantino | 5103007 | Mixed agriculture/livestock |

## Price Validation

Transactions with R$/ha outside the range **R$ 5,000 – R$ 250,000** are automatically flagged as potential outliers (configurable in `processor.py`).

## LAI Strategy

Since municipal ITBI portals are often unstable or incomplete, the recommended approach for academic research is:

1. Use `lai_template.py` to generate a formal LAI request
2. Submit via the municipality's e-SIC portal or Falabr (https://falabr.cgu.gov.br)
3. Import the received dataset via `processor.validar_e_processar_transacao()`

## License

Academic research use. Respect data provider terms of service and LGPD (Lei nº 13.709/2018).
