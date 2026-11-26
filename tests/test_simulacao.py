"""Testes da simulação passo a passo (simulacao.py) e das rotas do servidor (servidor.py).

Rodar com: python -m unittest discover -s tests -v
"""

import http.client
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from servidor import Manipulador, ServidorLocal, criar_servidor  # noqa: E402
from simulacao import simular_roteiro  # noqa: E402


def roteiro(nome: str) -> str:
    return (RAIZ / "roteiros" / nome).read_text(encoding="utf-8")


def layout(passo: dict) -> list[tuple]:
    return [(b["inicio"], b["tamanho"], b["id"]) for b in passo["blocos"]]


class TestSimulacao(unittest.TestCase):

    def test_passo_zero_e_o_estado_antes_do_primeiro_comando(self):
        passo = simular_roteiro("init 8")["passos"][0]
        self.assertEqual(passo, {"numero": 0, "comando": None, "tamanho": 0, "blocos": [],
                                 "ponteiro": 0, "proximo_id": 1, "stats": None, "evento": None})

    def test_comentarios_show_e_stats_nao_viram_passo(self):
        passos = simular_roteiro("# teste\n\ninit 8\nshow\nalloc 2 first\nstats\n")["passos"]
        self.assertEqual([p["comando"] for p in passos], [None, "init 8", "alloc 2 first"])

    def test_show_ou_stats_com_argumento_viram_erro(self):
        passos = simular_roteiro("init 8\nshow tudo")["passos"]
        self.assertEqual(passos[2]["evento"]["erro"], "Erro: comando inválido: show tudo")

    def test_roteiro_do_next_fit(self):
        passos = simular_roteiro(roteiro("exemplo-nextfit.cmd"))["passos"]
        self.assertEqual(len(passos), 8)                      # passo 0 + 7 comandos
        ultimo = passos[-1]
        self.assertEqual(ultimo["comando"], "alloc 6 next")
        self.assertEqual(ultimo["ponteiro"], 6)
        self.assertEqual(ultimo["stats"]["uso"], 81.25)
        self.assertEqual([b["inicio"] for b in ultimo["evento"]["examinados"]], [28, 0])
        self.assertEqual(passos[-2]["ponteiro"], 28)          # ponteiro antes do passo

    def test_retratos_nao_mudam_depois(self):
        passos = simular_roteiro(roteiro("exemplo-nextfit.cmd"))["passos"]
        self.assertEqual(layout(passos[1]), [(0, 32, None)])  # logo depois do init

    def test_passo_com_erro_mantem_a_memoria(self):
        passos = simular_roteiro(roteiro("exemplo-erro.cmd"))["passos"]
        erro = passos[7]
        self.assertEqual(erro["comando"], "alloc 24 best")
        self.assertTrue(erro["evento"]["erro"].startswith("Erro: sem espaço contíguo"))
        self.assertEqual(layout(erro), layout(passos[6]))
        self.assertEqual(len(passos[6]["evento"]["unidos"]), 3)  # coalescência do freeid 3

    def test_passo_de_defrag_traz_as_tres_opcoes(self):
        evento = simular_roteiro(roteiro("exemplo-defrag.cmd"))["passos"][-1]["evento"]
        self.assertEqual(evento["tipo"], "defrag")
        self.assertEqual({op: c["bytes_movidos"] for op, c in evento["opcoes"].items()},
                         {"init": 16, "end": 6, "opt": 6})

    def test_init_de_novo_muda_o_tamanho(self):
        passos = simular_roteiro("init 8\ninit 16")["passos"]
        self.assertEqual([p["tamanho"] for p in passos], [0, 8, 16])


class TestServidor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Porta 0: o sistema escolhe uma porta livre.
        cls.servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def pedir(self, caminho: str, corpo: bytes | None = None) -> tuple[int, dict]:
        """Faz GET (sem corpo) ou POST e devolve (status, JSON da resposta)."""
        pedido = urllib.request.Request(self.base + caminho, data=corpo)
        try:
            with urllib.request.urlopen(pedido) as resposta:
                return resposta.status, json.loads(resposta.read())
        except urllib.error.HTTPError as erro:
            return erro.code, json.loads(erro.read())

    def test_simular(self):
        corpo = json.dumps({"roteiro": "init 32\nalloc 8 next"}).encode()
        status, dados = self.pedir("/api/simular", corpo)
        self.assertEqual(status, 200)
        self.assertEqual(len(dados["passos"]), 3)

    def test_simular_com_pedido_invalido(self):
        for corpo in (b"isto nao e json", b'{"outra": 1}', b'{"roteiro": 5}'):
            with self.subTest(corpo=corpo):
                status, dados = self.pedir("/api/simular", corpo)
                self.assertEqual(status, 400)
                self.assertIn("erro", dados)

    def test_lista_os_roteiros_de_exemplo(self):
        status, dados = self.pedir("/api/roteiros")
        self.assertEqual(status, 200)
        self.assertIn("exemplo-nextfit.cmd", [r["nome"] for r in dados])

    def test_rota_desconhecida(self):
        status, _ = self.pedir("/api/outra", b"{}")
        self.assertEqual(status, 404)

    def test_content_length_negativo_e_recusado(self):
        conexao = http.client.HTTPConnection("127.0.0.1", self.servidor.server_address[1], timeout=5)
        conexao.putrequest("POST", "/api/simular")
        conexao.putheader("Content-Length", "-1")
        conexao.endheaders()
        self.assertEqual(conexao.getresponse().status, 400)
        conexao.close()


class TestPorta(unittest.TestCase):

    def test_porta_ocupada_usa_a_proxima(self):
        ocupado = ServidorLocal(("127.0.0.1", 0), Manipulador)
        porta = ocupado.server_address[1]
        try:
            novo = criar_servidor(porta)
            self.assertNotEqual(novo.server_address[1], porta)
            novo.server_close()
        finally:
            ocupado.server_close()


if __name__ == "__main__":
    unittest.main()
