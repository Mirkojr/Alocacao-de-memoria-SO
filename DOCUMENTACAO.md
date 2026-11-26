# Decisões de implementação

Este documento explica como o simulador foi construído: classes, estruturas de dados, padrões de projeto e as decisões que o enunciado deixa em aberto. Como executar está no [README](README.md).

## 1. Visão geral

O projeto é em Python 3.10, sem bibliotecas externas. Toda a lógica fica em `src/`. A CLI e a tela usam o **mesmo núcleo**: a tela não calcula nada, só desenha os passos que o Python simulou. Por isso as duas versões nunca dão resultados diferentes.

```
      CLI (main.py)                  Tela no navegador (web/)
            │                                 │ POST /api/simular
            │                          servidor.py
            │                          simulacao.py   roteiro → um retrato por passo
            └───────────────┬─────────────────┘
                      comandos.py              texto "alloc 6 next" → memoria.alloc(6, "next")
                            │
                      memoria.py               estado + métodos do enunciado
             ┌──────────────┼──────────────┐
       algoritmos.py    defrag.py    formatacao.py
             └──────────────┼──────────────┘
                        bloco.py               Bloco, FitAlg, Option
```

Cada camada só usa as de baixo, e cada arquivo tem uma responsabilidade:

| Arquivo | Responsabilidade |
|---|---|
| `bloco.py` | Estrutura de cada bloco (`Bloco`) e os tipos `FitAlg` e `Option`. |
| `memoria.py` | Classe `Memoria`: estado da memória e os métodos da tabela do enunciado. |
| `algoritmos.py` | First, Best, Worst e Next Fit: só escolhem o buraco. |
| `defrag.py` | Layout e custo das opções INIT, END e OPT. |
| `formatacao.py` | Textos no formato do PDF (`show`, `stats`, defrag) e todas as mensagens de erro. |
| `comandos.py` | Lê uma linha de comando e chama o método certo da `Memoria`. |
| `simulacao.py` | Executa um roteiro inteiro e guarda um retrato da memória a cada passo. |
| `main.py` | CLI: modo interativo, roteiro por argumento ou pela entrada padrão. |
| `servidor.py` | Servidor HTTP local (só biblioteca padrão) que entrega a tela e simula roteiros. |
| `api/*.py` | Funções da Vercel: só herdam o manipulador de `servidor.py`, então a versão publicada roda o mesmo código. |

## 2. Estruturas de dados

### O bloco

Cada trecho contíguo da memória é um `Bloco`, a estrutura de controle sugerida no enunciado:

```python
@dataclass
class Bloco:
    inicio: int            # endereço inicial
    tamanho: int           # em bytes
    id: int | None = None  # None = buraco livre
```

Duas propriedades ajudam a ler o código: `fim` (primeiro endereço depois do bloco) e `livre` (se é buraco). Neste simulador não há alinhamento nem fragmentação interna, então o espaço usado é sempre o tamanho do bloco.

### A memória

A classe `Memoria` guarda quatro atributos:

| Atributo | Significado |
|---|---|
| `tamanho` | Total de bytes (0 enquanto não houve `init`). |
| `blocos` | Lista de `Bloco` em ordem de endereço, cobrindo a memória inteira: blocos alocados e buracos intercalados. |
| `proximo_id` | Próximo id a usar. Começa em 1 e nunca é reaproveitado. |
| `ponteiro` | Ponteiro do Next Fit. |

Exemplo, depois de `init 32` e `alloc 8 first`:

```
blocos = [Bloco(0, 8, id=1), Bloco(8, 24)]
```

**Por que uma lista de blocos e não um vetor de bytes?** Todas as operações do enunciado trabalham com blocos: escolher um buraco, dividir, unir vizinhos, mover. Com a lista, cada operação mexe em poucos itens. As duas linhas do `show` (`####....` e `1111....`) são montadas a partir da lista na hora de imprimir.

A lista mantém uma regra: **nunca há dois buracos vizinhos**. Ao liberar um bloco, ele é unido aos buracos ao lado (coalescência), então cada buraco da lista é um espaço livre contíguo máximo. Com isso, "número de buracos" é só contar os blocos livres.

## 3. Métodos do enunciado

Os nomes e parâmetros seguem a tabela "Métodos a Implementar":

| Método | O que faz |
|---|---|
| `init(tamanho)` | Cria um único buraco do tamanho pedido; zera ids e ponteiro. |
| `alloc(tamanho, alg)` | Pede ao algoritmo um buraco, coloca o bloco no início dele e deixa a sobra livre. Aceita `FitAlg.NEXT` ou o texto `"next"`. |
| `free_id(id)` | Libera o bloco com esse id e faz a coalescência. |
| `free_addr(endereco)` | Igual, procurando o bloco que começa no endereço. |
| `show()` | Devolve o texto do mapa, dos blocos ativos e das estatísticas. |
| `stats()` | Devolve ocupado, livre, buracos, maior buraco e uso efetivo. |
| `defrag(option)` | Compacta a memória com INIT, END ou OPT. Aceita `Option.OPT` ou `"opt"`. |

Os métodos não imprimem nada: devolvem dados, e quem imprime é a CLI. Assim a mesma classe serve à tela.

Quando a operação é inválida, o método lança `ErroSimulador` com a mensagem pronta **antes** de alterar qualquer coisa. Por isso um comando com erro nunca deixa a memória pela metade.

Cada método que muda a memória devolve um **evento**: um dicionário dizendo o que mudou (bloco alocado, buracos examinados, buracos unidos, blocos movidos). A CLI usa só o necessário; a tela usa tudo para destacar o passo.

## 4. Algoritmos de alocação

Os quatro algoritmos recebem os buracos em ordem de endereço e devolvem o buraco escolhido e os buracos examinados até a decisão. Os examinados são o que a tela usa para mostrar a diferença entre os algoritmos.

| Algoritmo | Regra | Examina |
|---|---|---|
| First Fit | Primeiro buraco, em ordem de endereço, em que o bloco cabe. | Até achar. |
| Best Fit | Menor buraco em que o bloco cabe. | Todos. |
| Worst Fit | Maior buraco (se o bloco couber nele). | Todos. |
| Next Fit | Como o First Fit, mas começando no ponteiro. | Até achar, dando a volta. |

- **Empate:** vale o buraco de menor endereço. Como a lista já está em ordem de endereço, `min()` e `max()` ficam com o primeiro empatado.
- **Next Fit:** a busca começa no primeiro buraco cujo **fim** passa do ponteiro (então o buraco que contém o ponteiro é examinado inteiro). Ela segue até o fim da memória e depois volta ao endereço 0. Isso é feito reordenando os buracos (`buracos[partida:] + buracos[:partida]`) e aplicando o First Fit.
- **Ponteiro:** depois de um alloc bem-sucedido, vai para o fim do novo bloco. Liberar e alloc com erro não o movem. Volta a 0 depois de `init` e de `defrag`.
- **Ids:** sequenciais a partir de 1, nunca reaproveitados. Um alloc que falha não consome id.

## 5. Desfragmentação

As três opções são casos de uma mesma regra: **os k primeiros blocos ficam colados no início da memória, os demais colados no fim, e sobra um único buraco entre eles**. A ordem e os ids dos blocos não mudam.

| Opção | k | Resultado |
|---|---|---|
| INIT | 0 | Todos os blocos no fim; o espaço livre fica no início. |
| END | todos | Todos os blocos no início; o espaço livre fica no fim. |
| OPT | o de menor custo | O buraco fica onde mover menos bytes. Em empate, vale o maior k. |

Um bloco conta como **movido** quando o endereço inicial muda, e o **custo** é a soma dos tamanhos dos blocos movidos. O OPT calcula o custo para todo k de 0 até o número de blocos e escolhe o menor; para o empate valer o maior k, a busca percorre os k do maior para o menor.

Exemplo do enunciado (64 bytes, id=1 @0 +10B e id=3 @18 +6B): INIT move 2 blocos (16 B), END move 1 (6 B), OPT move 1 (6 B) com k=2, que empata com k=1.

## 6. Padrões de projeto

- **Strategy**, nos algoritmos de alocação. Os quatro têm a mesma assinatura, e a `Memoria` escolhe qual usar por um dicionário, sem `if` encadeado:

  ```python
  ESTRATEGIAS = {FitAlg.FIRST: first_fit, FitAlg.BEST: best_fit,
                 FitAlg.WORST: worst_fit, FitAlg.NEXT: next_fit}
  escolhido, examinados = ESTRATEGIAS[alg](self.buracos(), tamanho, self.ponteiro)
  ```

  Para incluir um algoritmo novo basta escrever a função e colocá-la no dicionário.
- **Snapshot (ideia do padrão Memento)**, no botão Voltar da tela, como o enunciado sugere. A cada passo, `simulacao.py` guarda um retrato do estado (blocos, ponteiro, próximo id e estatísticas) em um dicionário novo. Voltar é mostrar o retrato anterior, então ids e ponteiro voltam exatamente como estavam, sem precisar "desfazer" operações.

Os comandos são escolhidos com `match` (Python 3.10), que confere o nome e o número de argumentos de uma vez:

```python
match comando.nome, comando.args:
    case "alloc", [tamanho, algoritmo]:
        return memoria.alloc(_inteiro(tamanho, comando), algoritmo.lower())
```

## 7. Decisões nossas (o enunciado não define)

| Ponto em aberto | Decisão |
|---|---|
| Um `alloc first/best/worst` move o ponteiro do Next Fit? | Sim. O enunciado define o ponteiro como "logo após o último bloco alocado", sem restringir o algoritmo. |
| O que o `show` imprime | Mapa, blocos ativos **e** estatísticas, igual à "Saída esperada" do PDF. O `stats` imprime só as estatísticas. |
| `init`, `alloc` e `free` imprimem algo quando dão certo? | Não, para a saída bater com a sessão de exemplo do PDF. Só imprimem em caso de erro. |
| Id com 2 dígitos na linha de identificadores do `show` | Mostra o último dígito (id 12 → `2`), porque cada byte ocupa um caractere. A linha "Blocos ativos" traz o id completo. |
| Linha inválida no roteiro (ex.: `aloc 8`) | Vira um passo com mensagem de erro e a memória não muda. É o mesmo comportamento na CLI e na tela. |
| Roteiro pela entrada padrão | Imprime só as saídas (como a "Saída esperada"). Com o arquivo como argumento, cada comando é mostrado antes da saída. |

### Mensagens de erro

Todas ficam em `formatacao.py`.

| Situação | Mensagem |
|---|---|
| Alloc sem espaço (texto do enunciado) | `Erro: sem espaço contíguo para N bytes (livre total: X, maior buraco: Y)` |
| `freeid` sem bloco com esse id | `Erro: não há bloco alocado com id N` |
| `freeaddr` fora do início de um bloco alocado | `Erro: endereço N não é o início de um bloco alocado` |
| Comando antes do `init` | `Erro: memória não inicializada (use init <tamanho>)` |
| Tamanho zero ou negativo | `Erro: o tamanho deve ser maior que zero` |
| Algoritmo desconhecido | `Erro: algoritmo inválido: X (use first, best, worst ou next)` |
| Opção de defrag desconhecida | `Erro: opção de defrag inválida: X (use init, end ou opt)` |
| Comando desconhecido ou com argumentos errados | `Erro: comando inválido: <linha>` |

## 8. Simulação visual

- **Servidor** (`servidor.py`): entrega os arquivos de `web/` e tem duas rotas. `GET /api/roteiros` lista os exemplos de `roteiros/`, e `POST /api/simular` recebe o texto do roteiro e devolve a lista de passos.
- **Passos** (`simulacao.py`): o passo 0 é o estado antes do primeiro comando, para onde o Reiniciar volta. Cada passo traz o comando, o tamanho da memória, os blocos, o ponteiro, o próximo id, as estatísticas e o evento do que mudou.
- **Tela** (`web/`): HTML, CSS e JavaScript puros, sem bibliotecas, em cinco módulos:

| Módulo | Função |
|---|---|
| `main.js` | Único lugar com estado: a lista de passos e o passo atual. Avançar, Voltar, Reproduzir, Pausar, Reiniciar e o clique numa linha da pilha (ir direto a um passo) só mudam o índice e redesenham. Também troca as abas da coluna da direita (Passo atual, Estatísticas e Roteiro). |
| `api.js` | Lê o arquivo escolhido e conversa com o servidor. |
| `historico.js` | Pilha de barras no tempo, com escala de endereços, destaques do passo, setas do defrag e marca do ponteiro. |
| `painel.js` | Aba Passo atual (explicação com um resumo das estatísticas, mensagem de erro, blocos ativos e custo do defrag) e aba Estatísticas (as cinco métricas do `stats` e o próximo id). |
| `editor.js` | Aba "Roteiro": mostra o texto em execução, permite editar e manda o texto novo para o servidor simular de novo. |

Os efeitos visuais são discretos e só de CSS: cores que mudam suavemente, realce ao passar o mouse e um fade curto no passo atual quando o usuário muda de passo. Nada se desloca na tela, e com "reduzir movimento" ligado no sistema as transições não rodam.

A largura de cada bloco na barra é proporcional ao tamanho (`left` e `width` em %), então a tela funciona com qualquer tamanho de memória. A reprodução automática relê o intervalo a cada passo e aceita vírgula ou ponto (`0,5` ou `0.5`).

## 9. Testes

`python -m unittest discover -s tests -v`

- `test_enunciado.py`: a sessão de exemplo do PDF (saída do `show` idêntica), a tabela do Next Fit passo a passo, a tabela do defrag e casos de borda (ids, coalescência, empates, erros, `init` repetido).
- `test_comandos.py`: leitura dos comandos, comandos inválidos e a CLI de ponta a ponta, por arquivo e pela entrada padrão, inclusive com arquivo salvo com BOM.
- `test_simulacao.py`: os passos gerados para a tela e as rotas do servidor, com um servidor de verdade numa porta livre.

## 10. Limitações conhecidas

- O `show` usa um caractere por byte, como no PDF. Em memórias muito grandes (milhões de bytes) a saída fica enorme.
- A tela guarda um retrato completo por passo. Roteiros com milhares de comandos ficam pesados.
- Comentários só valem em linhas inteiras começando com `#`, como diz o enunciado.
