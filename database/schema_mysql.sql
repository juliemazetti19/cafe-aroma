-- =====================================================================
-- Café Aroma — Projeto físico do banco de dados (MySQL 8)
-- Mesmo modelo usado pela aplicação (que roda em SQLite por padrão).
-- Executar:  mysql -u root -p < schema_mysql.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS cafe_aroma
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
USE cafe_aroma;

-- Categoria do cardápio (Cafés, Bebidas geladas, Salgados, Doces)
CREATE TABLE categoria (
    id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome    VARCHAR(40) NOT NULL,
    CONSTRAINT uq_categoria_nome UNIQUE (nome)
) ENGINE = InnoDB;

-- Produto vendido na loja. "ativo = 0" esconde o item do cardápio sem apagá-lo,
-- preservando o histórico dos pedidos antigos.
CREATE TABLE produto (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    categoria_id    INT UNSIGNED  NOT NULL,
    nome            VARCHAR(80)   NOT NULL,
    descricao       VARCHAR(200)  NOT NULL DEFAULT '',
    preco           DECIMAL(10,2) NOT NULL,
    icone           VARCHAR(8)    NOT NULL DEFAULT '☕',
    ativo           BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_produto_categoria FOREIGN KEY (categoria_id) REFERENCES categoria (id),
    CONSTRAINT ck_produto_preco CHECK (preco > 0 AND preco <= 1000)
) ENGINE = InnoDB;

-- Cliente que fez o pedido (compra sem cadastro: nome e telefone bastam)
CREATE TABLE cliente (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(80)  NOT NULL,
    telefone    VARCHAR(11)  NOT NULL,   -- só dígitos, com DDD
    email       VARCHAR(120) NULL
) ENGINE = InnoDB;

CREATE TABLE pedido (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo              CHAR(6)       NOT NULL,   -- código que o cliente usa para acompanhar
    cliente_id          INT UNSIGNED  NOT NULL,
    criado_em           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tipo_entrega        ENUM('RETIRADA', 'ENTREGA') NOT NULL,
    endereco            VARCHAR(200)  NULL,
    forma_pagamento     ENUM('PIX', 'CARTAO', 'DINHEIRO') NOT NULL,
    subtotal            DECIMAL(10,2) NOT NULL,
    taxa_entrega        DECIMAL(10,2) NOT NULL DEFAULT 0,
    total               DECIMAL(10,2) NOT NULL,
    status              ENUM('RECEBIDO', 'EM_PREPARO', 'PRONTO', 'SAIU_PARA_ENTREGA', 'CONCLUIDO', 'CANCELADO')
                        NOT NULL DEFAULT 'RECEBIDO',
    observacao          VARCHAR(200)  NULL,
    CONSTRAINT uq_pedido_codigo UNIQUE (codigo),
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (cliente_id) REFERENCES cliente (id),
    CONSTRAINT ck_pedido_endereco CHECK (tipo_entrega = 'RETIRADA' OR endereco IS NOT NULL),
    INDEX idx_pedido_status (status),
    INDEX idx_pedido_criado_em (criado_em)
) ENGINE = InnoDB;

-- Itens do pedido. O preço é copiado no momento da compra, para que uma
-- mudança futura no cardápio não altere pedidos já feitos.
CREATE TABLE item_pedido (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    pedido_id       INT UNSIGNED  NOT NULL,
    produto_id      INT UNSIGNED  NOT NULL,
    quantidade      TINYINT UNSIGNED NOT NULL,
    preco_unitario  DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_item_pedido FOREIGN KEY (pedido_id) REFERENCES pedido (id) ON DELETE CASCADE,
    CONSTRAINT fk_item_produto FOREIGN KEY (produto_id) REFERENCES produto (id),
    CONSTRAINT ck_item_quantidade CHECK (quantidade BETWEEN 1 AND 20)
) ENGINE = InnoDB;

-- Funcionário que acessa o painel. A senha nunca é guardada em texto puro.
CREATE TABLE administrador (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    login       VARCHAR(40)  NOT NULL,
    senha_hash  CHAR(64)     NOT NULL,   -- PBKDF2-SHA256
    salt        CHAR(32)     NOT NULL,
    CONSTRAINT uq_administrador_login UNIQUE (login)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- Dados iniciais
-- ---------------------------------------------------------------------
INSERT INTO categoria (nome) VALUES ('Cafés'), ('Bebidas geladas'), ('Salgados'), ('Doces');

INSERT INTO produto (categoria_id, nome, descricao, preco, icone) VALUES
    (1, 'Espresso', 'Café espresso curto, grãos 100% arábica.', 6.00, '☕'),
    (1, 'Cappuccino', 'Espresso, leite vaporizado e espuma cremosa com canela.', 12.00, '☕'),
    (1, 'Latte', 'Espresso com bastante leite vaporizado.', 11.50, '🥛'),
    (1, 'Mocha', 'Espresso, chocolate meio amargo e leite vaporizado.', 13.50, '🍫'),
    (2, 'Café gelado', 'Cold brew servido com gelo e um toque de baunilha.', 14.00, '🧊'),
    (2, 'Frappé de caramelo', 'Café batido com gelo, leite e calda de caramelo.', 17.00, '🥤'),
    (2, 'Suco de laranja', 'Suco natural de laranja, 400 ml.', 10.00, '🍊'),
    (3, 'Pão de queijo', 'Porção com 6 unidades, quentinho.', 9.00, '🧀'),
    (3, 'Croissant de presunto e queijo', 'Massa folhada amanteigada.', 13.00, '🥐'),
    (3, 'Misto quente', 'Pão de forma, presunto e queijo na chapa.', 11.00, '🥪'),
    (4, 'Bolo de cenoura', 'Fatia com cobertura de chocolate.', 9.50, '🍰'),
    (4, 'Cookie de chocolate', 'Cookie artesanal com gotas de chocolate.', 7.00, '🍪'),
    (4, 'Brownie', 'Brownie de chocolate com nozes.', 8.50, '🟫');

-- O usuário administrador é criado pela aplicação (models/database.py),
-- que gera o hash e o salt da senha.

-- ---------------------------------------------------------------------
-- Consultas úteis
-- ---------------------------------------------------------------------
-- Faturamento por dia (sem pedidos cancelados):
--   SELECT DATE(criado_em) AS dia, COUNT(*) AS pedidos, SUM(total) AS faturamento
--     FROM pedido WHERE status <> 'CANCELADO' GROUP BY DATE(criado_em) ORDER BY dia DESC;
-- Produtos mais vendidos:
--   SELECT p.nome, SUM(i.quantidade) AS unidades
--     FROM item_pedido i JOIN produto p ON p.id = i.produto_id
--     JOIN pedido pe ON pe.id = i.pedido_id AND pe.status <> 'CANCELADO'
--    GROUP BY p.id ORDER BY unidades DESC LIMIT 5;
