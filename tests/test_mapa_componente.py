"""O componente próprio do mapa: o que o Python promete ao JavaScript."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src import mapa_componente


def test_arquivos_do_componente_existem() -> None:
    """O Streamlit serve a pasta como está: faltar um arquivo é mapa em branco."""
    for nome in ("index.html", "mapa.js", "deck.min.js", "deck-json.min.js"):
        assert (mapa_componente.DIRETORIO / nome).is_file(), nome


def test_bundle_do_deck_traz_o_que_o_js_usa() -> None:
    js = (mapa_componente.DIRETORIO / "deck.min.js").read_text(encoding="utf-8", errors="ignore")
    conv = (mapa_componente.DIRETORIO / "deck-json.min.js").read_text(encoding="utf-8", errors="ignore")
    assert "FlyToInterpolator" in js
    assert "JSONConverter" in conv and "JSONConfiguration" in conv


def test_clique_novo_devolve_chave_e_nonce() -> None:
    ev = {"nonce": "a-1", "properties": {"cod_mun6": "261160", "regiao": "Metropolitana"}}
    assert mapa_componente.alvo_do_clique(ev, None) == ("261160", "a-1")
    assert mapa_componente.alvo_do_clique({"nonce": "a-2", "properties": {"regiao": "Agreste"}}, "a-1") == ("Agreste", "a-2")


def test_clique_ja_tratado_nao_navega_de_novo() -> None:
    """O valor do componente persiste entre reruns; sem o nonce, todo rerun
    repetiria a última navegação."""
    ev = {"nonce": "a-1", "properties": {"cod_mun6": "261160"}}
    assert mapa_componente.alvo_do_clique(ev, "a-1") == (None, None)


def test_evento_estranho_nao_derruba() -> None:
    assert mapa_componente.alvo_do_clique(None, None) == (None, None)
    assert mapa_componente.alvo_do_clique({"nonce": "x"}, None) == (None, "x")
    assert mapa_componente.alvo_do_clique({"nonce": "x", "properties": {}}, None) == (None, "x")


def test_camada_de_geografia_tem_id_fixo_e_transicao() -> None:
    """Sem `id` estável o deck.gl não interpola a cor entre reruns."""
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import box

    from src import doencas, mapa

    pack = doencas.carregar()
    dados = gpd.GeoDataFrame(
        {"cod_mun6": ["1", "2"], "nome_mun": ["A", "B"]},
        geometry=[box(-36, -9, -35, -8), box(-35, -9, -34, -8)],
        crs="EPSG:4326",
    )
    desenho, _ = mapa.deck(
        dados, pd.Series([1.0, 2.0], index=["1", "2"]), chave="cod_mun6",
        rampa=pack.rampa_mapa("incid"), rotulo_metrica="x", coluna_nome="nome_mun",
    )
    spec = json.loads(desenho.to_json())
    geo = next(c for c in spec["layers"] if c["@@type"] == "GeoJsonLayer")
    assert geo["id"] == "geografia"
    assert geo["transitions"] == {"getFillColor": mapa.TRANSICAO_COR_MS}


def test_scripts_dos_componentes_levam_a_versao_no_nome() -> None:
    """O Streamlit serve `.js` com `Cache-Control: public` e só o `index.html`
    com `no-cache`. Sem o `?v=<hash>` no `src`, quem já abriu o painel uma
    vez continua com o JavaScript antigo — foi assim que a correção do clique
    duplo "não resolveu": o navegador nunca a baixou. O hash tem de ser o do
    arquivo atual; mudou o JS, muda o carimbo (`scripts/versionar_js.py`)."""
    import hashlib
    import re

    from src import grafico_componente, mapa_componente

    for pasta in (mapa_componente.DIRETORIO, grafico_componente.DIRETORIO):
        html = (pasta / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r'<script src="([^"?]+)\?v=([0-9a-f]{8})"></script>', html)
        assert scripts, f"{pasta.name}: script sem ?v="
        for nome, versao in scripts:
            esperado = hashlib.sha1((pasta / nome).read_bytes()).hexdigest()[:8]
            assert versao == esperado, f"{pasta.name}/{nome}: carimbo {versao} != {esperado} — rode scripts/versionar_js.py"


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


def _dois_municipios():
    import geopandas as gpd
    from shapely.geometry import box

    return gpd.GeoDataFrame(
        {"cod_mun6": ["1", "2", "3"], "nome_mun": ["A", "B", "C"]},
        geometry=[box(-36, -9, -35, -8), box(-35, -9, -34, -8), box(-34, -9, -33, -8)],
        crs="EPSG:4326",
    )


def _deck(camada, valores, **extra):
    import pandas as pd

    from src import doencas, mapa

    pack = doencas.carregar()
    return mapa.deck(
        camada, pd.Series(valores, index=["1", "2", "3"]), chave="cod_mun6",
        rampa=pack.rampa_mapa("cura_pct"), rotulo_metrica="x", coluna_nome="nome_mun",
        **extra,
    )


@pytest.mark.parametrize("memoizada", [False, True])
def test_valor_ausente_vira_null_e_o_json_e_valido(memoizada: bool) -> None:
    from src import mapa

    camada = _dois_municipios()
    extra = {"geometrias": mapa.geometrias_geojson(camada)} if memoizada else {}
    desenho, _ = _deck(camada, [1.0, float("nan"), 3.0], **extra)

    spec = _json_estrito(desenho.to_json())
    feicoes = next(c for c in spec["layers"] if c.get("id") == "geografia")["data"]["features"]
    por_mun = {f["properties"]["cod_mun6"]: f["properties"] for f in feicoes}
    assert por_mun["2"]["valor"] is None
    assert por_mun["1"]["valor"] == 1.0
    assert por_mun["2"]["classe"] == mapa.ROTULO_SEM_DADO
    assert por_mun["2"]["exibicao"] == "—"


def test_todos_sem_valor_tambem_nao_quebra() -> None:
    from src import mapa

    camada = _dois_municipios()
    desenho, escala = _deck(
        camada, [float("nan")] * 3, geometrias=mapa.geometrias_geojson(camada)
    )
    _json_estrito(desenho.to_json())
    assert not escala.rotulos


def test_a_serializacao_compacta_nao_engole_dado_invalido() -> None:
    """O `except Exception` de `_compactar` escondia justamente o `NaN`: o
    pydeck caía no `to_json` padrão, que o aceita, e o erro só aparecia no
    navegador. Dado inválido tem de estourar onde dá para ver."""
    import pydeck

    from src import mapa

    deck = pydeck.Deck(
        layers=[pydeck.Layer("GeoJsonLayer", data={"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": None, "properties": {"valor": float("nan")}}]})],
    )
    with pytest.raises(ValueError):
        mapa._compactar(deck)


@pytest.mark.dado
@pytest.mark.parametrize("ano", [2023, 2024])
def test_cura_numa_macrorregiao_sai_em_json_valido(ano: int) -> None:
    """O caso real: PE sem Fernando de Noronha é o recorte de uma macrorregião
    — sem ilha, a geometria memoizada vale, e metade dos municípios não tem
    encerramento no ano."""
    from src import doencas, mapa
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


def _feicoes(desenho) -> dict:
    spec = _json_estrito(desenho.to_json())
    geo = next(c for c in spec["layers"] if c.get("id") == "geografia")
    return geo, {f["properties"]["cod_mun6"]: f["properties"] for f in geo["data"]["features"]}


def test_o_padrao_mantem_a_divisa_de_sempre() -> None:
    """Sem `contornos`, o tbpe desenha como antes: divisa branca translúcida
    em toda feição, inclusive a sem dado, na espessura de sempre."""
    from src import mapa

    geo, props = _feicoes(_deck(_dois_municipios(), [1.0, float("nan"), 3.0])[0])
    assert {tuple(p["contorno"]) for p in props.values()} == {(255, 255, 255, 150)}
    assert geo["lineWidthMinPixels"] == mapa.Contornos().largura
    assert geo["getLineColor"] == "@@=properties.contorno"


def test_contorno_proprio_para_sem_dado() -> None:
    from src import mapa

    escuro = (71, 78, 92, 255)
    _, props = _feicoes(_deck(
        _dois_municipios(), [1.0, float("nan"), 3.0],
        contornos=mapa.Contornos(sem_dado=escuro),
    )[0])
    assert tuple(props["2"]["contorno"]) == escuro
    assert tuple(props["1"]["contorno"]) == mapa.Contornos().padrao


def test_faixa_realcada_apaga_o_resto_em_cinza_chapado() -> None:
    from src import mapa

    camada = _dois_municipios()
    _, escala = _deck(camada, [1.0, 50.0, 99.0])
    escolhida = mapa.classificar(pd.Series([99.0]), escala).iloc[0]

    desenho, _ = _deck(camada, [1.0, 50.0, 99.0], faixa_realcada=escolhida)
    geo, props = _feicoes(desenho)
    c = mapa.Contornos()
    assert props["3"]["classe"] == escolhida
    assert props["3"]["cor"] != list(c.preenchimento_apagado)
    assert tuple(props["3"]["contorno"]) == c.realcado
    for k in ("1", "2"):
        assert props[k]["cor"] == list(c.preenchimento_apagado)
        assert tuple(props[k]["contorno"]) == c.apagado
    assert geo["lineWidthMinPixels"] == c.largura_realce


def test_faixa_que_nao_existe_nesta_escala_nao_apaga_ninguem() -> None:
    """O rótulo da última interação sobra no `session_state` quando a métrica
    muda; sem a guarda, o mapa inteiro sairia cinza."""
    from src import mapa

    _, props = _feicoes(_deck(_dois_municipios(), [1.0, 2.0, 3.0], faixa_realcada="9 a 99")[0])
    assert all(p["cor"] != list(mapa.Contornos().preenchimento_apagado) for p in props.values())


def test_notas_so_onde_ha_e_escapadas() -> None:
    """O componente não escapa as propriedades — `mapa.js` troca `{campo}`
    pelo valor cru num tooltip HTML —, então a nota, texto livre, é escapada
    no Python."""
    camada = _dois_municipios()
    notas = pd.Series({"1": "População < 5 mil: taxa instável", "3": ""})
    desenho, _ = _deck(camada, [1.0, 2.0, 3.0], notas=notas)
    _, props = _feicoes(desenho)
    assert "&lt; 5 mil" in props["1"]["nota"] and "<br>" in props["1"]["nota"]
    assert props["2"]["nota"] == "" and props["3"]["nota"] == ""
    assert "{nota}" in desenho._tooltip["html"]


def test_sem_notas_o_tooltip_nao_muda() -> None:
    desenho, _ = _deck(_dois_municipios(), [1.0, 2.0, 3.0])
    _, props = _feicoes(desenho)
    assert "nota" not in props["1"]
    assert "{nota}" not in desenho._tooltip["html"]


def test_coluna_nome_e_obrigatoria() -> None:
    """O padrão antigo, `"bairro_nome"`, caía em silêncio para a chave nas
    camadas de PE: o tooltip mostrava o código no lugar do nome."""
    from src import mapa

    with pytest.raises(TypeError):
        mapa.deck(_dois_municipios(), pd.Series([1.0]), chave="cod_mun6",
                  rampa=["#000000"] * 7, rotulo_metrica="x")


def test_o_clique_aceita_os_campos_de_outro_territorio() -> None:
    ev = {"nonce": "a-1", "properties": {"bairro_key": "boa viagem", "ds": "VI"}}
    assert mapa_componente.alvo_do_clique(ev, None) == (None, "a-1")
    assert mapa_componente.alvo_do_clique(ev, None, ("bairro_key", "ds")) == ("boa viagem", "a-1")
