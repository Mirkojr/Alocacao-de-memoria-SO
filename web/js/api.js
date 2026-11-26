// Conversa com o servidor Python (src/servidor.py). A tela não simula nada sozinha.

const SEM_SERVIDOR = "Não foi possível falar com o servidor. Abra a tela com: python src/servidor.py";

/** Lista de roteiros de exemplo da pasta roteiros/: [{nome, texto}]. */
export async function buscarExemplos() {
  const resposta = await pedir("/api/roteiros");
  return resposta.json();
}

/** Manda o texto do roteiro e recebe {passos: [...]}, já simulado pelo Python. */
export async function simular(texto) {
  const resposta = await pedir("/api/simular", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ roteiro: texto }),
  });
  return resposta.json();
}

/** Lê o arquivo escolhido pelo usuário como texto. */
export function lerArquivo(arquivo) {
  return arquivo.text();
}

/** fetch com mensagens de erro em português. */
async function pedir(url, opcoes) {
  let resposta;
  try {
    resposta = await fetch(url, opcoes);
  } catch {
    throw new Error(SEM_SERVIDOR);          // página aberta sem o servidor
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new Error(corpo.erro ?? `Erro ${resposta.status} do servidor.`);
  }
  return resposta;
}
