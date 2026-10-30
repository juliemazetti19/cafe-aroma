// Funções compartilhadas por todas as páginas: comunicação com a API e utilidades de tela.

const Api = {
  async requisitar(metodo, url, corpo, token) {
    const opcoes = { method: metodo, headers: {} };
    if (corpo !== undefined) {
      opcoes.headers["Content-Type"] = "application/json";
      opcoes.body = JSON.stringify(corpo);
    }
    if (token) opcoes.headers.Authorization = "Bearer " + token;

    let resposta;
    try {
      resposta = await fetch(url, opcoes);
    } catch {
      throw new Error("Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.");
    }
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      const erro = new Error(dados.erro || `Erro inesperado (${resposta.status}).`);
      erro.status = resposta.status;
      throw erro;
    }
    return dados;
  },
  get(url, token) { return this.requisitar("GET", url, undefined, token); },
  post(url, corpo, token) { return this.requisitar("POST", url, corpo, token); },
  put(url, corpo, token) { return this.requisitar("PUT", url, corpo, token); },
  patch(url, corpo, token) { return this.requisitar("PATCH", url, corpo, token); },
};

const NOMES_STATUS = {
  RECEBIDO: "Recebido",
  EM_PREPARO: "Em preparo",
  PRONTO: "Pronto",
  SAIU_PARA_ENTREGA: "Saiu para entrega",
  CONCLUIDO: "Concluído",
  CANCELADO: "Cancelado",
};
const NOMES_PAGAMENTO = { PIX: "PIX", CARTAO: "Cartão", DINHEIRO: "Dinheiro" };
const NOMES_ENTREGA = { RETIRADA: "Retirada no balcão", ENTREGA: "Entrega" };

function formatarPreco(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatarDataHora(texto) {
  // O servidor envia "AAAA-MM-DD HH:MM:SS" no horário local da cafeteria.
  const [data, hora] = texto.split(" ");
  const [ano, mes, dia] = data.split("-");
  return `${dia}/${mes}/${ano} ${hora.slice(0, 5)}`;
}

function formatarTelefone(digitos) {
  const d = digitos.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d.length ? `(${d}` : "";
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

// Cria um elemento usando textContent (nunca innerHTML com dados do usuário).
function criarElemento(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined && texto !== null) elemento.textContent = texto;
  return elemento;
}

let temporizadorToast;
function mostrarToast(mensagem, tipo = "") {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = mensagem;
  toast.className = `toast visivel ${tipo}`;
  clearTimeout(temporizadorToast);
  temporizadorToast = setTimeout(() => { toast.className = "toast"; }, 3200);
}
