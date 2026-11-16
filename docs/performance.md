# Performance

Medido em 30/set/2026, com tuberculose, no `data/` deste painel, já com a
janela de dez anos que entrou no mesmo dia. Reproduzir com:

```bash
python -m scripts.medir_performance
```

Antes deste dia o arquivo trazia a linha de base de agosto, feita quando o
mapa era `st.pydeck_chart` e os gráficos eram Altair. Desde 21/set os dois são
componentes próprios (deck.gl e ECharts), e as medições precisavam ser
refeitas.

## O alvo

**300 ms por interação.** É o tempo entre o clique e a tela nova: abaixo disso
a resposta é percebida como imediata, e acima começa a parecer que travou.

Vale para a **primeira** vez. O `st.cache_data` guarda cada leitura por 24
horas, então repetir o mesmo recorte custa quase nada.

## Quanto custa cada leitura

Mediana de cinco execuções, em milissegundos, sem o cache do Streamlit, em
2024 — o último ano fechado, que é onde o painel abre.

| Operação | PE | macrorregião | Recife |
|---|---:|---:|---:|
| `canal.montar` | 141 | 235 | 144 |
| `canal.epicurva` (10 anos) | **29** | **37** | **29** |
| `composicao` (um tópico) | 14 | 21 | 17 |
| `piramide_completa` | 14 | 18 | 16 |
| `ranking` | 8 | 7 | 7 |
| `serie_anual` | 7 | 16 | 10 |
| `valores_por_geografia` (o mapa) | 3 | 3 | 3 |
| **soma dos leitores** | **217** | **337** | **225** |
| `kpis.calcular` (os 6 cards) | 23 | 38 | 30 |

A linha da epicurva já é a de depois da otimização de 30/set (abaixo); as
demais foram medidas antes dela. Somar a coluna superestima o que o usuário
espera — os leitores são cacheados separadamente e um clique não invalida
todos —, mas serve de teto, e ele **passou a caber nos 300 ms** em PE e no
município.

## O que sobrou de caro: o canal endêmico

Depois da otimização da epicurva, o item mais pesado é o `canal.montar`, com
141 ms em PE e 235 numa macrorregião — mais que todos os outros leitores
juntos. Ele monta os cinco anos de referência mais o corrente, um ano por
consulta, e precisa da **incidência**, não só da contagem: aplicar a mesma
correção exigiria trazer a população de todos os anos e recalcular a taxa, o
que mexe em número na tela e pede conferência.

**A janela de anos, aplicada em 30/set, já cortou um terço disso.** Antes a
epicurva varria de 2010 até o ano selecionado; agora o padrão é dez anos, que
é o recorte do Boletim. Medido:

| janela | PE | macrorregião |
|---|---:|---:|
| 15 anos | 344 ms | 586 ms |
| **10 anos (padrão)** | **228 ms** | **385 ms** |
| 5 anos | 112 ms | 190 ms |

O custo é linear no número de anos, e a razão é que a epicurva monta a série
com **uma consulta por ano**.

**Por que aqui custava mais que na hanseníase.** O `serie_mensal` daqui tira
a população da região do `incidence`, e não do `_cache_ts`, porque este só tem
linha para município com caso no mês — sem isso, a incidência de uma região
sairia errada. Era uma consulta a mais por ano, multiplicada pelos dez, e é o
que explica a epicurva custar 413 ms aqui contra 201 lá antes da correção.
Depois dela as duas custam o mesmo: a consulta agregada nem busca população.

A macrorregião é o pior recorte porque lê a partição `MUN` com uma lista de
municípios no `IN (...)`, pagando por vários onde o estado paga por um
agregado pronto. É o preço de o escopo atravessar a tela inteira.

## A epicurva numa consulta só — 30/set/2026

Ela montava a série **ano a ano**, e cada ano custava duas leituras do
`_cache_ts` (uma para casos, outra para incidência) mais duas do `incidence`
quando o recorte é uma região. Dez anos numa macrorregião eram quarenta
consultas para desenhar uma linha de contagem.

Agora é uma consulta: a partição `ano` fica fora do caminho, o glob pega todos
os anos e o `WHERE` recorta o intervalo. E só `casos` — a epicurva desenha
contagem, e trazer população para calcular uma incidência que ninguém usa era
metade do custo.

Medido alternando as duas implementações **no mesmo processo**, que é o que
torna a comparação honesta: a máquina varia de carga ao longo do dia, e medir
uma de manhã e a outra à tarde compara o computador, não o código.

| recorte | antes | depois | ganho |
|---|---:|---:|---:|
| PE | 413 ms | **29 ms** | 93% |
| macrorregião | 704 ms | **37 ms** | 95% |
| município | 403 ms | **29 ms** | 93% |

`tests/test_performance.py` compara mês a mês as duas contas: trocar um laço
por consulta agregada é o tipo de mudança que acerta o total e erra a
distribuição sem ninguém ver.

É a exceção à regra de podar pela partição (`contrato-dados.md`): vale porque
o que se lê é justamente a série inteira, e os arquivos de um mesmo nível têm
o mesmo esquema.

## O mapa

| | |
|---|---|
| Payload de PE, 185 municípios | **0,12 MB** |
| Montar o `deck` (geometria + cores + tooltip) | 221 ms |
| Ler os valores do mapa | 3 ms |

O teto de payload está preso por teste. Com 0,12 MB há folga larga — a malha
vem simplificada e as coordenadas arredondadas.

Os 221 ms de montagem acontecem uma vez por recorte e ficam em cache. O clique
que só muda a cor não paga isso: o componente interpola no navegador, sem
refazer o deck.

## O que a suíte prende

`tests/test_performance.py` guarda o que mantém o tempo baixo, sem medir tempo
— tempo varia com a máquina e o teste falharia por motivo errado:

- nenhuma variável do SINAN é lida duas vezes no mesmo `kpis.calcular`;
- o teto de payload do mapa continua existindo.

## O que não foi medido

- Vários usuários simultâneos.
- O tempo de renderização no navegador, separado do tempo de servidor.

---

## Abertura, medida em 16/nov/2026

O chefe reclamou de lentidão "quando acessamos". Medido no endereço público,
com o CPU do navegador freado em 4× (uma máquina comum, não esta):

| | HTML | 1º componente | tela de cima pronta |
|---|---|---|---|
| 1º acesso, container recém-subido | 0,9 s | 8,3 s | **12,5 s** |
| acessos seguintes | 0,9 s | 4,3 s | 7,6 s |

O gargalo não era dado nem VM: os leitores somam 230 ms em PE, o script roda
em 0,3 s com cache quente, o nginx serve em 50 ms e a VM estava ociosa. Era o
**cache vazio**: `TTL_DADOS` era de 24 h, então quem abria o painel uma vez
por dia pagava a leitura inteira **toda** vez.

Depois de tirar o prazo (o dado só muda com extração nova, que reinicia o
processo) e aquecer a tela de abertura numa thread ao subir:

| | tela de cima pronta |
|---|---|
| acesso comum, CPU 4× | 7,6 s → **5,2 s** |
| acesso comum, CPU normal | 2,5 s → **1,8 s** |
| 1º acesso depois de subir | 12,5 s → 10,5 s |

### O que foi tentado e não vale

- **Subir o ECharts só quando o gráfico chega perto da tela.** Corta o JS
  interpretado de 15,5 MB para 2,7 MB — e mesmo assim ficou **mais lento**
  com CPU freado (8,7 s contra 6,9 s): o gráfico visível passa a esperar o
  observador e a busca do bundle, e o ganho de parse não paga essa espera.
- **Bundle enxuto do ECharts** (470 kB em vez de 1 MB). Diferença medida:
  nenhuma (6,4 s contra 6,3 s) — o navegador compila o arquivo uma vez e os
  outros 13 iframes reaproveitam. De quebra, o `simple` não traz o componente
  de título, e os nomes das variáveis nos tópicos somem.

O que sobra no caminho crítico é o frontend do Streamlit (~2,6 s com CPU 4×)
e o deck.gl do mapa — os dois fora do nosso alcance sem trocar de arquitetura.
