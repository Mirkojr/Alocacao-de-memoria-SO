"""Compactação da memória (defrag): calcula o layout e o custo de INIT, END e OPT.

Os blocos mantêm a ordem relativa e os ids; só o endereço muda.
Todas as opções deixam um único buraco: os k primeiros blocos colados no
início e os demais colados no fim. INIT é k = 0, END é k = todos e o
OPT escolhe o k que move menos bytes.
"""

from bloco import Bloco, Option


def layout_com_k(alocados: list[Bloco], tamanho: int, k: int) -> list[Bloco]:
    """Os k primeiros blocos no início, os demais no fim e um buraco entre eles."""
    novos = []
    endereco = 0
    for b in alocados[:k]:
        novos.append(Bloco(endereco, b.tamanho, b.id))
        endereco += b.tamanho

    resto = alocados[k:]
    inicio_resto = tamanho - sum(b.tamanho for b in resto)
    if inicio_resto > endereco:                     # memória cheia não tem buraco
        novos.append(Bloco(endereco, inicio_resto - endereco))

    for b in resto:
        novos.append(Bloco(inicio_resto, b.tamanho, b.id))
        inicio_resto += b.tamanho
    return novos


def blocos_movidos(alocados: list[Bloco], novos: list[Bloco]) -> list[dict]:
    """Blocos cujo endereço inicial mudou (é isso que conta como 'movido')."""
    endereco_antigo = {b.id: b.inicio for b in alocados}
    return [{"id": b.id, "de": endereco_antigo[b.id], "para": b.inicio, "tamanho": b.tamanho}
            for b in novos if not b.livre and b.inicio != endereco_antigo[b.id]]


def calcular_opcoes(blocos: list[Bloco], tamanho: int) -> dict[Option, dict]:
    """Layout e custo de cada opção. Custo = soma dos tamanhos dos blocos movidos."""
    alocados = [b for b in blocos if not b.livre]

    candidatos = []
    for k in range(len(alocados) + 1):
        novos = layout_com_k(alocados, tamanho, k)
        movidos = blocos_movidos(alocados, novos)
        candidatos.append({
            "k": k,
            "blocos": novos,
            "movidos": movidos,
            "bytes_movidos": sum(m["tamanho"] for m in movidos),
        })

    # OPT: menor custo; em empate, vale o maior k.
    # Percorrendo do maior k para o menor, min() fica com o primeiro empatado.
    opt = min(reversed(candidatos), key=lambda c: c["bytes_movidos"])
    return {
        Option.INIT: candidatos[0],      # todos colados no fim: livre no início
        Option.END: candidatos[-1],      # todos colados no início: livre no fim
        Option.OPT: opt,
    }
