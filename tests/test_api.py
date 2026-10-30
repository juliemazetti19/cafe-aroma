"""Testes automatizados da API (unitários e de integração).

Sobem o servidor real numa porta livre, com um banco SQLite temporário, e
fazem requisições HTTP como o navegador faria.

Executar na pasta do projeto:  python -m unittest -v
(também funciona com pytest, se estiver instalado:  python -m pytest -v)
"""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import app
from models import database


class TesteApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta_temporaria = tempfile.TemporaryDirectory()
        database.configurar(os.path.join(cls.pasta_temporaria.name, "teste.db"))
        cls.servidor = app.criar_servidor("127.0.0.1", 0)
        cls.url = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.pasta_temporaria.cleanup()

    def requisitar(self, metodo, caminho, corpo=None, token=None):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(self.url + caminho, data=dados, method=metodo)
        if dados is not None:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req) as resposta:
                return resposta.status, json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            return erro.code, json.loads(erro.read().decode("utf-8"))

    def pedido_valido(self, **alteracoes):
        pedido = {
            "cliente": {"nome": "Maria Silva", "telefone": "(61) 99999-1234", "email": "maria@exemplo.com"},
            "tipo_entrega": "RETIRADA",
            "endereco": "",
            "forma_pagamento": "PIX",
            "observacao": "Sem açúcar",
            "itens": [{"produto_id": 1, "quantidade": 2}, {"produto_id": 8, "quantidade": 1}],
        }
        pedido.update(alteracoes)
        return pedido

    def login_admin(self):
        status, resposta = self.requisitar("POST", "/api/admin/login", {"login": "admin", "senha": "cafe123"})
        self.assertEqual(status, 200)
        return resposta["token"]

    # ---------- Cardápio ----------

    def test_lista_categorias_e_produtos(self):
        status, categorias = self.requisitar("GET", "/api/categorias")
        self.assertEqual(status, 200)
        self.assertEqual(len(categorias), 4)
        status, produtos = self.requisitar("GET", "/api/produtos")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(produtos), 10)
        self.assertTrue(all(p["ativo"] for p in produtos))

    def test_pagina_inicial_e_404(self):
        with urllib.request.urlopen(self.url + "/") as resposta:
            self.assertEqual(resposta.status, 200)
            self.assertIn("Café Aroma", resposta.read().decode("utf-8"))
        with self.assertRaises(urllib.error.HTTPError) as contexto:
            urllib.request.urlopen(self.url + "/../app.py")
        self.assertEqual(contexto.exception.code, 404)

    # ---------- Pedidos ----------

    def test_cria_pedido_para_retirada_sem_taxa(self):
        status, pedido = self.requisitar("POST", "/api/pedidos", self.pedido_valido())
        self.assertEqual(status, 201)
        # Espresso R$ 6,00 x 2 + Pão de queijo R$ 9,00 = R$ 21,00
        self.assertEqual(pedido["subtotal"], 21.0)
        self.assertEqual(pedido["taxa_entrega"], 0)
        self.assertEqual(pedido["total"], 21.0)
        self.assertEqual(pedido["status"], "RECEBIDO")
        self.assertEqual(len(pedido["codigo"]), 6)

    def test_pedido_para_entrega_soma_taxa(self):
        status, pedido = self.requisitar(
            "POST", "/api/pedidos", self.pedido_valido(tipo_entrega="ENTREGA", endereco="Rua das Flores, 123 - Centro")
        )
        self.assertEqual(status, 201)
        self.assertEqual(pedido["taxa_entrega"], 6.0)
        self.assertEqual(pedido["total"], 27.0)

    def test_entrega_sem_endereco_e_recusada(self):
        status, resposta = self.requisitar("POST", "/api/pedidos", self.pedido_valido(tipo_entrega="ENTREGA"))
        self.assertEqual(status, 400)
        self.assertIn("endereço", resposta["erro"])

    def test_preco_enviado_pelo_navegador_e_ignorado(self):
        itens = [{"produto_id": 1, "quantidade": 1, "preco": 0.01}]
        status, pedido = self.requisitar("POST", "/api/pedidos", self.pedido_valido(itens=itens))
        self.assertEqual(status, 201)
        self.assertEqual(pedido["total"], 6.0)

    def test_validacoes_do_pedido(self):
        casos = {
            "carrinho vazio": self.pedido_valido(itens=[]),
            "telefone curto": self.pedido_valido(cliente={"nome": "Maria", "telefone": "1234"}),
            "nome vazio": self.pedido_valido(cliente={"nome": " ", "telefone": "61999991234"}),
            "e-mail inválido": self.pedido_valido(cliente={"nome": "Maria", "telefone": "61999991234", "email": "x@"}),
            "quantidade zero": self.pedido_valido(itens=[{"produto_id": 1, "quantidade": 0}]),
            "quantidade acima do limite": self.pedido_valido(itens=[{"produto_id": 1, "quantidade": 21}]),
            "produto inexistente": self.pedido_valido(itens=[{"produto_id": 9999, "quantidade": 1}]),
            "pagamento inválido": self.pedido_valido(forma_pagamento="BITCOIN"),
        }
        for descricao, pedido in casos.items():
            with self.subTest(descricao):
                status, resposta = self.requisitar("POST", "/api/pedidos", pedido)
                self.assertEqual(status, 400)
                self.assertIn("erro", resposta)

    def test_consulta_publica_nao_expoe_dados_pessoais(self):
        _, criado = self.requisitar(
            "POST", "/api/pedidos", self.pedido_valido(tipo_entrega="ENTREGA", endereco="Rua das Flores, 123 - Centro")
        )
        status, pedido = self.requisitar("GET", f"/api/pedidos/{criado['codigo'].lower()}")
        self.assertEqual(status, 200)
        self.assertEqual(pedido["cliente"], {"nome": "Maria"})
        self.assertNotIn("endereco", pedido)
        self.assertNotIn("telefone", json.dumps(pedido))

    def test_consulta_de_codigo_inexistente(self):
        status, _ = self.requisitar("GET", "/api/pedidos/ZZZZZZ")
        self.assertEqual(status, 404)

    # ---------- Painel administrativo ----------

    def test_rotas_admin_exigem_login(self):
        for metodo, caminho in [("GET", "/api/admin/pedidos"), ("GET", "/api/admin/resumo"),
                                ("POST", "/api/admin/produtos"), ("PATCH", "/api/admin/pedidos/1/status")]:
            with self.subTest(caminho):
                status, _ = self.requisitar(metodo, caminho, {} if metodo != "GET" else None, token="token-falso")
                self.assertEqual(status, 401)

    def test_login_com_senha_errada(self):
        status, resposta = self.requisitar("POST", "/api/admin/login", {"login": "admin", "senha": "errada"})
        self.assertEqual(status, 401)
        self.assertNotIn("token", resposta)

    def test_fluxo_de_status_do_pedido(self):
        token = self.login_admin()
        _, criado = self.requisitar("POST", "/api/pedidos", self.pedido_valido())
        _, pedidos = self.requisitar("GET", "/api/admin/pedidos?status=RECEBIDO", token=token)
        pedido = next(p for p in pedidos if p["codigo"] == criado["codigo"])
        self.assertEqual(pedido["cliente"]["telefone"], "61999991234")
        self.assertEqual(pedido["proximos_status"], ["EM_PREPARO", "CANCELADO"])

        caminho = f"/api/admin/pedidos/{pedido['id']}/status"
        # Não pode pular etapas nem usar "Saiu para entrega" em pedido de retirada.
        self.assertEqual(self.requisitar("PATCH", caminho, {"status": "CONCLUIDO"}, token)[0], 400)
        for proximo in ("EM_PREPARO", "PRONTO"):
            status, atualizado = self.requisitar("PATCH", caminho, {"status": proximo}, token)
            self.assertEqual(status, 200)
        self.assertEqual(atualizado["proximos_status"], ["CONCLUIDO", "CANCELADO"])
        self.assertEqual(self.requisitar("PATCH", caminho, {"status": "SAIU_PARA_ENTREGA"}, token)[0], 400)
        status, atualizado = self.requisitar("PATCH", caminho, {"status": "CONCLUIDO"}, token)
        self.assertEqual(atualizado["status"], "CONCLUIDO")
        self.assertEqual(self.requisitar("PATCH", caminho, {"status": "CANCELADO"}, token)[0], 400)

    def test_cadastro_e_desativacao_de_produto(self):
        token = self.login_admin()
        novo = {"nome": "Chá verde", "descricao": "Chá verde orgânico", "preco": 7.5, "categoria_id": 2, "icone": "🍵"}
        status, produto = self.requisitar("POST", "/api/admin/produtos", novo, token)
        self.assertEqual(status, 201)
        self.assertEqual(produto["preco"], 7.5)

        status, _ = self.requisitar("PUT", f"/api/admin/produtos/{produto['id']}", {**novo, "ativo": False}, token)
        self.assertEqual(status, 200)
        _, cardapio = self.requisitar("GET", "/api/produtos")
        self.assertNotIn(produto["id"], [p["id"] for p in cardapio])

        itens = [{"produto_id": produto["id"], "quantidade": 1}]
        status, _ = self.requisitar("POST", "/api/pedidos", self.pedido_valido(itens=itens))
        self.assertEqual(status, 400)

    def test_validacao_de_produto(self):
        token = self.login_admin()
        invalidos = [
            {"nome": "X", "preco": 5, "categoria_id": 1},
            {"nome": "Café", "preco": 0, "categoria_id": 1},
            {"nome": "Café", "preco": "abc", "categoria_id": 1},
            {"nome": "Café", "preco": 5, "categoria_id": 999},
        ]
        for dados in invalidos:
            with self.subTest(dados):
                status, _ = self.requisitar("POST", "/api/admin/produtos", dados, token)
                self.assertEqual(status, 400)

    def test_resumo_do_dia(self):
        token = self.login_admin()
        self.requisitar("POST", "/api/pedidos", self.pedido_valido())
        status, resumo = self.requisitar("GET", "/api/admin/resumo", token=token)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(resumo["pedidos_hoje"], 1)
        self.assertGreater(resumo["faturamento_hoje"], 0)

    def test_json_invalido(self):
        req = urllib.request.Request(self.url + "/api/pedidos", data=b"{nao e json", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as contexto:
            urllib.request.urlopen(req)
        self.assertEqual(contexto.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
