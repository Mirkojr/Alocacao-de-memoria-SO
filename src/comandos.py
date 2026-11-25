"""Interpreta uma linha de comando e a executa na Memoria.

A mesma sintaxe vale na CLI e nos roteiros da tela:
init, alloc, freeid, freeaddr, show, stats e defrag.
"""

from dataclasses import dataclass

import formatacao
from memoria import ErroSimulador, Memoria


@dataclass
class Comando:
    """Uma linha já separada em nome e argumentos."""

    nome: str           # ex.: "alloc"
    args: list[str]     # ex.: ["6", "next"]
    texto: str          # linha original, usada nas mensagens e na tela


def interpretar(linha: str) -> Comando | None:
    """Separa a linha em nome e argumentos. Linha vazia ou comentário (#) devolve None."""
    texto = linha.strip()
    if not texto or texto.startswith("#"):
        return None
    nome, *args = texto.split()
    return Comando(nome.lower(), args, texto)


def executar(memoria: Memoria, comando: Comando) -> dict:
    """Executa o comando e devolve o evento.

    O evento sempre tem 'erro' (None se deu certo) e 'saida' (texto que a
    CLI imprime, ou None quando o comando é silencioso).
    """
    try:
        evento = _executar(memoria, comando)
    except ErroSimulador as erro:
        evento = {"tipo": comando.nome, "erro": str(erro)}
    evento["comando"] = comando.texto
    evento.setdefault("erro", None)
    # init, alloc e free não imprimem nada quando dão certo (como no exemplo do PDF).
    evento.setdefault("saida", evento["erro"])
    return evento


def _executar(memoria: Memoria, comando: Comando) -> dict:
    """Chama o método da Memoria que corresponde ao comando."""
    match comando.nome, comando.args:
        case "init", [tamanho]:
            return memoria.init(_inteiro(tamanho, comando))
        case "alloc", [tamanho, algoritmo]:
            return memoria.alloc(_inteiro(tamanho, comando), algoritmo.lower())
        case "freeid", [id_bloco]:
            return memoria.free_id(_inteiro(id_bloco, comando))
        case "freeaddr", [endereco]:
            return memoria.free_addr(_inteiro(endereco, comando))
        case "show", []:
            return {"tipo": "show", "saida": memoria.show()}
        case "stats", []:
            return {"tipo": "stats", "saida": formatacao.formatar_stats(memoria.stats())}
        case "defrag", [opcao]:
            evento = memoria.defrag(opcao.lower())
            evento["saida"] = formatacao.formatar_defrag(evento)
            return evento
        case _:
            # Nome desconhecido ou número errado de argumentos.
            raise ErroSimulador(formatacao.erro_comando_invalido(comando.texto))


def _inteiro(texto: str, comando: Comando) -> int:
    """Converte um argumento numérico; texto que não é número vira erro de comando."""
    try:
        return int(texto)
    except ValueError:
        raise ErroSimulador(formatacao.erro_comando_invalido(comando.texto)) from None
