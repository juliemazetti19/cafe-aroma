"""Model de Produto e Categoria: acesso aos dados e regras de validação."""
from models.database import conexao
from models.erros import ErroValidacao, NaoEncontrado

PRECO_MAXIMO_CENTAVOS = 100_000

_SELECT_BASE = """
    SELECT p.id, p.categoria_id, c.nome AS categoria, p.nome, p.descricao,
           p.preco_centavos, p.icone, p.ativo
      FROM produto p
      JOIN categoria c ON c.id = p.categoria_id
"""


def _para_dict(linha):
    return {
        "id": linha["id"],
        "categoria_id": linha["categoria_id"],
        "categoria": linha["categoria"],
        "nome": linha["nome"],
        "descricao": linha["descricao"],
        "preco": linha["preco_centavos"] / 100,
        "icone": linha["icone"],
        "ativo": bool(linha["ativo"]),
    }


def listar_categorias():
    with conexao() as con:
        return [dict(linha) for linha in con.execute("SELECT id, nome FROM categoria ORDER BY id")]


def listar(apenas_ativos=True):
    sql = _SELECT_BASE + (" WHERE p.ativo = 1" if apenas_ativos else "") + " ORDER BY p.categoria_id, p.nome"
    with conexao() as con:
        return [_para_dict(linha) for linha in con.execute(sql)]


def buscar(produto_id):
    with conexao() as con:
        linha = con.execute(_SELECT_BASE + " WHERE p.id = ?", (produto_id,)).fetchone()
    if linha is None:
        raise NaoEncontrado("Produto não encontrado.")
    return _para_dict(linha)


def _validar(con, dados):
    nome = str(dados.get("nome") or "").strip()
    if not 2 <= len(nome) <= 80:
        raise ErroValidacao("O nome do produto deve ter entre 2 e 80 caracteres.")

    descricao = str(dados.get("descricao") or "").strip()
    if len(descricao) > 200:
        raise ErroValidacao("A descrição deve ter no máximo 200 caracteres.")

    try:
        preco_centavos = round(float(dados.get("preco")) * 100)
    except (TypeError, ValueError):
        raise ErroValidacao("Informe um preço válido.") from None
    if not 0 < preco_centavos <= PRECO_MAXIMO_CENTAVOS:
        raise ErroValidacao("O preço deve ser maior que zero e no máximo R$ 1.000,00.")

    try:
        categoria_id = int(dados.get("categoria_id"))
    except (TypeError, ValueError):
        raise ErroValidacao("Selecione uma categoria.") from None
    if con.execute("SELECT 1 FROM categoria WHERE id = ?", (categoria_id,)).fetchone() is None:
        raise ErroValidacao("Categoria inexistente.")

    icone = str(dados.get("icone") or "☕").strip()[:4] or "☕"
    ativo = 1 if dados.get("ativo", True) else 0
    return (categoria_id, nome, descricao, preco_centavos, icone, ativo)


def criar(dados):
    with conexao() as con:
        valores = _validar(con, dados)
        cursor = con.execute(
            "INSERT INTO produto (categoria_id, nome, descricao, preco_centavos, icone, ativo) VALUES (?, ?, ?, ?, ?, ?)",
            valores,
        )
        novo_id = cursor.lastrowid
    return buscar(novo_id)


def atualizar(produto_id, dados):
    buscar(produto_id)
    with conexao() as con:
        valores = _validar(con, dados)
        con.execute(
            """UPDATE produto
                  SET categoria_id = ?, nome = ?, descricao = ?, preco_centavos = ?, icone = ?, ativo = ?
                WHERE id = ?""",
            (*valores, produto_id),
        )
    return buscar(produto_id)
