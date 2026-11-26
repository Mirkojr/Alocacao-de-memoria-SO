"""Interface de linha de comando (CLI) do simulador.

Uso:
    python src/main.py                        modo interativo: digite os comandos
    python src/main.py roteiros/exemplo.cmd   executa um roteiro, mostrando cada comando
    python src/main.py < roteiros/exemplo.cmd executa pela entrada padrão; imprime só as
                                              saídas, como a "Saída esperada" do enunciado
"""

import sys
from pathlib import Path
from typing import Iterable

from comandos import executar, interpretar
from memoria import Memoria

AJUDA = ("Comandos: init <tamanho> | alloc <tamanho> <first|best|worst|next> | "
         "freeid <id> | freeaddr <endereço> | show | stats | defrag <init|end|opt> | sair")


def rodar_linha(memoria: Memoria, linha: str, ecoar: bool) -> None:
    """Executa uma linha e imprime a saída, se houver."""
    comando = interpretar(linha)
    if comando is None:                    # linha vazia ou comentário
        return
    if ecoar:                              # num roteiro, mostra o comando antes da saída
        print(f"> {comando.texto}")
    evento = executar(memoria, comando)
    if evento["saida"]:
        print(evento["saida"])


def rodar_roteiro(memoria: Memoria, linhas: Iterable[str], ecoar: bool) -> None:
    """Executa um roteiro inteiro, uma linha por vez."""
    for linha in linhas:
        rodar_linha(memoria, linha, ecoar)


def modo_interativo(memoria: Memoria) -> None:
    """Lê comandos do teclado até 'sair' ou fim da entrada."""
    print("Simulador de alocação de memória")
    print(AJUDA)
    while True:
        try:
            linha = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if linha.strip().lower() in ("sair", "exit", "quit"):
            return
        rodar_linha(memoria, linha, ecoar=False)


def main() -> None:
    """Escolhe o modo: roteiro por argumento, entrada redirecionada ou interativo."""
    # Acentos corretos no terminal do Windows e em saída redirecionada.
    for fluxo in (sys.stdin, sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    memoria = Memoria()

    if len(sys.argv) > 1:
        caminho = Path(sys.argv[1])
        if not caminho.is_file():
            sys.exit(f"Erro: roteiro não encontrado: {caminho}")
        try:
            texto = caminho.read_text(encoding="utf-8-sig")   # aceita UTF-8 com ou sem BOM
        except UnicodeDecodeError:
            sys.exit(f"Erro: salve o roteiro em UTF-8: {caminho}")
        rodar_roteiro(memoria, texto.splitlines(), ecoar=True)
    elif not sys.stdin.isatty():           # entrada redirecionada: python src/main.py < roteiro
        rodar_roteiro(memoria, sys.stdin, ecoar=False)
    else:
        modo_interativo(memoria)


if __name__ == "__main__":
    main()
