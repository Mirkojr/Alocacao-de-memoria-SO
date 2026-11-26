// Estado da tela e controles. É o único lugar com estado: a lista de passos e o passo atual.
// Avançar, Voltar, Reproduzir e Reiniciar só mudam o índice e redesenham.

import { buscarExemplos, lerArquivo, simular } from "./api.js";
import { desenharHistorico } from "./historico.js";
import { desenharPainel, limparPainel } from "./painel.js";
import { avisarNoEditor, colocarTextoNaoExecutado, definirTexto, iniciarEditor } from "./editor.js";

const $ = (id) => document.getElementById(id);

const estado = {
  passos: [],       // retratos que vieram do servidor (passo 0 = antes do primeiro comando)
  atual: 0,         // índice do passo mostrado
  timer: null,      // reprodução automática em andamento
  carga: 0,         // conta os carregamentos; resposta de um carregamento antigo é descartada
  arquivo: null,    // {nome, texto} do exemplo ou arquivo aberto (para saber se o texto foi editado)
};

const painel = {
  contador: $("contador"), trilha: $("trilha-passos"), comando: $("comando"), explicacao: $("explicacao"),
  mensagem: $("mensagem"), stats: $("stats"), resumo: $("resumo-stats"), ativos: $("ativos"),
  custo: $("custo"), custoOpcoes: $("custo-opcoes"),
};

const ultimo = () => estado.passos.length - 1;
const tocando = () => estado.timer !== null;

// ---- Desenho ----

/** Redesenha a tela. `animar` = true ao mudar de passo (o passo atual entra com um fade curto). */
function render(animar = false) {
  const carregado = estado.passos.length > 0;
  $("vazio").hidden = carregado;
  if (carregado) {
    desenharHistorico($("historico"), $("escala"), estado.passos, estado.atual, animar);
    desenharPainel(painel, estado.passos, estado.atual);
  } else {
    $("historico").innerHTML = "";
    $("escala").innerHTML = "";
    limparPainel(painel);
  }
  atualizarBotoes(carregado);
}

function atualizarBotoes(carregado) {
  const noInicio = estado.atual === 0;
  const noFim = estado.atual >= ultimo();
  $("btn-reiniciar").disabled = !carregado || noInicio;
  $("btn-voltar").disabled = !carregado || noInicio;
  $("btn-avancar").disabled = !carregado || noFim;
  $("btn-reproduzir").disabled = !carregado || noFim || tocando();
  $("btn-pausar").disabled = !tocando();
}

// ---- Navegação ----

function irPara(indice) {
  estado.atual = Math.max(0, Math.min(indice, ultimo()));
  render(true);
}

// Avançar ou voltar manualmente pausa a reprodução (pedido do enunciado).
function avancar() { pausar(); irPara(estado.atual + 1); }
function voltar() { pausar(); irPara(estado.atual - 1); }
function reiniciar() { pausar(); irPara(0); }

/** Clique numa linha da pilha: vai direto para aquele passo (também pausa a reprodução). */
function irParaPasso(numero, peloTeclado) {
  if (numero === estado.atual) return;
  pausar();
  irPara(numero);
  // A pilha é redesenhada; quem usa teclado continua com o foco no passo escolhido.
  if (peloTeclado) document.querySelector("#historico .linha.atual .cmd")?.focus({ preventScroll: true });
}

// ---- Reprodução automática ----

/** Lê o intervalo em segundos; aceita vírgula ou ponto (0,5 ou 0.5). Inválido devolve null. */
function lerIntervalo() {
  const campo = $("intervalo");
  const segundos = Number(campo.value.trim().replace(",", "."));
  const valido = Number.isFinite(segundos) && segundos > 0;
  campo.setAttribute("aria-invalid", String(!valido));
  $("aviso-intervalo").hidden = valido;
  return valido ? segundos : null;
}

function reproduzir() {
  if (tocando() || estado.atual >= ultimo() || lerIntervalo() === null) return;
  agendarProximo();
  atualizarBotoes(true);
}

function agendarProximo() {
  const segundos = lerIntervalo();       // relido a cada passo: mudar o campo vale na hora
  if (segundos === null) { pausar(); return; }
  estado.timer = setTimeout(() => {
    estado.timer = null;
    estado.atual += 1;
    if (estado.atual < ultimo()) agendarProximo();   // para sozinha no fim do roteiro
    render(true);                                    // depois de agendar: Pausar continua ativo
  }, segundos * 1000);
}

function pausar() {
  clearTimeout(estado.timer);
  estado.timer = null;
  atualizarBotoes(estado.passos.length > 0);
}

// ---- Carregar roteiro ----

/**
 * Simula o texto e mostra o resultado. Devolve a mensagem de erro, ou null se deu certo.
 * Com `limparSeFalhar: false` (texto vindo do editor), uma falha mantém a simulação atual na tela.
 */
async function carregar(nome, texto, { limparSeFalhar = true } = {}) {
  pausar();
  const minhaCarga = ++estado.carga;
  let passos;
  try {
    ({ passos } = await simular(texto));
  } catch (erro) {
    if (minhaCarga === estado.carga && limparSeFalhar) mostrarFalha(erro.message);
    return erro.message;
  }
  if (minhaCarga !== estado.carga) return null;   // o usuário já escolheu outro roteiro
  if (passos.length < 2) {
    const aviso = `O roteiro ${nome} não tem nenhum comando.`;
    if (limparSeFalhar) mostrarFalha(aviso);
    return aviso;
  }
  estado.passos = passos;
  estado.atual = 0;
  $("nome-roteiro").textContent = `roteiro: ${nome}`;
  definirTexto(texto, passos.length - 1);         // a aba Roteiro mostra o texto em execução
  render();
  return null;
}

/** Abre um exemplo ou arquivo: guarda o original e executa. */
async function abrirRoteiro(nome, texto) {
  estado.arquivo = { nome, texto };
  const erro = await carregar(nome, texto);
  if (erro) {
    // O texto com problema vai para a aba Roteiro, para ser corrigido ali, e o erro aparece nas duas abas.
    colocarTextoNaoExecutado(texto);
    avisarNoEditor(erro);
  }
  return erro;
}

/** Executa o texto editado na aba Roteiro. */
async function executarEditado(texto) {
  const original = estado.arquivo;
  let nome = "roteiro digitado";
  if (original) nome = texto === original.texto ? original.nome : `${original.nome} (editado)`;
  const erro = await carregar(nome, texto, { limparSeFalhar: false });
  if (erro) avisarNoEditor(erro);                 // o erro aparece junto do editor, onde o usuário está
  // Rodando uma versão editada, a lista fica sem seleção: escolher o exemplo de novo recarrega o original.
  else if (original && texto !== original.texto) $("exemplos").value = "";
}

/** Limpa a tela e deixa só a mensagem de erro (ela fica até o próximo carregamento). */
function mostrarFalha(texto) {
  estado.passos = [];
  estado.atual = 0;
  $("nome-roteiro").textContent = "";
  render();
  painel.mensagem.classList.add("erro");
  painel.mensagem.textContent = texto;
}

async function iniciar() {
  try {
    const exemplos = await buscarExemplos();
    const lista = $("exemplos");
    for (const { nome, texto } of exemplos) {
      const opcao = new Option(nome, nome);
      opcao.dataset.texto = texto;
      lista.append(opcao);
    }
    // Abre direto no exemplo do Next Fit, o mais completo para a demonstração.
    const inicial = exemplos.find((e) => e.nome === "exemplo-nextfit.cmd") ?? exemplos[0];
    if (inicial) {
      lista.value = inicial.nome;
      await abrirRoteiro(inicial.nome, inicial.texto);
      return;
    }
  } catch (erro) {
    mostrarFalha(erro.message);
  }
  render();
}

// ---- Minimizar o controle ----

const controle = document.querySelector(".controle");

/** Recolhe (ou mostra) o controle flutuante e lembra a escolha para a próxima vez. */
function minimizar(recolher) {
  controle.classList.toggle("minimizado", recolher);
  const botao = $("btn-minimizar");
  botao.setAttribute("aria-expanded", String(!recolher));
  botao.setAttribute("aria-label", recolher ? "Mostrar controles" : "Minimizar controles");
  botao.title = recolher ? "Mostrar controles (M)" : "Minimizar controles (M)";
  try { localStorage.setItem("controle-minimizado", recolher ? "1" : "0"); } catch { /* sem armazenamento: só não lembra */ }
}

const alternarMinimizado = () => minimizar(!controle.classList.contains("minimizado"));

// ---- Abas da coluna da direita (Passo atual, Estatísticas, Roteiro) ----

/** Mostra o painel da aba clicada e esconde os outros. */
function mostrarAba(aba) {
  for (const outra of document.querySelectorAll('.abas [role="tab"]')) {
    const ativa = outra === aba;
    outra.setAttribute("aria-selected", String(ativa));
    $(outra.getAttribute("aria-controls")).hidden = !ativa;
  }
}

for (const aba of document.querySelectorAll('.abas [role="tab"]')) {
  aba.addEventListener("click", () => mostrarAba(aba));
}

// ---- Eventos ----

$("btn-minimizar").addEventListener("click", alternarMinimizado);

// Um único ouvinte para todas as linhas (elas são recriadas a cada passo).
$("historico").addEventListener("click", (evento) => {
  const linha = evento.target.closest(".linha");
  // detail === 0: o "clique" veio do teclado (Enter ou espaço no botão da linha).
  if (linha) irParaPasso(Number(linha.dataset.passo), evento.detail === 0);
});

$("btn-avancar").addEventListener("click", avancar);
$("btn-voltar").addEventListener("click", voltar);
$("btn-reiniciar").addEventListener("click", reiniciar);
$("btn-reproduzir").addEventListener("click", reproduzir);
$("btn-pausar").addEventListener("click", pausar);
$("intervalo").addEventListener("input", lerIntervalo);

$("exemplos").addEventListener("change", (evento) => {
  const opcao = evento.target.selectedOptions[0];
  if (opcao.value) abrirRoteiro(opcao.value, opcao.dataset.texto);
});

$("btn-arquivo").addEventListener("click", () => $("arquivo").click());
$("arquivo").addEventListener("change", async (evento) => {
  const arquivo = evento.target.files[0];
  if (!arquivo) return;
  $("exemplos").value = "";
  await abrirRoteiro(arquivo.name, await lerArquivo(arquivo));
  evento.target.value = "";             // permite escolher o mesmo arquivo de novo
});

// Atalhos de teclado (ignorados enquanto se digita no campo do intervalo).
document.addEventListener("keydown", (evento) => {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(evento.target.tagName)) return;
  if (evento.key === "m" || evento.key === "M") { alternarMinimizado(); return; }
  if (estado.passos.length === 0) return;
  if (evento.key === " " && evento.target.tagName === "BUTTON") return;   // espaço já "clica" o botão focado
  const acoes = {
    ArrowRight: avancar,
    ArrowLeft: voltar,
    Home: reiniciar,
    " ": () => (tocando() ? pausar() : reproduzir()),
  };
  if (acoes[evento.key]) {
    evento.preventDefault();
    acoes[evento.key]();
  }
});

// Redesenha ao mudar o tamanho da janela (a escala de endereços se adapta à largura).
window.addEventListener("resize", () => { if (estado.passos.length) render(); });

// Abre como ficou da última vez (minimizado ou não).
let estavaMinimizado = false;
try { estavaMinimizado = localStorage.getItem("controle-minimizado") === "1"; } catch { /* ignora */ }
minimizar(estavaMinimizado);

iniciarEditor(executarEditado);
iniciar();
