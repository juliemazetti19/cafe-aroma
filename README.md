# ☕ Café Aroma — Sistema de vendas online para cafeteria

Projeto Integrador Transdisciplinar em Sistemas de Informação II (PIT-II).

Aplicação web em que o cliente monta o pedido pelo cardápio, escolhe entre retirada no
balcão ou entrega e acompanha o preparo pelo código do pedido. Os funcionários usam um
painel para mudar o status dos pedidos e cuidar do cardápio.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Front-end (View) | HTML5, CSS3 e JavaScript puro (sem frameworks) |
| Back-end (Controller e Model) | Python 3.10+ com a biblioteca padrão (`http.server`, `sqlite3`) |
| Banco de dados | SQLite (arquivo `database/cafeteria.db`, criado sozinho). Script MySQL equivalente em `database/schema_mysql.sql` |
| Testes | `unittest` (compatível com `pytest`) |

Não é preciso instalar nenhuma biblioteca, só o Python.

## Como executar

1. Instale o Python 3.10 ou mais novo (https://www.python.org/downloads/).
2. Abra um terminal na pasta `cafeteria` e rode:
   ```
   python app.py
   ```
3. Acesse no navegador:
   - Loja: http://localhost:8000
   - Acompanhar pedido: http://localhost:8000/acompanhar.html
   - Painel da cafeteria: http://localhost:8000/admin.html (login `admin`, senha `cafe123`)

Para parar o servidor, pressione `Ctrl + C` no terminal. Para recomeçar com o banco limpo,
apague o arquivo `database/cafeteria.db`.

## Manual de uso

### Cliente
1. Na página **Cardápio**, filtre por categoria e clique em **Adicionar** nos itens desejados.
2. No quadro **Seu pedido**, ajuste as quantidades com **−** e **+** ou remova itens. O carrinho
   fica salvo no navegador, mesmo que a página seja fechada.
3. Clique em **Finalizar pedido** e preencha nome, telefone, forma de recebimento (retirada grátis
   ou entrega com taxa de R$ 6,00), forma de pagamento e observações.
4. Ao confirmar, aparece o **código do pedido** (6 letras e números). Guarde esse código.
5. Na página **Acompanhar pedido**, digite o código para ver a etapa do pedido: Recebido →
   Em preparo → Pronto → (Saiu para entrega) → Concluído. A página se atualiza sozinha.

### Funcionário (painel)
1. Acesse `/admin.html` e entre com login e senha.
2. No topo aparecem os pedidos do dia, o faturamento e os pedidos em aberto.
3. Na aba **Pedidos**, use os botões de cada linha para avançar o status (ex.: **→ Em preparo**).
   O sistema só mostra os próximos passos válidos. Para cancelar, clique em **Cancelar** duas vezes.
4. Na aba **Produtos**, cadastre novos itens, edite preço/descrição ou **Desative** um item que
   acabou (ele some do cardápio, mas continua nos pedidos antigos).

## Arquitetura (padrão MVC)

```
cafeteria/
├── app.py                  # Servidor HTTP + roteador: liga cada URL ao controller
├── models/                 # MODEL: dados e regras de negócio
│   ├── database.py         #   conexão, criação das tabelas e dados iniciais
│   ├── produto.py          #   cardápio e validação de produtos
│   ├── pedido.py           #   cálculo de valores, validação e fluxo de status
│   ├── administrador.py    #   autenticação do painel
│   ├── seguranca.py        #   hash de senha (PBKDF2)
│   └── erros.py            #   exceções de validação
├── controllers/            # CONTROLLER: recebe a requisição e chama o model
│   ├── loja_controller.py  #   rotas públicas (cardápio, pedidos)
│   └── admin_controller.py #   rotas protegidas por login
├── views/                  # VIEW: o que o usuário vê
│   ├── index.html, acompanhar.html, admin.html, 404.html
│   ├── css/style.css
│   └── js/ (api.js, loja.js, acompanhar.js, admin.js)
├── database/schema_mysql.sql   # projeto físico do banco em MySQL
└── tests/test_api.py           # testes automatizados
```

Fluxo de uma requisição: **Usuário → View (JS faz `fetch`) → Roteador (`app.py`) → Controller →
Model → banco**. A resposta JSON volta pelo mesmo caminho e a View atualiza a tela.

### Rotas da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/categorias` | Lista as categorias |
| GET | `/api/produtos` | Lista os produtos ativos |
| GET | `/api/configuracoes` | Taxa de entrega e limite de quantidade |
| POST | `/api/pedidos` | Cria um pedido |
| GET | `/api/pedidos/{codigo}` | Consulta pública do pedido (sem dados pessoais) |
| POST | `/api/admin/login` / `logout` | Entrar/sair do painel |
| GET | `/api/admin/resumo` | Indicadores do dia |
| GET | `/api/admin/pedidos?status=` | Lista pedidos |
| PATCH | `/api/admin/pedidos/{id}/status` | Avança o status |
| GET/POST | `/api/admin/produtos` | Lista todos / cadastra produto |
| PUT | `/api/admin/produtos/{id}` | Edita produto |

### Regras de negócio e segurança
- O **preço é sempre calculado no servidor** com os valores do banco. O valor enviado pelo navegador é ignorado.
- Valores em dinheiro são guardados em **centavos** (inteiros), sem erros de arredondamento.
- O status só avança pelos caminhos válidos (não é possível pular etapas nem reabrir pedido concluído).
- A consulta pública mostra só o primeiro nome do cliente, sem telefone nem endereço.
- Senhas guardadas com **hash PBKDF2 + salt**. As rotas do painel exigem token de sessão (expira em 8h).
- Consultas SQL parametrizadas (contra *SQL injection*). As telas usam `textContent` (contra *XSS*).

## Testes

```
python -m unittest -v
```

São 16 testes que sobem o servidor com um banco temporário e verificam cardápio, criação de
pedido (retirada e entrega), validações, cálculo do total, privacidade da consulta pública,
login, proteção das rotas, fluxo de status e cadastro de produtos.

## Publicação gratuita (para os colegas testarem)

O servidor lê as variáveis `HOST` e `PORT`, então pode ser publicado, por exemplo, no
**Render** (Web Service gratuito, comando de início `python app.py`, variável `HOST=0.0.0.0`) ou no
**PythonAnywhere**. **Antes de publicar, defina a variável `ADMIN_SENHA`** com uma senha forte.
Ela é usada na primeira execução, quando o banco é criado.
