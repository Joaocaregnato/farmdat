import pytest
from farmdat.processor import (
    limpar_numero_br,
    calcular_preco_ha,
    gerar_id_transacao,
    validar_e_processar_transacao,
)


class TestLimparNumeroBr:
    def test_valor_com_milhar_e_centavo(self):
        assert limpar_numero_br("24.791.250,00") == 24791250.0

    def test_valor_com_prefixo_rs(self):
        assert limpar_numero_br("R$ 24.791.250,00") == 24791250.0

    def test_area_com_ha(self):
        assert limpar_numero_br("450,7500 ha") == 450.75

    def test_valor_com_so_virgula(self):
        assert limpar_numero_br("450,75") == 450.75

    def test_valor_americano(self):
        assert limpar_numero_br("24791250.00") == 24791250.0

    def test_vazio(self):
        assert limpar_numero_br("") == 0.0

    def test_none(self):
        assert limpar_numero_br(None) == 0.0

    def test_letras_apenas(self):
        assert limpar_numero_br("N/A") == 0.0


class TestCalcularPrecoHa:
    def test_calculo_simples(self):
        assert calcular_preco_ha(24791250.0, 450.75) == pytest.approx(55005.55, rel=1e-3)

    def test_area_zero(self):
        assert calcular_preco_ha(1000000.0, 0.0) == 0.0

    def test_valor_zero(self):
        assert calcular_preco_ha(0.0, 500.0) == 0.0


class TestValidarProcessar:
    def test_transacao_valida(self):
        raw = {
            "id_guia": "ITBI-2026-88492",
            "codigo_incra": "9501140384721",
            "municipio": "Sorriso",
            "uf": "MT",
            "area_total_texto": "450,7500 ha",
            "valor_transacao_texto": "R$ 24.791.250,00",
            "valor_vtn_texto": "21.150.000,00",
            "data_transacao": "2026-04-10",
            "vendedor_tipo": "PF",
            "comprador_tipo": "PJ",
            "comprador_uf": "SP",
        }
        result = validar_e_processar_transacao(raw)
        assert result["dados_validos"] is True
        assert result["area_hectares"] == 450.75
        assert result["valor_declarado"] == 24791250.0
        assert result["preco_por_hectare"] == pytest.approx(55005.55, rel=1e-3)
        assert result["outlier_flag"] is False
        assert result["municipio"] == "Sorriso"
        assert result["data_transacao"] is not None

    def test_transacao_sem_area(self):
        raw = {"id_guia": "X", "valor_transacao_texto": "1000000", "area_total_texto": ""}
        result = validar_e_processar_transacao(raw)
        assert result["dados_validos"] is False
        assert result["preco_por_hectare"] == 0.0

    def test_outlier_preco_muito_alto(self):
        raw = {
            "id_guia": "Y",
            "area_total_texto": "1",
            "valor_transacao_texto": "999999999",
        }
        result = validar_e_processar_transacao(raw)
        assert result["outlier_flag"] is True

    def test_id_deterministico(self):
        raw = {
            "municipio": "Sorriso",
            "codigo_incra": "1234567890123",
            "data_transacao": "2024-01-01",
            "valor_transacao_texto": "1000000",
            "area_total_texto": "100",
        }
        r1 = validar_e_processar_transacao(raw)
        r2 = validar_e_processar_transacao(raw)
        assert r1["id"] == r2["id"]
