// Página de acompanhamento: o cliente digita o código e vê o status do pedido.

const INTERVALO_ATUALIZACAO_MS = 15000;
const ETAPAS = {
  RETIRADA: ["RECEBIDO", "EM_PREPARO", "PRONTO", "CONCLUIDO"],
  ENTREGA: ["RECEBIDO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA", "CONCLUIDO"],
};

const el = (id) => document.getElementById(id);
let temporizador;
let ultimoStatus = null; // status da última consulta, para avisar o cliente quando ele mudar

function renderizarPedido(pedido) {
  el("res-codigo").textContent = pedido.codigo;
  el("res-info").textContent =
    `${pedido.cliente.nome} · ${formatarDataHora(pedido.criado_em)} · ` +
    `${NOMES_ENTREGA[pedido.tipo_entrega]} · Pagamento: ${NOMES_PAGAMENTO[pedido.forma_pagamento]}`;

  const cancelado = pedido.status === "CANCELADO";
  el("res-cancelado").hidden = !cancelado;

  const linha = el("res-linha-tempo");
  linha.replaceChildren();
  const etapas = ETAPAS[pedido.tipo_entrega];
  const posicaoAtual = etapas.indexOf(pedido.status);
  linha.hidden = cancelado;
  etapas.forEach((etapa, indice) => {
    const li = criarElemento("li", null, NOMES_STATUS[etapa]);
    if (indice < posicaoAtual || pedido.status === "CONCLUIDO") li.className = "feito";
    else if (indice === posicaoAtual) {
      li.className = "atual";
      li.setAttribute("aria-current", "step");
    }
    linha.append(li);
  });

  const itens = el("res-itens");
  itens.replaceChildren();
  for (const item of pedido.itens) {
    const li = document.createElement("li");
    li.append(
      criarElemento("span", null, `${item.quantidade}× ${item.icone} ${item.nome}`),
      criarElemento("span", null, formatarPreco(item.subtotal))
    );
    itens.append(li);
  }
  el("res-subtotal").textContent = formatarPreco(pedido.subtotal);
  el("res-taxa").textContent = pedido.taxa_entrega ? formatarPreco(pedido.taxa_entrega) : "Grátis";
  el("res-total").textContent = formatarPreco(pedido.total);

  const finalizado = pedido.status === "CONCLUIDO" || cancelado;
  el("res-atualizado").textContent = finalizado
    ? ""
    : `Atualizado às ${new Date().toLocaleTimeString("pt-BR")}. A página se atualiza sozinha a cada 15 segundos.`;
  el("resultado").hidden = false;
  return finalizado;
}

async function consultar(codigo, silencioso = false) {
  clearTimeout(temporizador);
  if (!silencioso) el("erro-busca").textContent = "";
  try {
    const pedido = await Api.get(`/api/pedidos/${encodeURIComponent(codigo)}`);
    // Melhoria vinda dos testes com usuários: a atualização automática passava despercebida,
    // então a mudança de status agora gera um aviso na tela.
    if (silencioso && ultimoStatus && pedido.status !== ultimoStatus) {
      mostrarToast(`Seu pedido agora está: ${NOMES_STATUS[pedido.status]}.`, "sucesso");
    }
    ultimoStatus = pedido.status;
    const finalizado = renderizarPedido(pedido);
    history.replaceState(null, "", `?codigo=${encodeURIComponent(pedido.codigo)}`);
    if (!finalizado) temporizador = setTimeout(() => consultar(codigo, true), INTERVALO_ATUALIZACAO_MS);
  } catch (erro) {
    if (silencioso) {
      temporizador = setTimeout(() => consultar(codigo, true), INTERVALO_ATUALIZACAO_MS);
      return;
    }
    el("resultado").hidden = true;
    el("erro-busca").textContent = erro.message;
  }
}

const form = el("form-busca");
form.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const codigo = form.elements.codigo.value.trim().toUpperCase();
  if (!/^[A-Z0-9]{4,12}$/.test(codigo)) {
    el("erro-busca").textContent = "Digite o código de 6 letras/números que apareceu ao finalizar o pedido.";
    return;
  }
  consultar(codigo);
});

const codigoNaUrl = new URLSearchParams(location.search).get("codigo");
if (codigoNaUrl) {
  form.elements.codigo.value = codigoNaUrl.toUpperCase();
  consultar(codigoNaUrl.toUpperCase());
}
