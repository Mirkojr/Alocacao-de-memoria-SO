// Pilha de barras no tempo: uma linha por passo, como nos slides da aula.
// Só desenha: todos os números vêm prontos do servidor.

const CORES = ["#F26B6B", "#6FE04A", "#9B97F2", "#EFA855", "#6A9BF2", "#F28DD0", "#4FD1C5", "#D6C84A"];

/** Cor fixa de cada id (as cores se repetem a cada 8 ids). */
export function corDoBloco(id) {
  return CORES[(id - 1) % CORES.length];
}

/** Escapa o texto vindo do roteiro antes de colocá-lo no HTML. */
export function escapar(texto) {
  const trocas = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return String(texto).replace(/[&<>"']/g, (c) => trocas[c]);
}

/** Posição em % da largura da barra. */
const pct = (valor, total) => `${(100 * valor) / total}%`;

/**
 * Barra da memória: blocos coloridos e buracos em cinza, com largura proporcional.
 * `marcas` dá uma classe extra a um segmento pelo endereço inicial (novo, unido, movido).
 */
export function barra(blocos, tamanho, { marcas = new Map(), extra = "", classe = "" } = {}) {
  if (!tamanho) return `<div class="barra vazia ${classe}"></div>`;
  const segmentos = blocos.map((b) => {
    const livre = b.id === null;
    // Cada bloco mostra id, endereço e tamanho (pedido do enunciado); o buraco, tamanho e endereço.
    const texto = livre
      ? `<span>${b.tamanho} B</span><span class="pos">@${b.inicio}</span>`
      : `<span>id=${b.id}</span><span class="pos">@${b.inicio} +${b.tamanho}B</span>`;
    const dica = livre ? `buraco @${b.inicio} +${b.tamanho}B` : `bloco id=${b.id} @${b.inicio} +${b.tamanho}B`;
    const cor = livre ? "" : `background:${corDoBloco(b.id)};`;
    return `<div class="segmento ${livre ? "buraco" : "bloco"} ${marcas.get(b.inicio) ?? ""}"
      style="left:${pct(b.inicio, tamanho)};width:${pct(b.tamanho, tamanho)};${cor}"
      title="${dica}">${texto}</div>`;
  });
  return `<div class="barra ${classe}">${segmentos.join("")}${extra}</div>`;
}

/**
 * Desenha a escala de endereços e todas as linhas do roteiro.
 * `animar` liga o fade curto do passo atual (só ao navegar, não ao redimensionar a janela).
 */
export function desenharHistorico(lista, escala, passos, atual, animar = false) {
  // Antes do primeiro comando ainda não há memória: usa o tamanho do primeiro init.
  const tamanho = passos[atual]?.tamanho || passos.find((p) => p.tamanho)?.tamanho || 0;
  // Barra estreita (tela pequena) usa 4 divisões para os números não se encostarem.
  escala.innerHTML = desenharEscala(tamanho, escala.clientWidth < 420 ? 4 : 8);
  lista.classList.toggle("animar", animar);
  lista.innerHTML = passos.slice(1).map((p) => linha(p, passos[p.numero - 1], atual)).join("");
  manterVisivel(lista, lista.querySelector(".atual"));
}

/** Rola só a caixa do histórico (não a página) para o passo atual ficar à vista. */
function manterVisivel(lista, linhaAtual) {
  if (!linhaAtual) return;
  const topo = linhaAtual.offsetTop;
  const fundo = topo + linhaAtual.offsetHeight;
  if (topo < lista.scrollTop || fundo > lista.scrollTop + lista.clientHeight) {
    lista.scrollTop = topo - lista.clientHeight / 3;
  }
}

/** Endereços em `divisoes` partes iguais: 0, ..., tamanho. */
function desenharEscala(tamanho, divisoes) {
  if (!tamanho) return "";
  const rotulos = [];
  for (let i = 0; i <= divisoes; i++) {
    const endereco = Math.round((tamanho * i) / divisoes);
    rotulos.push(`<span style="left:${pct(endereco, tamanho)}">${endereco}</span>`);
  }
  return rotulos.join("");
}

/** Botão com número e comando: clicar na linha (ou Enter no botão) leva a esse passo. */
function botaoDoPasso(passo, extra = "") {
  return `<button type="button" class="cmd ${extra}" title="Ir para o passo ${passo.numero}"
    aria-label="Ir para o passo ${passo.numero}: ${escapar(passo.comando)}"><span class="n">${passo.numero}</span>`;
}

/** Uma linha: comando | barra | ponteiro. Passos futuros aparecem só com o comando. */
function linha(passo, anterior, atual) {
  if (passo.numero > atual) {
    return `<div class="linha futura" data-passo="${passo.numero}">
      ${botaoDoPasso(passo)}${escapar(passo.comando)}</button>
      <div class="trilho"><div class="barra vazia"></div></div>
      <span class="ptr"></span>
    </div>`;
  }

  const evento = passo.evento;
  const ehAtual = passo.numero === atual;
  const falhou = Boolean(evento.erro);
  const classes = ["linha", ehAtual ? "atual" : "", ehAtual && falhou ? "com-erro" : ""].join(" ");

  let trilho = barra(passo.blocos, passo.tamanho);
  if (ehAtual) {
    // Só o passo atual mostra o que mudou: setas, destaques, ponteiro e buracos examinados.
    const ponteiro = passo.tamanho
      ? `<div class="marca-ponteiro" style="left:${pct(passo.ponteiro, passo.tamanho)}" title="ponteiro @${passo.ponteiro}"></div>`
      : "";
    trilho = setas(evento, passo.tamanho)
      + barra(passo.blocos, passo.tamanho, { marcas: destaques(evento), extra: ponteiro })
      + faixa(evento, passo)
      + (falhou ? `<div class="erro-linha">${escapar(evento.erro)}</div>` : "");
  }

  return `<div class="${classes}" data-passo="${passo.numero}">
    ${botaoDoPasso(passo, falhou ? "falhou" : "")}${falhou ? "✗ " : ""}${escapar(passo.comando)}</button>
    <div class="trilho">${trilho}</div>
    <span class="ptr">${textoPonteiro(passo, anterior, ehAtual)}</span>
  </div>`;
}

/** "@28 → @6" quando o ponteiro mudou no passo atual; senão só a posição. */
function textoPonteiro(passo, anterior, ehAtual) {
  if (!passo.tamanho) return "—";
  if (ehAtual && anterior?.tamanho && anterior.ponteiro !== passo.ponteiro) {
    return `@${anterior.ponteiro} → @${passo.ponteiro}`;
  }
  return `@${passo.ponteiro}`;
}

/** Segmentos que mudaram no passo, pelo endereço inicial. */
function destaques(evento) {
  if (evento.erro) return new Map();
  switch (evento.tipo) {
    case "alloc": return new Map([[evento.bloco.inicio, "novo"]]);
    case "free": return new Map([[evento.resultado.inicio, "unido"]]);
    case "defrag": return new Map(evento.movidos.map((m) => [m.para, "movido"]));
    default: return new Map();
  }
}

/** Número dentro de um círculo (①, ②...) para a ordem em que os buracos foram examinados. */
const ordem = (i) => (i < 20 ? String.fromCharCode(0x2460 + i) : `${i + 1}.`);

/** Marcas embaixo da barra: buracos examinados no alloc, coalescência no free. */
function faixa(evento, passo) {
  if (evento.erro || !passo.tamanho) return "";
  const marca = (b, classe, texto) =>
    `<div class="marca ${classe}" style="left:${pct(b.inicio, passo.tamanho)};width:${pct(b.tamanho, passo.tamanho)}">${texto}</div>`;

  if (evento.tipo === "alloc") {
    const marcas = evento.examinados.map((b, i) => {
      if (b.inicio === evento.escolhido.inicio) return marca(b, "escolhido", `${ordem(i)} escolhido`);
      return marca(b, "examinado", `${ordem(i)} ${b.tamanho < evento.pedido ? "não cabe" : "cabe"}`);
    });
    return `<div class="faixa">${marcas.join("")}</div>`;
  }
  if (evento.tipo === "free") {
    const r = evento.resultado;
    const texto = evento.unidos.length > 1 ? `coalescência → @${r.inicio} +${r.tamanho}B` : "liberado";
    return `<div class="faixa">${marca(r, "uniao", texto)}</div>`;
  }
  return "";
}

/** Setas pontilhadas acima da barra: de onde cada bloco saiu para onde foi no defrag. */
function setas(evento, tamanho) {
  if (evento.erro || evento.tipo !== "defrag" || evento.movidos.length === 0) return "";
  const altura = 22 + 12 * evento.movidos.length;
  const arcos = evento.movidos.map((m, i) => {
    const inicio = Math.min(m.de, m.para);
    const direcao = m.para < m.de ? "para-esquerda" : "para-direita";
    return `<div class="seta ${direcao}" style="left:${pct(inicio, tamanho)};width:${pct(Math.abs(m.de - m.para), tamanho)};height:${altura - 16 - 12 * i}px">
      <span class="rotulo">id=${m.id}</span></div>`;
  });
  return `<div class="setas" style="height:${altura}px">${arcos.join("")}</div>`;
}
