"""Servidor local da tela passo a passo. Usa só a biblioteca padrão do Python.

Uso:
    python src/servidor.py [porta]       abre http://127.0.0.1:8000 no navegador

Rotas:
    GET  /               arquivos da pasta web/
    GET  /api/roteiros   exemplos da pasta roteiros/ (nome e texto)
    POST /api/simular    {"roteiro": "init 32\\n..."}  →  {"passos": [...]}

A tela não calcula nada: o servidor roda a mesma simulação da CLI e devolve os passos.
"""

import json
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from simulacao import simular_roteiro

RAIZ = Path(__file__).resolve().parent.parent
PASTA_WEB = RAIZ / "web"
PASTA_ROTEIROS = RAIZ / "roteiros"
LIMITE_ROTEIRO = 200_000          # bytes; um roteiro de verdade tem poucas linhas


class Manipulador(SimpleHTTPRequestHandler):
    """Entrega os arquivos de web/ e responde às rotas /api/."""

    # Tipos fixos: no Windows o registro às vezes diz que .js é texto puro,
    # e o navegador se recusa a carregar o módulo.
    extensions_map = {".html": "text/html; charset=utf-8", ".css": "text/css",
                      ".js": "text/javascript", ".svg": "image/svg+xml"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PASTA_WEB), **kwargs)

    def do_GET(self):
        """Lista de exemplos em /api/roteiros; qualquer outro caminho é arquivo de web/."""
        if self.path == "/api/roteiros":
            self.responder_json(200, listar_roteiros())
        else:
            super().do_GET()                     # arquivo estático de web/

    def do_POST(self):
        """Recebe {"roteiro": texto} em /api/simular e devolve os passos simulados."""
        if self.path != "/api/simular":
            self.responder_json(404, {"erro": "Rota não encontrada."})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", 0))
            if tamanho < 0:
                raise ValueError                 # read(-1) esperaria o cliente fechar a conexão
            if tamanho > LIMITE_ROTEIRO:
                self.responder_json(413, {"erro": "Roteiro grande demais."})
                return
            roteiro = json.loads(self.rfile.read(tamanho).decode("utf-8"))["roteiro"]
            if not isinstance(roteiro, str):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            self.responder_json(400, {"erro": 'Envie um JSON no formato {"roteiro": "..."}.'})
            return
        self.responder_json(200, simular_roteiro(roteiro))

    def responder_json(self, status: int, dados) -> None:
        """Envia `dados` como JSON em UTF-8."""
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def end_headers(self):
        """Pede ao navegador para sempre conferir se o arquivo mudou (evita tela desatualizada)."""
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, formato, *args):
        """Não imprime uma linha por requisição."""


class ServidorLocal(ThreadingHTTPServer):
    """Servidor que falha de verdade quando a porta já está em uso."""

    # No Windows, SO_REUSEADDR deixa dois programas abrirem a mesma porta;
    # desligado, a porta ocupada dá erro e criar_servidor tenta a próxima.
    allow_reuse_address = sys.platform != "win32"


def listar_roteiros() -> list[dict]:
    """Exemplos de roteiros/ para a lista da tela."""
    return [{"nome": arquivo.name, "texto": arquivo.read_text(encoding="utf-8-sig")}
            for arquivo in sorted(PASTA_ROTEIROS.glob("*.cmd"))]


def criar_servidor(porta: int) -> ThreadingHTTPServer:
    """Abre o servidor na porta pedida ou na próxima livre (até 10 tentativas)."""
    for tentativa in range(porta, porta + 10):
        try:
            return ServidorLocal(("127.0.0.1", tentativa), Manipulador)
        except OSError:                          # porta ocupada
            continue
    sys.exit(f"Erro: nenhuma porta livre entre {porta} e {porta + 9}.")


def main() -> None:
    """Abre o servidor, mostra o endereço e abre o navegador."""
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    except ValueError:
        sys.exit(f"Erro: porta inválida: {sys.argv[1]}")
    servidor = criar_servidor(porta)
    endereco = f"http://127.0.0.1:{servidor.server_address[1]}"
    print(f"Simulação visual em {endereco}  (Ctrl+C para encerrar)")
    webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
