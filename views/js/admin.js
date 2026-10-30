// Painel administrativo: login, acompanhamento de pedidos e cadastro de produtos.

const CHAVE_TOKEN = "cafe-aroma-token";
const INTERVALO_ATUALIZACAO_MS = 20000;

const el = (id) => document.getElementById(id);
let token = sessionStorage.getItem(CHAVE_TOKEN);
let categorias = [];
let produtoEmEdicao = null;
let temporizador;

// ---------- Sessão ----------

function mostrarTela(logado) {
  el("tela-login").hidden = logado;
  el("tela-painel").hidden = !logado;
  el("link-sair").hidden = !logado;
}

function encerrarSessao(mensagem) {
  token = null;
  sessionStorage.removeItem(CHAVE_TOKEN);
  clearTimeout(temporizador);
  mostrarTela(false);
  if (mensagem) el("erro-login").textContent = mensagem;
}

// Chama a API autenticada; se a sessão expirou, volta para o login.
async function chamar(metodo, url, corpo) {
  try {
    return await Api.requisitar(metodo, url, corpo, token);
  } catch (erro) {
    if (erro.status === 401) encerrarSessao(erro.message);
    throw erro;
  }
}

el("form-login").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const f = evento.target.elements;
  el("erro-login").textContent = "";
  try {
    const resposta = await Api.post("/api/admin/login", { login: f.login.value.trim(), senha: f.senha.value });
    token = resposta.token;
    sessionStorage.setItem(CHAVE_TOKEN, token);
    f.senha.value = "";
    iniciarPainel();
  } catch (erro) {
    el("erro-login").textContent = erro.message;
  }
});

el("link-sair").addEventListener("click", async (evento) => {
  evento.preventDefault();
  await Api.post("/api/admin/logout", {}, token).catch(() => {});
  encerrarSessao();
});

// ---------- Abas ----------

for (const aba of document.querySelectorAll(".aba")) {
  aba.addEventListener("click", () => {
    for (const outra of document.querySelectorAll(".aba")) outra.setAttribute("aria-selected", String(outra === aba));
    el("aba-pedidos").hidden = aba.dataset.aba !== "pedidos";
    el("aba-produtos").hidden = aba.dataset.aba !== "produtos";
    if (aba.dataset.aba === "produtos") carregarProdutos();
  });
}

// ---------- Resumo e pedidos ----------

async function carregarResumo() {
  const resumo = await chamar("GET", "/api/admin/resumo");
  el("resumo-pedidos").textContent = resumo.pedidos_hoje;
  el("resumo-faturamento").textContent = formatarPreco(resumo.faturamento_hoje);
  el("resumo-abertos").textContent = resumo.em_aberto;
}

function etiquetaStatus(status) {
  return criarElemento("span", `etiqueta status-${status}`, NOMES_STATUS[status]);
}

function celula(...conteudo) {
  const td = document.createElement("td");
  for (const item of conteudo) {
    if (item === null || item === undefined || item === "") continue;
    if (typeof item === "string") {
      if (td.childNodes.length) td.append(document.createElement("br"));
      td.append(item);
    } else {
      td.append(item);
    }
  }
  return td;
}

async function mudarStatus(pedido, novoStatus) {
  if (novoStatus === "CANCELADO" && !confirmarCancelamento(pedido)) return;
  try {
    await chamar("PATCH", `/api/admin/pedidos/${pedido.id}/status`, { status: novoStatus });
    mostrarToast(`Pedido ${pedido.codigo}: ${NOMES_STATUS[novoStatus]}.`, "sucesso");
    atualizarPainel();
  } catch (erro) {
    mostrarToast(erro.message, "erro");
  }
}

// Cancelamento pede um segundo clique em vez de um confirm() do navegador.
const cancelamentosPendentes = new Set();
function confirmarCancelamento(pedido) {
  if (cancelamentosPendentes.has(pedido.id)) {
    cancelamentosPendentes.delete(pedido.id);
    return true;
  }
  cancelamentosPendentes.add(pedido.id);
  mostrarToast(`Clique em "Cancelar" de novo para confirmar o cancelamento do pedido ${pedido.codigo}.`);
  setTimeout(() => cancelamentosPendentes.delete(pedido.id), 5000);
  return false;
}

async function carregarPedidos() {
  const status = el("filtro-status").value;
  const pedidos = await chamar("GET", `/api/admin/pedidos${status ? `?status=${status}` : ""}`);
  const corpo = el("tabela-pedidos");
  corpo.replaceChildren();
  if (!pedidos.length) {
    const tr = document.createElement("tr");
    const td = criarElemento("td", "vazio", "Nenhum pedido encontrado.");
    td.colSpan = 8;
    tr.append(td);
    corpo.append(tr);
  }
  for (const pedido of pedidos) {
    const tr = document.createElement("tr");
    const itens = pedido.itens.map((i) => `${i.quantidade}× ${i.nome}`).join(", ");
    const acoes = criarElemento("div", "acoes");
    for (const proximo of pedido.proximos_status) {
      const cancelar = proximo === "CANCELADO";
      const botao = criarElemento("button", `botao pequeno ${cancelar ? "perigo" : "primario"}`,
        cancelar ? "Cancelar" : `→ ${NOMES_STATUS[proximo]}`);
      botao.type = "button";
      botao.addEventListener("click", () => mudarStatus(pedido, proximo));
      acoes.append(botao);
    }
    tr.append(
      celula(criarElemento("strong", null, pedido.codigo)),
      celula(formatarDataHora(pedido.criado_em)),
      celula(pedido.cliente.nome, formatarTelefone(pedido.cliente.telefone)),
      celula(itens, pedido.observacao ? `Obs.: ${pedido.observacao}` : ""),
      celula(NOMES_ENTREGA[pedido.tipo_entrega], pedido.endereco, `Pagamento: ${NOMES_PAGAMENTO[pedido.forma_pagamento]}`),
      celula(formatarPreco(pedido.total)),
      celula(etiquetaStatus(pedido.status)),
      celula(pedido.proximos_status.length ? acoes : "—")
    );
    corpo.append(tr);
  }
  el("pedidos-atualizado").textContent = `Atualizado às ${new Date().toLocaleTimeString("pt-BR")}`;
}

async function atualizarPainel() {
  clearTimeout(temporizador);
  try {
    await Promise.all([carregarResumo(), carregarPedidos()]);
  } catch (erro) {
    if (erro.status === 401) return;
    mostrarToast(erro.message, "erro");
  }
  temporizador = setTimeout(atualizarPainel, INTERVALO_ATUALIZACAO_MS);
}

el("filtro-status").addEventListener("change", atualizarPainel);
el("btn-atualizar-pedidos").addEventListener("click", atualizarPainel);

// ---------- Produtos ----------

async function carregarProdutos() {
  let produtos;
  try {
    produtos = await chamar("GET", "/api/admin/produtos");
  } catch (erro) {
    if (erro.status !== 401) mostrarToast(erro.message, "erro");
    return;
  }
  const corpo = el("tabela-produtos");
  corpo.replaceChildren();
  for (const produto of produtos) {
    const tr = document.createElement("tr");
    if (!produto.ativo) tr.className = "inativo";
    const editar = criarElemento("button", "botao pequeno", "Editar");
    editar.type = "button";
    editar.addEventListener("click", () => abrirFormularioProduto(produto));
    const alternar = criarElemento("button", "botao pequeno", produto.ativo ? "Desativar" : "Ativar");
    alternar.type = "button";
    alternar.addEventListener("click", () => salvarProduto(produto.id, { ...produto, ativo: !produto.ativo }));
    const acoes = criarElemento("div", "acoes");
    acoes.append(editar, alternar);
    tr.append(
      celula(produto.icone),
      celula(criarElemento("strong", null, produto.nome), produto.descricao),
      celula(produto.categoria),
      celula(formatarPreco(produto.preco)),
      celula(produto.ativo ? "Disponível" : "Inativo"),
      celula(acoes)
    );
    corpo.append(tr);
  }
}

function abrirFormularioProduto(produto) {
  produtoEmEdicao = produto;
  const f = el("form-produto").elements;
  el("titulo-produto").textContent = produto ? "Editar produto" : "Novo produto";
  el("erro-produto").textContent = "";
  f.nome.value = produto?.nome ?? "";
  f.descricao.value = produto?.descricao ?? "";
  f.preco.value = produto ? produto.preco.toFixed(2) : "";
  f.categoria_id.value = produto?.categoria_id ?? categorias[0]?.id;
  f.icone.value = produto?.icone ?? "";
  f.ativo.checked = produto?.ativo ?? true;
  el("dialogo-produto").showModal();
  f.nome.focus();
}

async function salvarProduto(id, dados) {
  try {
    if (id) await chamar("PUT", `/api/admin/produtos/${id}`, dados);
    else await chamar("POST", "/api/admin/produtos", dados);
    mostrarToast("Produto salvo.", "sucesso");
    carregarProdutos();
    return true;
  } catch (erro) {
    if (el("dialogo-produto").open) el("erro-produto").textContent = erro.message;
    else mostrarToast(erro.message, "erro");
    return false;
  }
}

el("btn-novo-produto").addEventListener("click", () => abrirFormularioProduto(null));
el("btn-cancelar-produto").addEventListener("click", () => el("dialogo-produto").close());
el("form-produto").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const f = evento.target.elements;
  const dados = {
    nome: f.nome.value.trim(),
    descricao: f.descricao.value.trim(),
    preco: Number(f.preco.value.replace(",", ".")),
    categoria_id: Number(f.categoria_id.value),
    icone: f.icone.value.trim(),
    ativo: f.ativo.checked,
  };
  if (dados.nome.length < 2) return (el("erro-produto").textContent = "Informe o nome do produto.");
  if (!(dados.preco > 0)) return (el("erro-produto").textContent = "Informe um preço maior que zero.");
  if (await salvarProduto(produtoEmEdicao?.id, dados)) el("dialogo-produto").close();
});

// ---------- Inicialização ----------

async function iniciarPainel() {
  mostrarTela(true);
  try {
    categorias = await Api.get("/api/categorias");
    const select = el("select-categoria");
    select.replaceChildren(...categorias.map((c) => {
      const opcao = criarElemento("option", null, c.nome);
      opcao.value = c.id;
      return opcao;
    }));
  } catch (erro) {
    mostrarToast(erro.message, "erro");
  }
  atualizarPainel();
}

if (token) iniciarPainel();
else mostrarTela(false);
