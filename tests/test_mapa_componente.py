"""O componente próprio do mapa: o que o Python promete ao JavaScript."""

from __future__ import annotations

import json

import pytest



# ---------------------------------------------------------------------------
# Valor ausente: o `NaN` que deixava o mapa parado ao escolher Cura
# ---------------------------------------------------------------------------
#
# Achado no DFTB em 08/out/2026 (`a4a2101` de lá) e trazido para cá em
# 14/out: município sem encerramento tem `cura_pct` `NaN`, e no caminho da
# geometria memoizada — toda macrorregião e região de saúde, onde não há ilha
# que o desligue — ele ia ao navegador como `NaN`, JSON inválido. O
# `JSON.parse` do componente falhava e o mapa mantinha o desenho anterior,
# enquanto a legenda (que vem do Python) trocava.


def _json_estrito(texto: str) -> dict:
    """Parse que recusa `NaN`/`Infinity` como o `JSON.parse` do navegador."""

    def recusa(constante: str):
        raise ValueError(f"não é JSON válido: {constante}")

    return json.loads(texto, parse_constant=recusa)


@pytest.mark.dado
@pytest.mark.parametrize("ano", [2023, 2024])
def test_cura_numa_macrorregiao_sai_em_json_valido(ano: int) -> None:
    """O caso real: PE sem Fernando de Noronha é o recorte de uma macrorregião
    — sem ilha, a geometria memoizada vale, e metade dos municípios não tem
    encerramento no ano."""
    from cenarios_core import mapa

    from src import doencas
    from src.data import geo, leitura
    from src.data.escopo import Escopo

    pack = doencas.carregar()
    camada = geo.municipios("PE")
    _, ilhas = mapa.limites_uteis(camada)
    camada = camada.drop(index=ilhas).reset_index(drop=True)
    valores = leitura.valores_por_geografia(Escopo("TUBERCULOSE", ano, "UF", uf="PE"), "cura_pct")
    assert valores.isna().any(), "o teste só prova algo se houver município sem taxa"

    desenho, _ = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=pack.rampa_mapa("cura_pct"),
        rotulo_metrica="Cura", coluna_nome="nome_mun",
        geometrias=mapa.geometrias_geojson(camada),
    )
    _json_estrito(desenho.to_json())


# ---------------------------------------------------------------------------
# O `deck` dos quatro painéis: notas, faixa realçada, contornos e clique
# ---------------------------------------------------------------------------
#
# 14/out/2026: o `deck` do tbpe passa a aceitar o que cada painel inventou à
# parte — `notas` do RecifeTB, `faixa_realcada` do hansepe e do DFTB, cores
# de contorno como casca e os campos do clique —, para ser o do core.


@pytest.mark.dado
def test_o_quadro_do_mapa_tem_nome_para_leitor_de_tela() -> None:
    """O Streamlit batiza o iframe com o nome interno do componente, que um
    leitor de tela anunciaria como nome de módulo. O core põe no quadro o
    `titulo` que o painel manda (desde o 0.3.0); aqui se cobra que o tbpe
    mande "Mapa de Pernambuco: <métrica>"."""
    from streamlit.testing.v1 import AppTest

    from tests.test_aplicacao import APLICACAO, LIMITE

    at = AppTest.from_file(APLICACAO, default_timeout=LIMITE).run()
    args = [json.loads(c.proto.json_args) for c in at.get("component_instance")
            if '"spec"' in c.proto.json_args]
    assert args, "o mapa não foi desenhado"
    assert args[0]["titulo"].startswith("Mapa de Pernambuco: "), args[0].get("titulo")
