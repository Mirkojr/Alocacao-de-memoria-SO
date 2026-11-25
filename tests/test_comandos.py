"""Testes da leitura de comandos (comandos.py) e da CLI (main.py).

Rodar com: python -m unittest discover -s tests -v
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from comandos import executar, interpretar  # noqa: E402
from memoria import Memoria  # noqa: E402


def rodar(*linhas: str) -> tuple[Memoria, list[dict]]:
    """Executa as linhas numa memória nova e devolve a memória e os eventos."""
    memoria = Memoria()
    eventos = [executar(memoria, interpretar(linha)) for linha in linhas]
    return memoria, eventos


class TestInterpretar(unittest.TestCase):

    def test_ignora_linha_vazia_e_comentario(self):
        for linha in ("", "   ", "# comentário", "  # recuado"):
            self.assertIsNone(interpretar(linha))

    def test_ignora_o_bom_do_inicio_do_arquivo(self):
        self.assertEqual(interpretar("﻿init 64").nome, "init")

    def test_separa_nome_e_argumentos(self):
        comando = interpretar("  ALLOC 6 Next ")
        self.assertEqual((comando.nome, comando.args, comando.texto),
                         ("alloc", ["6", "Next"], "ALLOC 6 Next"))


class TestExecutar(unittest.TestCase):

    def test_init_alloc_e_free_sao_silenciosos(self):
        _, eventos = rodar("init 16", "alloc 4 first", "freeaddr 0", "alloc 4 next", "freeid 2")
        for evento in eventos:
            self.assertIsNone(evento["erro"])
            self.assertIsNone(evento["saida"])

    def test_show_stats_e_defrag_tem_saida(self):
        _, eventos = rodar("init 16", "alloc 4 BEST", "show", "stats", "defrag OPT")
        self.assertTrue(eventos[2]["saida"].startswith("Mapa de Memória (16 bytes)"))
        self.assertTrue(eventos[3]["saida"].startswith("== Estatísticas =="))
        self.assertEqual(eventos[4]["saida"], "Defrag OPT: 0 bloco(s) movido(s), 0 bytes deslocados")

    def test_comando_invalido(self):
        for linha in ("aloc 8 first", "alloc 8", "alloc oito first", "init 1 2", "show tudo"):
            with self.subTest(linha=linha):
                _, eventos = rodar("init 16", linha)
                self.assertEqual(eventos[1]["erro"], f"Erro: comando inválido: {linha}")
                self.assertEqual(eventos[1]["saida"], eventos[1]["erro"])

    def test_erro_nao_muda_a_memoria(self):
        memoria, eventos = rodar("init 16", "alloc 10 first", "alloc 8 best")
        self.assertTrue(eventos[2]["erro"].startswith("Erro: sem espaço contíguo"))
        self.assertEqual(len(memoria.blocos), 2)

    def test_evento_guarda_o_texto_do_comando(self):
        _, eventos = rodar("init 16")
        self.assertEqual(eventos[0]["comando"], "init 16")


class TestCLI(unittest.TestCase):

    def cli(self, *args: str, entrada: str | None = None) -> subprocess.CompletedProcess:
        """Roda python src/main.py como o usuário rodaria no terminal."""
        return subprocess.run([sys.executable, str(RAIZ / "src" / "main.py"), *args],
                              input=entrada, capture_output=True, text=True, encoding="utf-8")

    def saida_esperada_da_sessao(self) -> str:
        """Comandos ecoados com '> ' seguidos do show do exemplo do PDF."""
        memoria, _ = rodar("init 64", "alloc 10 first", "alloc 8 first", "freeid 2", "alloc 6 best")
        ecos = ["> init 64", "> alloc 10 first", "> alloc 8 first",
                "> freeid 2", "> alloc 6 best", "> show"]
        return "\n".join(ecos + [memoria.show()]) + "\n"

    def test_roteiro_por_argumento(self):
        resultado = self.cli(str(RAIZ / "roteiros" / "exemplo-sessao.cmd"))
        self.assertEqual(resultado.stdout, self.saida_esperada_da_sessao())

    def test_roteiro_pela_entrada_padrao(self):
        texto = (RAIZ / "roteiros" / "exemplo-sessao.cmd").read_text(encoding="utf-8")
        resultado = self.cli(entrada=texto)
        self.assertEqual(resultado.stdout, self.saida_esperada_da_sessao())

    def test_roteiro_com_erro_imprime_a_mensagem(self):
        resultado = self.cli(str(RAIZ / "roteiros" / "exemplo-erro.cmd"))
        self.assertIn("Erro: sem espaço contíguo para 24 bytes (livre total: 20, maior buraco: 20)",
                      resultado.stdout)

    def test_roteiro_salvo_com_bom_ou_em_utf16(self):
        texto = (RAIZ / "roteiros" / "exemplo-sessao.cmd").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as pasta:
            com_bom = Path(pasta) / "com-bom.cmd"
            com_bom.write_text(texto, encoding="utf-8-sig")
            self.assertEqual(self.cli(str(com_bom)).stdout, self.saida_esperada_da_sessao())

            utf16 = Path(pasta) / "utf16.cmd"
            utf16.write_text(texto, encoding="utf-16")
            resultado = self.cli(str(utf16))
            self.assertNotEqual(resultado.returncode, 0)
            self.assertIn("salve o roteiro em UTF-8", resultado.stderr)

    def test_roteiro_inexistente(self):
        resultado = self.cli("nao-existe.cmd")
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("roteiro não encontrado", resultado.stderr)


if __name__ == "__main__":
    unittest.main()
