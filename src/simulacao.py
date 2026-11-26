"""Executa um roteiro inteiro e guarda um retrato da memória a cada passo (para a tela).

A tela só navega por essa lista: Voltar é mostrar o retrato anterior,
com ids e ponteiro exatamente como estavam (ideia do padrão Memento).
"""

from comandos import executar, interpretar
from memoria import Memoria

# Na tela o mapa e as estatísticas estão sempre visíveis; esses comandos não viram passo.
IGNORADOS_NA_TELA = {"show", "stats"}


def simular_roteiro(texto: str) -> dict:
    """Devolve {'passos': [...]}. O passo 0 é o estado antes do primeiro comando."""
    memoria = Memoria()
    passos = [retrato(memoria, numero=0, evento=None)]
    for linha in texto.splitlines():
        comando = interpretar(linha)
        if comando is None:
            continue
        # show/stats válidos são pulados; com argumentos ("show tudo") viram passo de erro, como na CLI.
        if comando.nome in IGNORADOS_NA_TELA and not comando.args:
            continue
        evento = executar(memoria, comando)
        passos.append(retrato(memoria, numero=len(passos), evento=evento))
    return {"passos": passos}


def retrato(memoria: Memoria, numero: int, evento: dict | None) -> dict:
    """Cópia do estado da memória depois de um passo, já pronta para virar JSON."""
    return {
        "numero": numero,
        "comando": evento["comando"] if evento else None,
        "tamanho": memoria.tamanho,               # pode mudar se o roteiro der init de novo
        "blocos": [{"inicio": b.inicio, "tamanho": b.tamanho, "id": b.id}
                   for b in memoria.blocos],
        "ponteiro": memoria.ponteiro,
        "proximo_id": memoria.proximo_id,
        "stats": memoria.stats() if memoria.tamanho else None,
        "evento": evento,                         # o que mudou neste passo
    }
