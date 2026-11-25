"""Estratégias de escolha de buraco (padrão Strategy): First, Best, Worst e Next Fit.

As quatro têm a mesma assinatura: recebem os buracos em ordem de endereço,
o tamanho pedido e o ponteiro do Next Fit, e devolvem
(buraco escolhido ou None, buracos examinados até decidir).
"""

from bloco import Bloco, FitAlg

Resultado = tuple[Bloco | None, list[Bloco]]


def first_fit(buracos: list[Bloco], tamanho: int, ponteiro: int) -> Resultado:
    """Primeiro buraco, em ordem de endereço, em que o bloco cabe."""
    examinados = []
    for buraco in buracos:
        examinados.append(buraco)
        if buraco.tamanho >= tamanho:
            return buraco, examinados
    return None, examinados


def best_fit(buracos: list[Bloco], tamanho: int, ponteiro: int) -> Resultado:
    """Menor buraco em que o bloco cabe. Examina todos."""
    cabem = [b for b in buracos if b.tamanho >= tamanho]
    # Empate: min() fica com o primeiro da lista, que é o de menor endereço.
    escolhido = min(cabem, key=lambda b: b.tamanho, default=None)
    return escolhido, list(buracos)


def worst_fit(buracos: list[Bloco], tamanho: int, ponteiro: int) -> Resultado:
    """Maior buraco, se o bloco couber nele. Examina todos."""
    # Empate: max() também fica com o primeiro, o de menor endereço.
    maior = max(buracos, key=lambda b: b.tamanho, default=None)
    if maior is None or maior.tamanho < tamanho:
        return None, list(buracos)
    return maior, list(buracos)


def next_fit(buracos: list[Bloco], tamanho: int, ponteiro: int) -> Resultado:
    """Como o First Fit, mas começa no ponteiro e dá a volta na memória."""
    # Começa no primeiro buraco cujo fim passa do ponteiro:
    # o buraco que contém o ponteiro é examinado inteiro.
    partida = next((i for i, b in enumerate(buracos) if b.fim > ponteiro), len(buracos))
    # Da partida até o fim da memória e, depois, do endereço 0 até a partida.
    ordem = buracos[partida:] + buracos[:partida]
    return first_fit(ordem, tamanho, ponteiro)


# A Memoria escolhe a estratégia por aqui, sem if encadeado.
ESTRATEGIAS = {
    FitAlg.FIRST: first_fit,
    FitAlg.BEST: best_fit,
    FitAlg.WORST: worst_fit,
    FitAlg.NEXT: next_fit,
}
