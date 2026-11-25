"""Testes que reproduzem os exemplos do enunciado e os casos de borda.

Rodar com: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bloco import FitAlg  # noqa: E402
from memoria import ErroSimulador, Memoria  # noqa: E402


def layout(memoria: Memoria) -> list[tuple]:
    """Memória como lista de (início, tamanho, id) para comparar fácil."""
    return [(b.inicio, b.tamanho, b.id) for b in memoria.blocos]


class TestExemplosDoEnunciado(unittest.TestCase):

    def test_sessao_de_exemplo_show(self):
        """init 64, alloc 10 first, alloc 8 first, freeid 2, alloc 6 best, show."""
        m = Memoria()
        m.init(64)
        m.alloc(10, FitAlg.FIRST)
        m.alloc(8, FitAlg.FIRST)
        m.free_id(2)
        m.alloc(6, FitAlg.BEST)
        esperado = "\n".join([
            "Mapa de Memória (64 bytes)",
            "-" * 66,
            "[" + "#" * 16 + "." * 48 + "]",
            "[" + "1" * 10 + "3" * 6 + "." * 48 + "]",
            "-" * 66,
            "",
            "Blocos ativos: [id=1] @0 +10B (usado=10B) | [id=3] @10 +6B (usado=6B)",
            "== Estatísticas ==",
            "Tamanho total: 64 bytes",
            "Ocupado: 16 bytes | Livre: 48 bytes",
            "Buracos (fragmentação externa): 1",
            "Maior buraco livre: 48 bytes",
            "Uso efetivo: 25.00%",
        ])
        self.assertEqual(m.show(), esperado)

    def test_tabela_do_next_fit(self):
        """Os 7 passos da tabela do Next Fit (memória de 32 bytes)."""
        m = Memoria()
        m.init(32)
        self.assertEqual(m.ponteiro, 0)

        passos = [
            # (operação, layout esperado, ponteiro esperado)
            (lambda: m.alloc(8, FitAlg.NEXT), [(0, 8, 1), (8, 24, None)], 8),
            (lambda: m.alloc(8, FitAlg.NEXT), [(0, 8, 1), (8, 8, 2), (16, 16, None)], 16),
            (lambda: m.alloc(8, FitAlg.NEXT),
             [(0, 8, 1), (8, 8, 2), (16, 8, 3), (24, 8, None)], 24),
            (lambda: m.free_id(1),
             [(0, 8, None), (8, 8, 2), (16, 8, 3), (24, 8, None)], 24),
            # O First Fit usaria @0; o Next Fit parte do ponteiro e usa @24.
            (lambda: m.alloc(4, FitAlg.NEXT),
             [(0, 8, None), (8, 8, 2), (16, 8, 3), (24, 4, 4), (28, 4, None)], 28),
            # @28 +4B não comporta 6: a busca volta ao início e usa @0.
            (lambda: m.alloc(6, FitAlg.NEXT),
             [(0, 6, 5), (6, 2, None), (8, 8, 2), (16, 8, 3), (24, 4, 4), (28, 4, None)], 6),
        ]
        for operacao, esperado, ponteiro in passos:
            operacao()
            self.assertEqual(layout(m), esperado)
            self.assertEqual(m.ponteiro, ponteiro)

        self.assertEqual(m.stats(), {
            "tamanho": 32, "ocupado": 26, "livre": 6,
            "buracos": 2, "maior_buraco": 4, "uso": 81.25,
        })

    def test_next_fit_registra_buracos_examinados(self):
        """No último passo da tabela, @28 é examinado antes de @0 ser escolhido."""
        m = Memoria()
        m.init(32)
        for _ in range(3):
            m.alloc(8, FitAlg.NEXT)
        m.free_id(1)
        m.alloc(4, FitAlg.NEXT)
        evento = m.alloc(6, FitAlg.NEXT)
        self.assertEqual([b["inicio"] for b in evento["examinados"]], [28, 0])
        self.assertEqual(evento["escolhido"]["inicio"], 0)


class TestAlgoritmos(unittest.TestCase):

    def memoria_com_buracos(self) -> Memoria:
        """Buracos de 6, 4 e 6 bytes (@0, @10 e @18), separados por blocos."""
        m = Memoria()
        m.init(24)
        for tamanho in (6, 4, 4, 4, 6):
            m.alloc(tamanho, FitAlg.FIRST)
        m.free_id(1)
        m.free_id(3)
        m.free_id(5)
        return m

    def test_first_fit_usa_o_primeiro_que_cabe(self):
        m = self.memoria_com_buracos()
        self.assertEqual(m.alloc(5, FitAlg.FIRST)["bloco"]["inicio"], 0)

    def test_best_fit_usa_o_menor_que_cabe(self):
        m = self.memoria_com_buracos()
        self.assertEqual(m.alloc(4, FitAlg.BEST)["bloco"]["inicio"], 10)

    def test_worst_fit_usa_o_maior(self):
        m = self.memoria_com_buracos()
        self.assertEqual(m.alloc(2, FitAlg.WORST)["bloco"]["inicio"], 0)

    def test_worst_fit_falha_se_o_maior_nao_cabe(self):
        m = self.memoria_com_buracos()
        with self.assertRaises(ErroSimulador):
            m.alloc(7, FitAlg.WORST)

    def test_next_fit_com_ponteiro_no_fim_volta_ao_inicio(self):
        m = Memoria()
        m.init(16)
        m.alloc(4, FitAlg.NEXT)
        m.alloc(12, FitAlg.NEXT)      # ponteiro vai para 16, o fim da memória
        m.free_id(1)
        self.assertEqual(m.alloc(4, FitAlg.NEXT)["bloco"]["inicio"], 0)
        self.assertEqual(m.ponteiro, 4)

    def test_empate_vale_o_menor_endereco(self):
        # Os buracos @0 e @18 têm 6 bytes: Best e Worst ficam com @0.
        m = self.memoria_com_buracos()
        self.assertEqual(m.alloc(6, FitAlg.BEST)["bloco"]["inicio"], 0)
        m = self.memoria_com_buracos()
        self.assertEqual(m.alloc(6, FitAlg.WORST)["bloco"]["inicio"], 0)


class TestCasosDeBorda(unittest.TestCase):

    def test_ids_nunca_sao_reaproveitados(self):
        m = Memoria()
        m.init(16)
        m.alloc(4, FitAlg.FIRST)
        m.free_id(1)
        self.assertEqual(m.alloc(4, FitAlg.FIRST)["bloco"]["id"], 2)

    def test_alloc_sem_espaco_nao_muda_nada(self):
        m = Memoria()
        m.init(16)
        m.alloc(10, FitAlg.FIRST)
        antes = (layout(m), m.proximo_id, m.ponteiro)
        with self.assertRaises(ErroSimulador) as erro:
            m.alloc(8, FitAlg.FIRST)
        self.assertEqual(str(erro.exception),
                         "Erro: sem espaço contíguo para 8 bytes (livre total: 6, maior buraco: 6)")
        self.assertEqual((layout(m), m.proximo_id, m.ponteiro), antes)

    def test_freeaddr_exige_inicio_de_bloco_alocado(self):
        m = Memoria()
        m.init(16)
        m.alloc(4, FitAlg.FIRST)
        with self.assertRaises(ErroSimulador):
            m.free_addr(2)        # meio do bloco
        with self.assertRaises(ErroSimulador):
            m.free_addr(4)        # início de um buraco
        m.free_addr(0)
        self.assertEqual(layout(m), [(0, 16, None)])

    def test_freeid_inexistente_e_erro(self):
        m = Memoria()
        m.init(16)
        with self.assertRaises(ErroSimulador):
            m.free_id(1)

    def test_coalescencia_dos_dois_lados(self):
        m = Memoria()
        m.init(12)
        for _ in range(3):
            m.alloc(4, FitAlg.FIRST)
        m.free_id(1)
        m.free_id(3)
        evento = m.free_id(2)
        self.assertEqual(layout(m), [(0, 12, None)])
        self.assertEqual(len(evento["unidos"]), 3)

    def test_liberar_nao_move_o_ponteiro(self):
        m = Memoria()
        m.init(16)
        m.alloc(4, FitAlg.NEXT)
        m.free_id(1)
        self.assertEqual(m.ponteiro, 4)

    def test_init_de_novo_reinicia_ids_e_ponteiro(self):
        m = Memoria()
        m.init(16)
        m.alloc(4, FitAlg.NEXT)
        m.init(32)
        self.assertEqual((layout(m), m.proximo_id, m.ponteiro), ([(0, 32, None)], 1, 0))

    def test_comando_antes_do_init_e_erro(self):
        with self.assertRaises(ErroSimulador):
            Memoria().alloc(4, FitAlg.FIRST)

    def test_tamanho_invalido_e_erro(self):
        m = Memoria()
        with self.assertRaises(ErroSimulador):
            m.init(0)
        m.init(8)
        with self.assertRaises(ErroSimulador):
            m.alloc(-1, FitAlg.FIRST)

    def test_algoritmo_em_texto_e_algoritmo_invalido(self):
        m = Memoria()
        m.init(8)
        self.assertEqual(m.alloc(4, "best")["algoritmo"], "best")
        with self.assertRaises(ErroSimulador):
            m.alloc(2, "fast")

    def test_show_com_id_de_dois_digitos(self):
        m = Memoria()
        m.init(12)
        for _ in range(12):
            m.alloc(1, FitAlg.FIRST)
        self.assertIn("[123456789012]", m.show())


if __name__ == "__main__":
    unittest.main()
