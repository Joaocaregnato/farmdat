"""
PDF parser for INCRA Atlas do Mercado de Terras.
Run locally after downloading the PDFs from:
- 2023: https://www.gov.br/incra/pt-br/centrais-de-conteudos/publicacoes/ATLAS_MERCADO_TERRAS_2023.pdf
- 2025: https://www.gov.br/incra/pt-br/centrais-de-conteudos/publicacoes/Atlas_do_Mercado_de_Terras_2025.pdf

Requires: pip install pdfplumber
"""
import re
from pathlib import Path
from typing import Optional


def parse_atlas_pdf(pdf_path: str, uf_filter: str = "MT") -> dict:
    """
    Parses an Atlas do Mercado de Terras PDF and extracts MRT data.
    Returns dict with same structure as ATLAS_DATA in atlas_data.py.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Install pdfplumber: pip install pdfplumber")

    results = {}
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}. Download from INCRA website.")

    with pdfplumber.open(pdf_path) as pdf:
        current_mrt = None
        current_uf = None

        for page in pdf.pages:
            text = page.extract_text() or ""
            tables = page.extract_tables()

            # Detect UF header
            uf_match = re.search(r'\b(MT|PA|GO|MS|BA)\b', text)
            if uf_match:
                current_uf = uf_match.group(1)

            if current_uf != uf_filter:
                continue

            # Detect MRT name
            mrt_match = re.search(r'MRT[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
            if mrt_match:
                current_mrt = mrt_match.group(1).strip()
                results[current_mrt] = {
                    "agricultura": {},
                    "pecuaria": {},
                    "vegetacao_nativa": {},
                }

            # Parse price tables
            for table in (tables or []):
                _parse_price_table(table, current_mrt, results)

    return results


def _parse_price_table(table: list, mrt_name: Optional[str], results: dict) -> None:
    """Extracts min/avg/max VTN values from a table."""
    if not mrt_name or mrt_name not in results:
        return

    uso_map = {
        "agricultura": "agricultura",
        "lavoura": "agricultura",
        "pecuária": "pecuaria",
        "pecuaria": "pecuaria",
        "pastagem": "pecuaria",
        "vegetação nativa": "vegetacao_nativa",
        "nativa": "vegetacao_nativa",
        "floresta": "vegetacao_nativa",
    }

    for row in (table or []):
        if not row:
            continue
        row_text = " ".join(str(c or "").lower() for c in row)

        uso_key = None
        for keyword, key in uso_map.items():
            if keyword in row_text:
                uso_key = key
                break

        if not uso_key:
            continue

        # Extract numeric values (R$/ha)
        nums = re.findall(r'[\d]+(?:[.,]\d+)*', row_text)
        floats = []
        for n in nums:
            try:
                floats.append(float(n.replace(".", "").replace(",", ".")))
            except ValueError:
                continue

        # Filter to plausible R$/ha range for Brazil rural land
        valid = [f for f in floats if 500 < f < 500_000]
        if len(valid) >= 3:
            results[mrt_name][uso_key] = {
                "min": min(valid[:3]),
                "avg": sorted(valid[:3])[1],
                "max": max(valid[:3]),
            }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m analysis.pdf_parser <path_to_atlas_pdf> [UF]")
        print("Example: python -m analysis.pdf_parser atlas_2025.pdf MT")
        sys.exit(1)

    pdf_file = sys.argv[1]
    uf = sys.argv[2] if len(sys.argv) > 2 else "MT"

    print(f"Parsing {pdf_file} for UF={uf} ...")
    data = parse_atlas_pdf(pdf_file, uf_filter=uf)
    print(f"Found {len(data)} MRT regions:")
    for mrt, values in data.items():
        print(f"  {mrt}: {values}")
