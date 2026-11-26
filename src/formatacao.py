"""Textos no formato do enunciado: mapa (show), estatísticas (stats), defrag e erros."""

# ---- Mensagens de erro ----

ERRO_SEM_INIT = "Erro: memória não inicializada (use init <tamanho>)"
ERRO_TAMANHO = "Erro: o tamanho deve ser maior que zero"


def erro_sem_espaco(pedido: int, livre: int, maior: int) -> str:
    """Texto exato do enunciado para alloc sem buraco que comporte o pedido."""
    return (f"Erro: sem espaço contíguo para {pedido} bytes "
            f"(livre total: {livre}, maior buraco: {maior})")


def erro_id_inexistente(id_bloco: int) -> str:
    """freeid com um id que não está alocado."""
    return f"Erro: não há bloco alocado com id {id_bloco}"


def erro_endereco_invalido(endereco: int) -> str:
    """freeaddr com um endereço que não é o início de um bloco alocado."""
    return f"Erro: endereço {endereco} não é o início de um bloco alocado"


def erro_algoritmo_invalido(nome) -> str:
    """alloc com algoritmo fora de first, best, worst e next."""
    return f"Erro: algoritmo inválido: {nome} (use first, best, worst ou next)"


def erro_opcao_invalida(nome) -> str:
    """defrag com opção fora de init, end e opt."""
    return f"Erro: opção de defrag inválida: {nome} (use init, end ou opt)"


def erro_comando_invalido(linha: str) -> str:
    """Comando desconhecido, com argumentos a mais/a menos ou número inválido."""
    return f"Erro: comando inválido: {linha}"


# ---- defrag ----

def formatar_defrag(evento: dict) -> str:
    """Ex.: Defrag OPT: 1 bloco(s) movido(s), 6 bytes deslocados"""
    return (f"Defrag {evento['opcao'].upper()}: "
            f"{len(evento['movidos'])} bloco(s) movido(s), "
            f"{evento['bytes_movidos']} bytes deslocados")


# ---- show e stats ----

def formatar_show(memoria) -> str:
    """Mapa em duas linhas, blocos ativos e estatísticas, como na 'Saída esperada'."""
    uso = "".join(("." if b.livre else "#") * b.tamanho for b in memoria.blocos)
    # Decisão nossa: id com 2 dígitos mostra só o último; "Blocos ativos" traz o id completo.
    ids = "".join(("." if b.livre else str(b.id % 10)) * b.tamanho for b in memoria.blocos)
    traco = "-" * (memoria.tamanho + 2)
    return "\n".join([
        f"Mapa de Memória ({memoria.tamanho} bytes)",
        traco,
        f"[{uso}]",
        f"[{ids}]",
        traco,
        "",
        "Blocos ativos: " + formatar_blocos_ativos(memoria.blocos),
        formatar_stats(memoria.stats()),
    ])


def formatar_blocos_ativos(blocos) -> str:
    """Ex.: [id=1] @0 +10B (usado=10B) | [id=3] @10 +6B (usado=6B)"""
    # Sem fragmentação interna neste simulador: usado = tamanho do bloco.
    ativos = [f"[id={b.id}] @{b.inicio} +{b.tamanho}B (usado={b.tamanho}B)"
              for b in blocos if not b.livre]
    return " | ".join(ativos) if ativos else "(nenhum)"


def formatar_stats(stats: dict) -> str:
    """Bloco de estatísticas do comando stats."""
    return "\n".join([
        "== Estatísticas ==",
        f"Tamanho total: {stats['tamanho']} bytes",
        f"Ocupado: {stats['ocupado']} bytes | Livre: {stats['livre']} bytes",
        f"Buracos (fragmentação externa): {stats['buracos']}",
        f"Maior buraco livre: {stats['maior_buraco']} bytes",
        f"Uso efetivo: {stats['uso']:.2f}%",
    ])
