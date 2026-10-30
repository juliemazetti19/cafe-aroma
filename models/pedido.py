"""Model de Pedido: validação, cálculo de valores e fluxo de status.

Os preços são sempre lidos do banco no momento da compra; o valor enviado pelo
navegador é ignorado, para que o cliente não consiga alterar o total.
"""
import re
import secrets

from models.database import conexao
from models.erros import ErroValidacao, NaoEncontrado

TAXA_ENTREGA_CENTAVOS = 600
QUANTIDADE_MAXIMA = 20
TIPOS_ENTREGA = ("RETIRADA", "ENTREGA")
FORMAS_PAGAMENTO = ("PIX", "CARTAO", "DINHEIRO")
STATUS = ("RECEBIDO", "EM_PREPARO", "PRONTO", "SAIU_PARA_ENTREGA", "CONCLUIDO", "CANCELADO")

# Para cada status, quais são os próximos permitidos.
FLUXO_STATUS = {
    "RECEBIDO": ("EM_PREPARO", "CANCELADO"),
    "EM_PREPARO": ("PRONTO", "CANCELADO"),
    "PRONTO": ("SAIU_PARA_ENTREGA", "CONCLUIDO", "CANCELADO"),
    "SAIU_PARA_ENTREGA": ("CONCLUIDO",),
    "CONCLUIDO": (),
    "CANCELADO": (),
}

_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _proximos_status(status, tipo_entrega):
    proximos = FLUXO_STATUS[status]
    if tipo_entrega == "RETIRADA":
        proximos = tuple(s for s in proximos if s != "SAIU_PARA_ENTREGA")
    return list(proximos)


def _validar(dados):
    cliente = dados.get("cliente")
    if not isinstance(cliente, dict):
        raise ErroValidacao("Informe os dados do cliente.")

    nome = str(cliente.get("nome") or "").strip()
    if not 3 <= len(nome) <= 80:
        raise ErroValidacao("Informe seu nome (de 3 a 80 caracteres).")

    telefone = re.sub(r"\D", "", str(cliente.get("telefone") or ""))
    if len(telefone) not in (10, 11):
        raise ErroValidacao("Informe um telefone válido com DDD.")

    email = str(cliente.get("email") or "").strip() or None
    if email and (len(email) > 120 or not _REGEX_EMAIL.match(email)):
        raise ErroValidacao("E-mail inválido.")

    tipo_entrega = dados.get("tipo_entrega")
    if tipo_entrega not in TIPOS_ENTREGA:
        raise ErroValidacao("Escolha retirada no balcão ou entrega.")

    endereco = str(dados.get("endereco") or "").strip()
    if tipo_entrega == "ENTREGA":
        if not 10 <= len(endereco) <= 200:
            raise ErroValidacao("Informe o endereço completo para entrega.")
    else:
        endereco = None

    forma_pagamento = dados.get("forma_pagamento")
    if forma_pagamento not in FORMAS_PAGAMENTO:
        raise ErroValidacao("Escolha uma forma de pagamento.")

    observacao = str(dados.get("observacao") or "").strip()
    if len(observacao) > 200:
        raise ErroValidacao("A observação deve ter no máximo 200 caracteres.")

    itens_recebidos = dados.get("itens")
    if not isinstance(itens_recebidos, list) or not itens_recebidos:
        raise ErroValidacao("O carrinho está vazio.")

    itens = {}
    for item in itens_recebidos:
        try:
            produto_id = int(item["produto_id"])
            quantidade = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            raise ErroValidacao("Item do carrinho inválido.") from None
        itens[produto_id] = itens.get(produto_id, 0) + quantidade
    for quantidade in itens.values():
        if not 1 <= quantidade <= QUANTIDADE_MAXIMA:
            raise ErroValidacao(f"A quantidade de cada item deve ser de 1 a {QUANTIDADE_MAXIMA}.")

    return {
        "nome": nome,
        "telefone": telefone,
        "email": email,
        "tipo_entrega": tipo_entrega,
        "endereco": endereco,
        "forma_pagamento": forma_pagamento,
        "observacao": observacao or None,
        "itens": itens,
    }


def _gerar_codigo(con):
    while True:
        codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(6))
        if con.execute("SELECT 1 FROM pedido WHERE codigo = ?", (codigo,)).fetchone() is None:
            return codigo


def criar(dados):
    pedido = _validar(dados)
    with conexao() as con:
        ids = list(pedido["itens"])
        marcadores = ",".join("?" * len(ids))
        produtos = {
            linha["id"]: linha
            for linha in con.execute(
                f"SELECT id, nome, preco_centavos FROM produto WHERE ativo = 1 AND id IN ({marcadores})", ids
            )
        }
        indisponiveis = [i for i in ids if i not in produtos]
        if indisponiveis:
            raise ErroValidacao("Um ou mais produtos do carrinho não estão mais disponíveis. Atualize a página.")

        subtotal = sum(produtos[i]["preco_centavos"] * qtd for i, qtd in pedido["itens"].items())
        taxa = TAXA_ENTREGA_CENTAVOS if pedido["tipo_entrega"] == "ENTREGA" else 0

        cliente_id = con.execute(
            "INSERT INTO cliente (nome, telefone, email) VALUES (?, ?, ?)",
            (pedido["nome"], pedido["telefone"], pedido["email"]),
        ).lastrowid
        codigo = _gerar_codigo(con)
        pedido_id = con.execute(
            """INSERT INTO pedido (codigo, cliente_id, tipo_entrega, endereco, forma_pagamento,
                                   subtotal_centavos, taxa_entrega_centavos, total_centavos, observacao)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (codigo, cliente_id, pedido["tipo_entrega"], pedido["endereco"], pedido["forma_pagamento"],
             subtotal, taxa, subtotal + taxa, pedido["observacao"]),
        ).lastrowid
        con.executemany(
            "INSERT INTO item_pedido (pedido_id, produto_id, quantidade, preco_unitario_centavos) VALUES (?, ?, ?, ?)",
            [(pedido_id, i, qtd, produtos[i]["preco_centavos"]) for i, qtd in pedido["itens"].items()],
        )
    return buscar_por_codigo(codigo)


_SELECT_PEDIDO = """
    SELECT pe.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone, c.email AS cliente_email
      FROM pedido pe
      JOIN cliente c ON c.id = pe.cliente_id
"""


def _montar(con, linha, publico=False):
    itens = [
        {
            "produto_id": item["produto_id"],
            "nome": item["nome"],
            "icone": item["icone"],
            "quantidade": item["quantidade"],
            "preco_unitario": item["preco_unitario_centavos"] / 100,
            "subtotal": item["quantidade"] * item["preco_unitario_centavos"] / 100,
        }
        for item in con.execute(
            """SELECT i.produto_id, p.nome, p.icone, i.quantidade, i.preco_unitario_centavos
                 FROM item_pedido i JOIN produto p ON p.id = i.produto_id
                WHERE i.pedido_id = ? ORDER BY i.id""",
            (linha["id"],),
        )
    ]
    pedido = {
        "codigo": linha["codigo"],
        "criado_em": linha["criado_em"],
        "status": linha["status"],
        "tipo_entrega": linha["tipo_entrega"],
        "forma_pagamento": linha["forma_pagamento"],
        "subtotal": linha["subtotal_centavos"] / 100,
        "taxa_entrega": linha["taxa_entrega_centavos"] / 100,
        "total": linha["total_centavos"] / 100,
        "observacao": linha["observacao"],
        "itens": itens,
    }
    if publico:
        # Na consulta pública, só o primeiro nome: quem tem o código não vê telefone nem endereço.
        pedido["cliente"] = {"nome": linha["cliente_nome"].split()[0]}
    else:
        pedido["id"] = linha["id"]
        pedido["endereco"] = linha["endereco"]
        pedido["cliente"] = {
            "nome": linha["cliente_nome"],
            "telefone": linha["cliente_telefone"],
            "email": linha["cliente_email"],
        }
        pedido["proximos_status"] = _proximos_status(linha["status"], linha["tipo_entrega"])
    return pedido


def buscar_por_codigo(codigo, publico=False):
    with conexao() as con:
        linha = con.execute(_SELECT_PEDIDO + " WHERE pe.codigo = ?", (str(codigo).upper(),)).fetchone()
        if linha is None:
            raise NaoEncontrado("Pedido não encontrado. Confira o código.")
        return _montar(con, linha, publico)


def listar(status=None):
    if status is not None and status not in STATUS:
        raise ErroValidacao("Status inválido.")
    sql = _SELECT_PEDIDO + (" WHERE pe.status = ?" if status else "") + " ORDER BY pe.id DESC LIMIT 200"
    with conexao() as con:
        return [_montar(con, linha) for linha in con.execute(sql, (status,) if status else ())]


def atualizar_status(pedido_id, novo_status):
    with conexao() as con:
        linha = con.execute("SELECT status, tipo_entrega FROM pedido WHERE id = ?", (pedido_id,)).fetchone()
        if linha is None:
            raise NaoEncontrado("Pedido não encontrado.")
        if novo_status not in _proximos_status(linha["status"], linha["tipo_entrega"]):
            raise ErroValidacao(f"Não é possível mudar o pedido de {linha['status']} para {novo_status}.")
        con.execute("UPDATE pedido SET status = ? WHERE id = ?", (novo_status, pedido_id))
        atualizado = con.execute(_SELECT_PEDIDO + " WHERE pe.id = ?", (pedido_id,)).fetchone()
        return _montar(con, atualizado)


def resumo_do_dia():
    with conexao() as con:
        linha = con.execute(
            """SELECT COUNT(*) AS pedidos,
                      COALESCE(SUM(CASE WHEN status <> 'CANCELADO' THEN total_centavos END), 0) AS faturamento,
                      COALESCE(SUM(CASE WHEN status IN ('RECEBIDO', 'EM_PREPARO', 'PRONTO', 'SAIU_PARA_ENTREGA')
                                        THEN 1 END), 0) AS em_aberto
                 FROM pedido
                WHERE date(criado_em) = date('now', 'localtime')"""
        ).fetchone()
    return {
        "pedidos_hoje": linha["pedidos"],
        "faturamento_hoje": linha["faturamento"] / 100,
        "em_aberto": linha["em_aberto"],
    }
