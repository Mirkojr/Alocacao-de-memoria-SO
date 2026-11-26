// Aba "Roteiro": mostra o texto do roteiro carregado, deixa editar ali mesmo e executar de novo.
// Quem simula continua sendo o servidor: o editor só entrega o texto para o main.js.

const $ = (id) => document.getElementById(id);

const editor = {
  base: "",          // texto em execução (o que gerou os passos mostrados agora)
  passos: 0,         // quantos passos esse texto gerou
  aoExecutar: null,  // função do main.js que simula um texto
};

/** Liga abas, botões e atalhos. `executar(texto)` é chamada ao clicar em Executar. */
export function iniciarEditor(executar) {
  editor.aoExecutar = executar;
  const campo = $("editor-texto");

  campo.addEventListener("input", atualizar);
  // Os números de linha rolam junto com o texto.
  campo.addEventListener("scroll", () => { $("editor-linhas").scrollTop = campo.scrollTop; });
  campo.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" && (evento.ctrlKey || evento.metaKey)) {
      evento.preventDefault();
      executarTexto();
    }
  });

  $("btn-executar").addEventListener("click", executarTexto);
  $("btn-desfazer").addEventListener("click", () => {
    campo.value = editor.base;
    atualizar();
  });

  $("aba-passo").addEventListener("click", () => mostrarAba("passo"));
  $("aba-roteiro").addEventListener("click", () => mostrarAba("roteiro"));
  atualizar();
}

/** Coloca no editor o texto que acabou de ser executado (vindo de um arquivo ou do próprio editor). */
export function definirTexto(texto, passos) {
  editor.base = texto;
  editor.passos = passos;
  $("editor-texto").value = texto;
  atualizar();
}

/** Coloca no editor um texto que não chegou a executar (ex.: arquivo com erro), para corrigir ali. */
export function colocarTextoNaoExecutado(texto) {
  editor.base = "";
  editor.passos = 0;
  $("editor-texto").value = texto;
  atualizar();
}

/** Mostra no editor um erro de execução (ex.: roteiro sem comandos). */
export function avisarNoEditor(texto) {
  const status = $("editor-status");
  status.dataset.estado = "erro";
  status.textContent = texto;
}

/** Mostra a aba "passo" ou "roteiro". */
function mostrarAba(nome) {
  const roteiro = nome === "roteiro";
  $("aba-passo").setAttribute("aria-selected", String(!roteiro));
  $("aba-roteiro").setAttribute("aria-selected", String(roteiro));
  $("painel-passo").hidden = roteiro;
  $("painel-roteiro").hidden = !roteiro;
  if (roteiro) $("editor-texto").focus();
}

function executarTexto() {
  editor.aoExecutar?.($("editor-texto").value);
}

/** Atualiza números de linha, aviso de alteração e o botão Desfazer. */
function atualizar() {
  const texto = $("editor-texto").value;
  const linhas = texto.split("\n").length;
  $("editor-linhas").textContent = Array.from({ length: linhas }, (_, i) => i + 1).join("\n");

  const alterado = texto !== editor.base;
  const status = $("editor-status");
  if (alterado) {
    status.dataset.estado = "alterado";
    status.textContent = "Alterado, ainda não executado";
  } else if (editor.base) {
    status.dataset.estado = "executado";
    status.textContent = `Em execução: ${editor.passos} passo(s)`;
  } else {
    status.dataset.estado = "";
    status.textContent = "Nenhum roteiro carregado. Digite os comandos e clique em Executar.";
  }
  $("marca-alterado").hidden = !alterado;
  $("btn-desfazer").disabled = !alterado;
}
