// Coluna da direita: passo atual com explicação, mensagem de erro, estatísticas e custo do defrag.

import { barra, corDoBloco } from "./historico.js";

const NOMES = { first: "First Fit", best: "Best Fit", worst: "Worst Fit", next: "Next Fit" };

/** Atualiza toda a coluna da direita para o passo `atual`. */
export function desenharPainel(el, passos, atual) {
  const passo = passos[atual];
  const anterior = passos[atual - 1];
  el.contador.textContent = `Passo ${atual} de ${passos.length - 1}`;
  // Uma marca por passo na barra de reprodução: já executados, atual e futuros.
  el.trilha.innerHTML = passos.slice(1).map((p) =>
    `<span class="${p.numero < atual ? "feito" : p.numero === atual ? "agora" : ""}"></span>`).join("");
  el.comando.textContent = passo.comando ?? "—";
  el.explicacao.innerHTML = explicar(passo, anterior);
  desenharMensagem(el.mensagem, passo.evento);
  desenharStats(el.stats, passo);
  desenharAtivos(el.ativos, passo);
  desenharCustoDefrag(el.custo, el.custoOpcoes, passo.evento);
}

/** Volta a coluna da direita ao estado vazio (nenhum roteiro carregado). */
export function limparPainel(el) {
  el.contador.textContent = "Passo 0 de 0";
  el.trilha.innerHTML = "";
  el.comando.textContent = "—";
  el.explicacao.textContent = "";
  el.stats.innerHTML = "";
  el.ativos.innerHTML = "";
  el.custo.hidden = true;
}

/** Uma ou duas frases dizendo o que aconteceu no passo. */
function explicar(passo, anterior) {
  const e = passo.evento;
  if (!e) return "Estado inicial, antes do primeiro comando. Use <b>Avançar</b> ou <b>Reproduzir</b>.";
  if (e.erro) return "O comando falhou: a memória, os ids e o ponteiro não mudaram.";

  switch (e.tipo) {
    case "init":
      return `Memória criada com ${e.tamanho} bytes: um único buraco. Ids e ponteiro reiniciados.`;

    case "alloc": {
      const ex = e.examinados;
      const b = e.bloco;
      const sobra = e.escolhido.tamanho - b.tamanho;
      // No Next Fit, a ordem examinada "volta" quando a busca passa do fim para o endereço 0.
      const deuVolta = ex.some((h, i) => i > 0 && h.inicio < ex[i - 1].inicio);
      let texto = `<b>${NOMES[e.algoritmo]}</b>: `;
      if (e.algoritmo === "next") {
        texto += `a busca começou no ponteiro @${anterior.ponteiro}${deuVolta ? ", chegou ao fim e voltou ao endereço 0" : ""}; `;
      }
      texto += `examinou ${ex.length} buraco(s) e escolheu @${e.escolhido.inicio} +${e.escolhido.tamanho}B. `;
      texto += `Bloco <b>id=${b.id} @${b.inicio} +${b.tamanho}B</b>`;
      texto += sobra > 0 ? `; a sobra @${b.inicio + b.tamanho} +${sobra}B continua livre. ` : ". ";
      return texto + `Ponteiro: @${anterior.ponteiro} → @${passo.ponteiro}.`;
    }

    case "free": {
      const b = e.bloco;
      const r = e.resultado;
      const uniao = e.unidos.length > 1
        ? ` Coalescência: ${e.unidos.length} áreas vizinhas viram um buraco só, @${r.inicio} +${r.tamanho}B.`
        : "";
      return `Bloco <b>id=${b.id} @${b.inicio} +${b.tamanho}B</b> liberado.${uniao} O ponteiro não muda.`;
    }

    case "defrag": {
      const k = e.opcao === "opt" ? ` (k=${e.k})` : "";
      const movimentos = e.movidos.map((m) => `id=${m.id}: @${m.de} → @${m.para}`).join(", ");
      return `Defrag <b>${e.opcao.toUpperCase()}</b>${k}: ${e.movidos.length} bloco(s) movido(s), `
        + `${e.bytes_movidos} bytes deslocados${movimentos ? ` (${movimentos})` : ""}. O ponteiro volta a @0.`;
    }

    default:
      return "";
  }
}

/** Mensagem de erro do passo em vermelho, ou um aviso neutro. */
function desenharMensagem(caixa, evento) {
  const erro = evento?.erro;
  caixa.classList.toggle("erro", Boolean(erro));
  caixa.textContent = erro ?? "Sem erros neste passo.";
}

/** As cinco estatísticas do comando stats, mais o próximo id (mostra que o Voltar restaura os ids). */
function desenharStats(lista, passo) {
  const s = passo.stats;
  const itens = s
    ? [["Ocupado", `${s.ocupado} bytes`],
       ["Livre", `${s.livre} bytes`],
       ["Buracos (frag. externa)", s.buracos],
       ["Maior buraco livre", `${s.maior_buraco} bytes`],
       ["Uso efetivo", `${s.uso.toFixed(2)}%`],
       ["Próximo id", passo.proximo_id]]
    : [["Memória", "ainda não iniciada"]];
  lista.innerHTML = itens.map(([nome, valor]) => `<dt>${nome}</dt><dd>${valor}</dd>`).join("");
}

/** Lista dos blocos alocados: id, endereço e tamanho, com a cor do bloco. */
function desenharAtivos(lista, passo) {
  const ativos = passo.blocos.filter((b) => b.id !== null);
  lista.innerHTML = ativos.length
    ? ativos.map((b) => `<li><span class="cor" style="background:${corDoBloco(b.id)}"></span>`
        + `id=${b.id} @${b.inicio} +${b.tamanho}B</li>`).join("")
    : "<li>nenhum</li>";
}

/** INIT, END e OPT lado a lado (só nos passos de defrag). */
function desenharCustoDefrag(secao, caixa, evento) {
  const mostrar = evento?.tipo === "defrag" && !evento.erro;
  secao.hidden = !mostrar;
  if (!mostrar) return;

  const tamanho = evento.opcoes.init.blocos.reduce((soma, b) => soma + b.tamanho, 0);
  caixa.innerHTML = ["init", "end", "opt"].map((nome) => {
    const op = evento.opcoes[nome];
    const usada = nome === evento.opcao;
    const nota = nome === "opt" ? `k = ${op.k} (empate: vale o maior k)` : nome === "init" ? "livre no início" : "livre no fim";
    return `<div class="opcao-defrag ${usada ? "escolhida" : ""}">
      <div class="titulo"><b>${nome.toUpperCase()}${usada ? " ✓ usado" : ""}</b>
        <span>${op.blocos_movidos} bloco(s) · ${op.bytes_movidos} B</span></div>
      ${barra(op.blocos, tamanho, { classe: "mini" })}
      <span class="nota">${nota}</span>
    </div>`;
  }).join("");
}
