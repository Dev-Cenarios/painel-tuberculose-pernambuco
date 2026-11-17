# Diferenças em relação ao painel em R — canal endêmico

> **De onde vem este arquivo.** O registro completo das diferenças entre os
> nossos painéis e o painel em R/Shiny da equipe parceira fica no RecifeTB,
> o painel da tuberculose do Recife (ainda não publicado na organização).
> Aqui estão só as três seções que o código deste repositório cita, sobre o
> canal endêmico. A numeração (§4, §5, §6) é a do documento original, para
> que as referências no código continuem valendo.
>
> Os números das tabelas são do **Recife**, onde as diferenças foram medidas.
> As decisões valem igual para os painéis estaduais.

---

## 4. O gráfico histórico deles para em 2019 — **em aberto**

O gráfico "Todos os anos" do painel em R tem **120 pontos**, de janeiro de
2010 a dezembro de 2019, mesmo havendo dado até 2023.

**A pergunta é:** é uma janela de dez anos escolhida de propósito, ou é um
corte acidental?

A pergunta foi feita à equipe parceira e ainda não teve resposta. **Não vamos
copiar esse comportamento sem saber o motivo**: copiar sem entender é o jeito
mais fácil de herdar um defeito. Por isso a nossa série histórica vai até o
último ano com dado.

---

## 5. Canal endêmico: qual população usar — **fechada: nós estamos certos**

| | Painel em R | Este painel |
|---|---|---|
| População usada nos anos anteriores | a do **ano escolhido** | a **de cada ano** |
| Efeito | as linhas de 2020 a 2022 sobem cerca de 0,37% | a taxa real de cada ano |

**Isso foi medido, não suposto.** Dividindo os casos de janeiro pela taxa que
eles mostram, dá para descobrir que população eles usaram. Deu **a mesma nos
quatro anos**:

| Ano | Casos em janeiro | População que o painel em R usou | População real daquele ano |
|---|---:|---:|---:|
| 2020 | 172 | 1.592.362 | 1.598.198 |
| 2021 | 147 | 1.592.362 | 1.597.208 |
| 2022 | 187 | 1.592.362 | 1.594.897 |
| 2023 | 279 | 1.592.362 | 1.592.362 |

1.592.362 é a população de **2023**.

**A diferença no número é pequena, mas no significado é grande.** Com a
população fixa, a linha de 2020 não é a incidência de 2020: é **a contagem de
2020 dividida pela população de hoje**, um número que não é a taxa de ano
nenhum. O canal endêmico existe justamente para dizer se o mês atual saiu do
padrão **histórico**, então o padrão precisa ser o que realmente aconteceu.

**A regra dos quartis era a mesma nos dois:** três anos anteriores e o mesmo
método de cálculo (interpolação linear). Isso foi confirmado até a 6ª casa
decimal antes de aparecer a diferença de população. O `tests/test_canal.py`
confere as duas coisas separadamente. Depois, o número de anos mudou de 3
para 5 (veja a §6).

**Fechada por:** medição direta. Não depende da resposta de ninguém.

---

## 6. Quantos anos o canal endêmico usa: 5, e não 3 — **decidida**

| | Painel em R | Este painel |
|---|---:|---:|
| Anos que formam a faixa | 3 | **5** |
| Faixa usada para 2023 | 2020 a 2022 | 2018 a 2022 |
| Largura média da faixa | 2,05 | 1,70 |
| Meses de 2023 acima da faixa (acima do Q3) | 10 de 12 | **11 de 12** |

**Decidido em 28/ago/2026.** Com só três anos, cada quartil fica entre dois
valores, e 2020, o ano mais baixo da série, pesa um terço da faixa.

### Uma correção na justificativa

A primeira versão dizia que **2020 e 2021** tiveram poucas notificações por
causa da pandemia. **Os dados mostram que só metade disso é verdade:**

| Ano | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Incidência (por 100 mil) | 123,8 | 123,5 | 111,2 | 113,7 | **103,9** | 127,2 | 150,9 | 156,1 |

**Só 2020 ficou abaixo.** 2021 já passa 2018 e 2019.

### O limite que nenhuma quantidade de anos resolve

**A tuberculose no Recife está subindo sem parar:** são 50% acima do ponto
mais baixo (2020) em três anos.

O canal endêmico **parte do princípio de que a doença tem um padrão
estável**: a faixa dos anos anteriores é o "esperado", e o ano atual é
comparado com ela. **Quando a doença está crescendo, a faixa fica sempre para
trás**, e o ano atual aparece acima dela quase todo mês.

Foi o que aconteceu. E piorou com cinco anos: passou de 10 para **11 dos 12
meses** acima da faixa, porque 2018 e 2019 são mais baixos que 2021 e 2022 e
puxam a faixa para baixo.

**A leitura do gráfico é verdadeira, mas o que ela diz é "a doença cresceu",
e não "houve um surto em março".** Quem for usar o gráfico para achar um pico
fora de época precisa saber disso. Usar mais anos deixa a faixa mais estável,
mas **não resolve a tendência de alta**.

Se um dia achar picos fora de época virar uma necessidade, **o gráfico
precisa mudar**: por exemplo, uma faixa que leve a tendência em conta, ou uma
comparação com o esperado de um modelo, em vez do quartil puro. Fica
anotado, mas não virou tarefa.
