"""Memória simulada: o estado e os métodos pedidos no enunciado."""

import formatacao
from algoritmos import ESTRATEGIAS
from bloco import Bloco, FitAlg, Option
from defrag import calcular_opcoes


class ErroSimulador(Exception):
    """Operação inválida. A mensagem já vem pronta para ser impressa."""


class Memoria:
    """Memória como lista de blocos contíguos, em ordem de endereço.

    A lista cobre a memória inteira, alternando blocos alocados e buracos.
    Nunca há dois buracos vizinhos: ao liberar, eles são unidos.
    """

    def __init__(self) -> None:
        self.tamanho = 0                  # 0 = ainda não houve init
        self.blocos: list[Bloco] = []
        self.proximo_id = 1
        self.ponteiro = 0                 # ponteiro do Next Fit

    # ---- Métodos do enunciado ----

    def init(self, tamanho: int) -> dict:
        """Cria a memória com um único buraco e reinicia ids e ponteiro."""
        if tamanho <= 0:
            raise ErroSimulador(formatacao.ERRO_TAMANHO)
        self.tamanho = tamanho
        self.blocos = [Bloco(0, tamanho)]
        self.proximo_id = 1
        self.ponteiro = 0
        return {"tipo": "init", "tamanho": tamanho}

    def alloc(self, tamanho: int, alg: FitAlg) -> dict:
        """Aloca `tamanho` bytes no buraco escolhido pelo algoritmo `alg`."""
        self._exigir_init()
        if tamanho <= 0:
            raise ErroSimulador(formatacao.ERRO_TAMANHO)
        try:
            alg = FitAlg(alg)             # aceita FitAlg.NEXT ou o texto "next"
        except ValueError:
            raise ErroSimulador(formatacao.erro_algoritmo_invalido(alg)) from None

        escolhido, examinados = ESTRATEGIAS[alg](self.buracos(), tamanho, self.ponteiro)
        if escolhido is None:
            # Sem espaço: a memória não muda, nenhum id é consumido e o ponteiro fica.
            stats = self.stats()
            raise ErroSimulador(formatacao.erro_sem_espaco(
                tamanho, stats["livre"], stats["maior_buraco"]))

        # O bloco ocupa o início do buraco; a sobra continua livre.
        novo = Bloco(escolhido.inicio, tamanho, self.proximo_id)
        sobra = escolhido.tamanho - tamanho
        pedaco = [novo] + ([Bloco(novo.fim, sobra)] if sobra else [])
        i = self.blocos.index(escolhido)
        self.blocos[i:i + 1] = pedaco

        self.proximo_id += 1          # ids nunca são reaproveitados
        # Decisão nossa: qualquer alloc move o ponteiro ("logo após o último bloco alocado").
        self.ponteiro = novo.fim
        return {
            "tipo": "alloc",
            "algoritmo": alg.value,
            "pedido": tamanho,
            "examinados": [_resumo(b) for b in examinados],
            "escolhido": _resumo(escolhido),
            "bloco": _resumo(novo),
        }

    def free_id(self, id_bloco: int) -> dict:
        """Libera o bloco com esse id."""
        self._exigir_init()
        bloco = next((b for b in self.blocos if b.id == id_bloco), None)
        if bloco is None:
            raise ErroSimulador(formatacao.erro_id_inexistente(id_bloco))
        return self._liberar(bloco)

    def free_addr(self, endereco: int) -> dict:
        """Libera o bloco alocado que começa nesse endereço."""
        self._exigir_init()
        bloco = next((b for b in self.blocos
                      if b.inicio == endereco and not b.livre), None)
        if bloco is None:
            raise ErroSimulador(formatacao.erro_endereco_invalido(endereco))
        return self._liberar(bloco)

    def show(self) -> str:
        """Texto do comando show: mapa, blocos ativos e estatísticas."""
        self._exigir_init()
        return formatacao.formatar_show(self)

    def stats(self) -> dict:
        """Métricas de uso e de fragmentação externa."""
        self._exigir_init()
        buracos = self.buracos()
        ocupado = sum(b.tamanho for b in self.blocos if not b.livre)
        return {
            "tamanho": self.tamanho,
            "ocupado": ocupado,
            "livre": self.tamanho - ocupado,
            "buracos": len(buracos),
            "maior_buraco": max((b.tamanho for b in buracos), default=0),
            "uso": 100 * ocupado / self.tamanho,
        }

    def defrag(self, option: Option) -> dict:
        """Compacta a memória com a opção INIT, END ou OPT."""
        self._exigir_init()
        try:
            option = Option(option)       # aceita Option.OPT ou o texto "opt"
        except ValueError:
            raise ErroSimulador(formatacao.erro_opcao_invalida(option)) from None

        opcoes = calcular_opcoes(self.blocos, self.tamanho)
        escolhida = opcoes[option]
        self.blocos = escolhida["blocos"]
        self.ponteiro = 0                 # após o defrag, o ponteiro do Next Fit volta a 0
        return {
            "tipo": "defrag",
            "opcao": option.value,
            "k": escolhida["k"],
            "movidos": escolhida["movidos"],
            "bytes_movidos": escolhida["bytes_movidos"],
            # Custo e layout das três opções, para a tela comparar.
            "opcoes": {op.value: {"k": c["k"],
                                  "blocos_movidos": len(c["movidos"]),
                                  "bytes_movidos": c["bytes_movidos"],
                                  "blocos": [_resumo(b) for b in c["blocos"]]}
                       for op, c in opcoes.items()},
        }

    # ---- Apoio ----

    def buracos(self) -> list[Bloco]:
        """Buracos livres em ordem de endereço."""
        return [b for b in self.blocos if b.livre]

    def _exigir_init(self) -> None:
        """Erro se ainda não houve init (init deve ser o primeiro comando)."""
        if self.tamanho == 0:
            raise ErroSimulador(formatacao.ERRO_SEM_INIT)

    def _liberar(self, bloco: Bloco) -> dict:
        """Transforma o bloco em buraco e o une aos buracos vizinhos."""
        i = self.blocos.index(bloco)
        ini, fim = i, i + 1
        # Coalescência: inclui o buraco da esquerda e o da direita, se houver.
        if i > 0 and self.blocos[i - 1].livre:
            ini = i - 1
        if i + 1 < len(self.blocos) and self.blocos[i + 1].livre:
            fim = i + 2
        unidos = self.blocos[ini:fim]
        resultado = Bloco(unidos[0].inicio, sum(b.tamanho for b in unidos))
        self.blocos[ini:fim] = [resultado]
        # Liberar não move o ponteiro do Next Fit.
        return {
            "tipo": "free",
            "bloco": _resumo(bloco),
            "unidos": [_resumo(b) for b in unidos],   # mais de 1 = houve coalescência
            "resultado": _resumo(resultado),
        }


def _resumo(bloco: Bloco) -> dict:
    """Bloco como dicionário simples (para eventos e JSON)."""
    return {"inicio": bloco.inicio, "tamanho": bloco.tamanho, "id": bloco.id}
