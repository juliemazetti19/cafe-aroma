"""Conexão com o banco de dados SQLite, criação das tabelas e dados iniciais.

Os valores em dinheiro são guardados em centavos (INTEGER) para evitar erros
de arredondamento de ponto flutuante. O script equivalente para MySQL está em
database/schema_mysql.sql.
"""
import os
import sqlite3
from contextlib import contextmanager

from models.seguranca import gerar_hash

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_caminho = os.environ.get("CAFE_DB", os.path.join(PASTA_PROJETO, "database", "cafeteria.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS categoria (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nome    TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS produto (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id    INTEGER NOT NULL REFERENCES categoria(id),
    nome            TEXT    NOT NULL,
    descricao       TEXT    NOT NULL DEFAULT '',
    preco_centavos  INTEGER NOT NULL CHECK (preco_centavos > 0),
    icone           TEXT    NOT NULL DEFAULT '☕',
    ativo           INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS cliente (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    telefone    TEXT    NOT NULL,
    email       TEXT
);

CREATE TABLE IF NOT EXISTS pedido (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                  TEXT    NOT NULL UNIQUE,
    cliente_id              INTEGER NOT NULL REFERENCES cliente(id),
    criado_em               TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    tipo_entrega            TEXT    NOT NULL CHECK (tipo_entrega IN ('RETIRADA', 'ENTREGA')),
    endereco                TEXT,
    forma_pagamento         TEXT    NOT NULL CHECK (forma_pagamento IN ('PIX', 'CARTAO', 'DINHEIRO')),
    subtotal_centavos       INTEGER NOT NULL,
    taxa_entrega_centavos   INTEGER NOT NULL DEFAULT 0,
    total_centavos          INTEGER NOT NULL,
    status                  TEXT    NOT NULL DEFAULT 'RECEBIDO'
        CHECK (status IN ('RECEBIDO', 'EM_PREPARO', 'PRONTO', 'SAIU_PARA_ENTREGA', 'CONCLUIDO', 'CANCELADO')),
    observacao              TEXT
);

CREATE TABLE IF NOT EXISTS item_pedido (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id               INTEGER NOT NULL REFERENCES pedido(id) ON DELETE CASCADE,
    produto_id              INTEGER NOT NULL REFERENCES produto(id),
    quantidade              INTEGER NOT NULL CHECK (quantidade BETWEEN 1 AND 20),
    preco_unitario_centavos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS administrador (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    login       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,
    salt        TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pedido_status ON pedido(status);
CREATE INDEX IF NOT EXISTS idx_item_pedido_pedido ON item_pedido(pedido_id);
"""

CATEGORIAS = ["Cafés", "Bebidas geladas", "Salgados", "Doces"]

# (categoria, nome, descrição, preço em centavos, ícone)
PRODUTOS = [
    (1, "Espresso", "Café espresso curto, grãos 100% arábica.", 600, "☕"),
    (1, "Cappuccino", "Espresso, leite vaporizado e espuma cremosa com canela.", 1200, "☕"),
    (1, "Latte", "Espresso com bastante leite vaporizado.", 1150, "🥛"),
    (1, "Mocha", "Espresso, chocolate meio amargo e leite vaporizado.", 1350, "🍫"),
    (2, "Café gelado", "Cold brew servido com gelo e um toque de baunilha.", 1400, "🧊"),
    (2, "Frappé de caramelo", "Café batido com gelo, leite e calda de caramelo.", 1700, "🥤"),
    (2, "Suco de laranja", "Suco natural de laranja, 400 ml.", 1000, "🍊"),
    (3, "Pão de queijo", "Porção com 6 unidades, quentinho.", 900, "🧀"),
    (3, "Croissant de presunto e queijo", "Massa folhada amanteigada.", 1300, "🥐"),
    (3, "Misto quente", "Pão de forma, presunto e queijo na chapa.", 1100, "🥪"),
    (4, "Bolo de cenoura", "Fatia com cobertura de chocolate.", 950, "🍰"),
    (4, "Cookie de chocolate", "Cookie artesanal com gotas de chocolate.", 700, "🍪"),
    (4, "Brownie", "Brownie de chocolate com nozes.", 850, "🟫"),
]

# Senha do painel criada na primeira execução. Em produção, defina a variável ADMIN_SENHA.
ADMIN_LOGIN_PADRAO = "admin"
ADMIN_SENHA_PADRAO = os.environ.get("ADMIN_SENHA", "cafe123")


def configurar(caminho):
    """Troca o arquivo do banco (usado pelos testes automatizados)."""
    global _caminho
    _caminho = caminho


@contextmanager
def conexao():
    con = sqlite3.connect(_caminho)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def inicializar():
    os.makedirs(os.path.dirname(os.path.abspath(_caminho)), exist_ok=True)
    with conexao() as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM categoria").fetchone()[0] == 0:
            _popular(con)


def _popular(con):
    con.executemany("INSERT INTO categoria (nome) VALUES (?)", [(nome,) for nome in CATEGORIAS])
    con.executemany(
        "INSERT INTO produto (categoria_id, nome, descricao, preco_centavos, icone) VALUES (?, ?, ?, ?, ?)",
        PRODUTOS,
    )
    senha_hash, salt = gerar_hash(ADMIN_SENHA_PADRAO)
    con.execute(
        "INSERT INTO administrador (login, senha_hash, salt) VALUES (?, ?, ?)",
        (ADMIN_LOGIN_PADRAO, senha_hash, salt),
    )
