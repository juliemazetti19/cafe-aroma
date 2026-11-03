# Café Aroma

Sistema de pedidos online para uma cafeteria, feito para o Projeto Integrador Transdisciplinar em Sistemas de Informação II (PIT-II).

O cliente escolhe os produtos no cardápio, decide se vai retirar no balcão ou receber em casa e acompanha o pedido pelo código que recebe ao finalizar. A equipe da cafeteria usa um painel para mudar o status dos pedidos e cuidar do cardápio.

Versão publicada: https://cafe-aroma-zz6g.onrender.com (no plano gratuito do Render, o primeiro acesso pode levar até 1 minuto).

## Tecnologias

| Parte | O que usei |
|---|---|
| Front-end (View) | HTML, CSS e JavaScript, sem framework |
| Back-end (Controller e Model) | Python 3.10 ou mais novo, só com a biblioteca padrão (`http.server` e `sqlite3`) |
| Banco de dados | SQLite, no arquivo `database/cafeteria.db`, que é criado na primeira execução. O mesmo modelo em MySQL está em `database/schema_mysql.sql` |
| Testes | `unittest` |

Não precisa instalar nenhuma biblioteca, só o Python.

## Como rodar no computador

1. Instale o Python 3.10 ou mais novo (https://www.python.org/downloads/).
2. Abra um terminal na pasta do projeto e rode:
   ```
   python app.py
   ```
3. Abra no navegador:
   - Loja: http://localhost:8000
   - Acompanhar pedido: http://localhost:8000/acompanhar.html
   - Painel da cafeteria: http://localhost:8000/admin.html (login `admin` e senha `cafe123`)

Para parar, aperte `Ctrl + C` no terminal. Se quiser começar com o banco zerado, apague o arquivo `database/cafeteria.db` antes de rodar de novo.

## Manual de uso

### Cliente

1. No cardápio, escolha uma categoria se quiser e clique em Adicionar nos produtos.
2. No quadro "Seu pedido" dá para aumentar ou diminuir a quantidade e remover itens. O carrinho fica salvo no navegador, então ele continua lá se a página for fechada.
3. Clique em Finalizar pedido e preencha nome, telefone, se vai retirar (grátis) ou receber em casa (taxa de R$ 6,00), a forma de pagamento e, se quiser, uma observação.
4. Depois de confirmar, aparece o código do pedido, com 6 letras e números. Guarde esse código.
5. Em Acompanhar pedido, digite o código. A página mostra em que etapa o pedido está (Recebido, Em preparo, Pronto, Saiu para entrega e Concluído) e se atualiza sozinha. Quando o status muda, aparece um aviso na tela.

### Funcionário

1. Entre em `/admin.html` com login e senha.
2. No topo ficam os números do dia: pedidos, faturamento e pedidos em aberto.
3. Na aba Pedidos, cada pedido tem botões só com os próximos passos possíveis, por exemplo "Em preparo". Para cancelar, é preciso clicar em Cancelar duas vezes, para evitar engano.
4. Na aba Produtos dá para cadastrar um produto, mudar preço e descrição ou desativar um item que acabou. O produto desativado sai do cardápio, mas continua aparecendo nos pedidos antigos.

## Organização do código (MVC)

```
cafeteria/
├── app.py                  servidor e roteador, liga cada endereço ao controller
├── models/                 MODEL, dados e regras de negócio
│   ├── database.py         conexão, criação das tabelas e dados iniciais
│   ├── produto.py          cardápio e validação de produtos
│   ├── pedido.py           cálculo dos valores, validação e status
│   ├── administrador.py    login do painel
│   ├── seguranca.py        hash de senha (PBKDF2)
│   └── erros.py            erros de validação
├── controllers/            CONTROLLER, recebe a requisição e chama o model
│   ├── loja_controller.py  rotas da loja (cardápio e pedidos)
│   └── admin_controller.py rotas do painel, que exigem login
├── views/                  VIEW, as telas
│   ├── index.html, acompanhar.html, admin.html, 404.html
│   ├── css/style.css
│   └── js/ (api.js, loja.js, acompanhar.js, admin.js)
├── database/schema_mysql.sql   projeto físico do banco em MySQL
└── tests/test_api.py           testes automatizados
```

Quando o usuário faz alguma coisa na tela, o JavaScript chama a API com `fetch`. O `app.py` encontra o controller certo, o controller chama o model e o model lê ou grava no banco. A resposta volta em JSON e o JavaScript atualiza a tela.

### Rotas da API

| Método | Rota | Para que serve |
|---|---|---|
| GET | `/api/categorias` | Lista as categorias |
| GET | `/api/produtos` | Lista os produtos ativos |
| GET | `/api/configuracoes` | Taxa de entrega e limite de quantidade |
| POST | `/api/pedidos` | Cria um pedido |
| GET | `/api/pedidos/{codigo}` | Consulta o pedido pelo código, sem dados pessoais |
| POST | `/api/admin/login` e `/api/admin/logout` | Entra e sai do painel |
| GET | `/api/admin/resumo` | Números do dia |
| GET | `/api/admin/pedidos?status=` | Lista os pedidos |
| PATCH | `/api/admin/pedidos/{id}/status` | Muda o status |
| GET e POST | `/api/admin/produtos` | Lista e cadastra produtos |
| PUT | `/api/admin/produtos/{id}` | Edita um produto |

### Regras importantes

- O preço é sempre calculado no servidor com o valor do banco. Se o navegador mandar outro preço, ele é ignorado.
- Os valores são guardados em centavos, como número inteiro, para não ter erro de arredondamento.
- O status só anda pelos caminhos válidos. Não dá para pular etapa nem mexer num pedido já concluído.
- A consulta pelo código mostra só o primeiro nome do cliente, sem telefone e sem endereço.
- A senha do painel é guardada com hash PBKDF2 e salt. As rotas do painel pedem um token de sessão, que vale por 8 horas.
- As consultas SQL usam parâmetros, para evitar SQL injection, e as telas mostram os textos com `textContent`, para evitar XSS.

## Testes

```
python -m unittest -v
```

São 16 testes. Eles sobem o servidor com um banco temporário e conferem o cardápio, os pedidos com retirada e com entrega, as validações, o cálculo do total, a privacidade da consulta, o login, a proteção das rotas do painel, a mudança de status e o cadastro de produtos.

## Publicação

O servidor lê as variáveis `HOST` e `PORT`, então dá para publicar em serviços gratuitos. Eu usei o Render (Web Service gratuito, comando de início `python app.py` e variável `HOST=0.0.0.0`). Antes de publicar, defina a variável `ADMIN_SENHA` com uma senha forte, porque ela é usada quando o banco é criado na primeira execução.
