// Página da loja: cardápio, carrinho e finalização do pedido.

const CHAVE_CARRINHO = "cafe-aroma-carrinho";

const estado = {
  produtos: [],
  categorias: [],
  categoriaSelecionada: 0, // 0 = todas
  carrinho: carregarCarrinho(), // { [produtoId]: quantidade }
  taxaEntrega: 0,
  quantidadeMaxima: 20,
};

const el = (id) => document.getElementById(id);

function carregarCarrinho() {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE_CARRINHO) || "{}");
    return salvo && typeof salvo === "object" ? salvo : {};
  } catch {
    return {};
  }
}

function salvarCarrinho() {
  localStorage.setItem(CHAVE_CARRINHO, JSON.stringify(estado.carrinho));
}

function produtoPorId(id) {
  return estado.produtos.find((p) => p.id === Number(id));
}

function itensDoCarrinho() {
  return Object.entries(estado.carrinho)
    .map(([id, quantidade]) => ({ produto: produtoPorId(id), quantidade }))
    .filter((item) => item.produto);
}

function subtotal() {
  return itensDoCarrinho().reduce((soma, item) => soma + item.produto.preco * item.quantidade, 0);
}

// ---------- Cardápio ----------

function renderizarFiltros() {
  const container = el("filtros");
  container.replaceChildren();
  const opcoes = [{ id: 0, nome: "Todos" }, ...estado.categorias];
  for (const categoria of opcoes) {
    const botao = criarElemento("button", "filtro", categoria.nome);
    botao.type = "button";
    botao.setAttribute("role", "tab");
    botao.setAttribute("aria-selected", String(categoria.id === estado.categoriaSelecionada));
    botao.addEventListener("click", () => {
      estado.categoriaSelecionada = categoria.id;
      renderizarFiltros();
      renderizarProdutos();
    });
    container.append(botao);
  }
}

function renderizarProdutos() {
  const grade = el("grade-produtos");
  grade.replaceChildren();
  const visiveis = estado.produtos.filter(
    (p) => estado.categoriaSelecionada === 0 || p.categoria_id === estado.categoriaSelecionada
  );
  if (!visiveis.length) {
    grade.append(criarElemento("p", "vazio", "Nenhum produto nesta categoria no momento."));
    return;
  }
  for (const produto of visiveis) {
    const cartao = criarElemento("article", "cartao");
    const icone = criarElemento("div", "icone", produto.icone);
    icone.setAttribute("aria-hidden", "true");
    const rodape = criarElemento("div", "rodape");
    const botao = criarElemento("button", "botao primario pequeno", "Adicionar");
    botao.type = "button";
    botao.setAttribute("aria-label", `Adicionar ${produto.nome} ao pedido`);
    botao.addEventListener("click", () => alterarQuantidade(produto.id, 1, true));
    rodape.append(criarElemento("span", "preco", formatarPreco(produto.preco)), botao);
    cartao.append(
      icone,
      criarElemento("span", "categoria-etiqueta", produto.categoria),
      criarElemento("h3", null, produto.nome),
      criarElemento("p", null, produto.descricao),
      rodape
    );
    grade.append(cartao);
  }
}

// ---------- Carrinho ----------

function alterarQuantidade(produtoId, delta, avisar = false) {
  const atual = estado.carrinho[produtoId] || 0;
  const nova = atual + delta;
  if (nova > estado.quantidadeMaxima) {
    mostrarToast(`Limite de ${estado.quantidadeMaxima} unidades por item.`, "erro");
    return;
  }
  if (nova <= 0) delete estado.carrinho[produtoId];
  else estado.carrinho[produtoId] = nova;
  salvarCarrinho();
  renderizarCarrinho();
  if (avisar) mostrarToast(`${produtoPorId(produtoId).nome} adicionado ao pedido.`, "sucesso");
}

function renderizarCarrinho() {
  const lista = el("itens-carrinho");
  lista.replaceChildren();
  const itens = itensDoCarrinho();
  const quantidadeTotal = itens.reduce((soma, item) => soma + item.quantidade, 0);
  const vazio = itens.length === 0;

  for (const { produto, quantidade } of itens) {
    const li = criarElemento("li", "item-carrinho");
    const controles = criarElemento("div", "quantidade");
    const menos = criarElemento("button", null, "−");
    menos.type = "button";
    menos.setAttribute("aria-label", `Diminuir ${produto.nome}`);
    menos.addEventListener("click", () => alterarQuantidade(produto.id, -1));
    const mais = criarElemento("button", null, "+");
    mais.type = "button";
    mais.setAttribute("aria-label", `Aumentar ${produto.nome}`);
    mais.addEventListener("click", () => alterarQuantidade(produto.id, 1));
    controles.append(menos, criarElemento("span", null, String(quantidade)), mais);

    const remover = criarElemento("button", "remover", "Remover");
    remover.type = "button";
    remover.addEventListener("click", () => alterarQuantidade(produto.id, -quantidade));

    li.append(
      criarElemento("span", "nome", `${produto.icone} ${produto.nome}`),
      criarElemento("span", "valor", formatarPreco(produto.preco * quantidade)),
      controles,
      remover
    );
    lista.append(li);
  }

  el("carrinho-vazio").hidden = !vazio;
  el("totais-carrinho").hidden = vazio;
  el("dica-taxa").hidden = vazio;
  el("btn-limpar").hidden = vazio;
  el("btn-finalizar").disabled = vazio;
  el("subtotal-carrinho").textContent = formatarPreco(subtotal());
  el("btn-ver-carrinho").hidden = vazio;
  el("contador-flutuante").textContent = quantidadeTotal;
  el("total-flutuante").textContent = formatarPreco(subtotal());
}

// ---------- Finalização ----------

const form = el("form-checkout");

function tipoEntregaEscolhido() {
  return form.elements.tipo_entrega.value;
}

function atualizarTotaisCheckout() {
  const entrega = tipoEntregaEscolhido() === "ENTREGA";
  const taxa = entrega ? estado.taxaEntrega : 0;
  el("campo-endereco").hidden = !entrega;
  el("checkout-subtotal").textContent = formatarPreco(subtotal());
  el("checkout-taxa").textContent = entrega ? formatarPreco(taxa) : "Grátis";
  el("checkout-total").textContent = formatarPreco(subtotal() + taxa);
}

function marcarInvalido(campo, mensagem) {
  campo.setAttribute("aria-invalid", "true");
  campo.focus();
  el("erro-checkout").textContent = mensagem;
  return false;
}

function validarFormulario() {
  for (const campo of form.querySelectorAll("[aria-invalid]")) campo.removeAttribute("aria-invalid");
  el("erro-checkout").textContent = "";
  const { nome, telefone, email, endereco } = form.elements;

  if (nome.value.trim().length < 3) return marcarInvalido(nome, "Informe seu nome completo.");
  const digitos = telefone.value.replace(/\D/g, "");
  if (digitos.length < 10 || digitos.length > 11) return marcarInvalido(telefone, "Informe um telefone válido com DDD.");
  if (email.value.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.value.trim()))
    return marcarInvalido(email, "Confira o e-mail informado.");
  if (tipoEntregaEscolhido() === "ENTREGA" && endereco.value.trim().length < 10)
    return marcarInvalido(endereco, "Informe o endereço completo para a entrega.");
  return true;
}

async function enviarPedido(evento) {
  evento.preventDefault();
  if (!validarFormulario()) return;

  const f = form.elements;
  const pedido = {
    cliente: { nome: f.nome.value.trim(), telefone: f.telefone.value, email: f.email.value.trim() },
    tipo_entrega: tipoEntregaEscolhido(),
    endereco: f.endereco.value.trim(),
    forma_pagamento: f.forma_pagamento.value,
    observacao: f.observacao.value.trim(),
    itens: itensDoCarrinho().map((item) => ({ produto_id: item.produto.id, quantidade: item.quantidade })),
  };

  const botao = el("btn-confirmar");
  botao.disabled = true;
  botao.textContent = "Enviando…";
  try {
    const criado = await Api.post("/api/pedidos", pedido);
    estado.carrinho = {};
    salvarCarrinho();
    renderizarCarrinho();
    form.reset();
    el("dialogo-checkout").close();
    el("codigo-pedido").textContent = criado.codigo;
    el("link-acompanhar").href = `/acompanhar.html?codigo=${encodeURIComponent(criado.codigo)}`;
    el("dialogo-sucesso").showModal();
  } catch (erro) {
    el("erro-checkout").textContent = erro.message;
  } finally {
    botao.disabled = false;
    botao.textContent = "Confirmar pedido";
  }
}

// ---------- Inicialização ----------

function configurarEventos() {
  el("btn-finalizar").addEventListener("click", () => {
    el("erro-checkout").textContent = "";
    atualizarTotaisCheckout();
    el("dialogo-checkout").showModal();
    form.elements.nome.focus();
  });
  el("btn-voltar").addEventListener("click", () => el("dialogo-checkout").close());
  el("btn-limpar").addEventListener("click", () => {
    estado.carrinho = {};
    salvarCarrinho();
    renderizarCarrinho();
    mostrarToast("Carrinho esvaziado.");
  });
  el("btn-ver-carrinho").addEventListener("click", () => el("carrinho").scrollIntoView({ behavior: "smooth" }));
  el("btn-novo-pedido").addEventListener("click", () => el("dialogo-sucesso").close());
  form.addEventListener("submit", enviarPedido);
  form.addEventListener("change", atualizarTotaisCheckout);
  form.elements.telefone.addEventListener("input", (e) => { e.target.value = formatarTelefone(e.target.value); });
}

async function iniciar() {
  configurarEventos();
  try {
    const [categorias, produtos, config] = await Promise.all([
      Api.get("/api/categorias"),
      Api.get("/api/produtos"),
      Api.get("/api/configuracoes"),
    ]);
    estado.categorias = categorias;
    estado.produtos = produtos;
    estado.taxaEntrega = config.taxa_entrega;
    estado.quantidadeMaxima = config.quantidade_maxima;
  } catch (erro) {
    el("grade-produtos").replaceChildren(criarElemento("p", "erro-form", erro.message));
    return;
  }

  // Remove do carrinho salvo produtos que saíram do cardápio.
  for (const id of Object.keys(estado.carrinho)) {
    if (!produtoPorId(id)) delete estado.carrinho[id];
  }
  salvarCarrinho();

  el("texto-taxa").textContent = `+ ${formatarPreco(estado.taxaEntrega)}`;
  el("dica-taxa").textContent = `Retirada grátis no balcão ou entrega por ${formatarPreco(estado.taxaEntrega)}.`;
  renderizarFiltros();
  renderizarProdutos();
  renderizarCarrinho();
}

iniciar();
