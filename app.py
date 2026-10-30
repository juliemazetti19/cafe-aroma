"""Café Aroma — loja online da cafeteria.

Ponto de entrada da aplicação. Sobe o servidor HTTP, encaminha as chamadas da
API (/api/...) para os controllers e entrega os arquivos da camada View
(HTML, CSS e JavaScript da pasta views/).

Para executar:  python app.py   e abrir http://localhost:8000
"""
import json
import os
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from controllers import admin_controller, loja_controller
from controllers.base import ErroHttp, Requisicao
from models import database
from models.erros import ErroValidacao, NaoEncontrado

PASTA_VIEWS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "views"))
TAMANHO_MAXIMO_CORPO = 100 * 1024
TIPOS_ARQUIVO = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

# Roteador: (método HTTP, padrão da URL, ação do controller)
ROTAS = [
    ("GET", r"/api/categorias", loja_controller.listar_categorias),
    ("GET", r"/api/produtos", loja_controller.listar_produtos),
    ("GET", r"/api/configuracoes", loja_controller.configuracoes),
    ("POST", r"/api/pedidos", loja_controller.criar_pedido),
    ("GET", r"/api/pedidos/(?P<codigo>[A-Za-z0-9]{1,12})", loja_controller.consultar_pedido),
    ("POST", r"/api/admin/login", admin_controller.login),
    ("POST", r"/api/admin/logout", admin_controller.logout),
    ("GET", r"/api/admin/resumo", admin_controller.resumo),
    ("GET", r"/api/admin/pedidos", admin_controller.listar_pedidos),
    ("PATCH", r"/api/admin/pedidos/(?P<pedido_id>\d+)/status", admin_controller.atualizar_status),
    ("GET", r"/api/admin/produtos", admin_controller.listar_produtos),
    ("POST", r"/api/admin/produtos", admin_controller.criar_produto),
    ("PUT", r"/api/admin/produtos/(?P<produto_id>\d+)", admin_controller.editar_produto),
]
ROTAS = [(metodo, re.compile(padrao + "$"), acao) for metodo, padrao, acao in ROTAS]


class Manipulador(BaseHTTPRequestHandler):
    server_version = "CafeAroma/1.0"

    def do_GET(self):
        self._tratar("GET")

    def do_POST(self):
        self._tratar("POST")

    def do_PUT(self):
        self._tratar("PUT")

    def do_PATCH(self):
        self._tratar("PATCH")

    def _tratar(self, metodo):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            self._tratar_api(metodo, url)
        elif metodo == "GET":
            self._servir_arquivo(url.path)
        else:
            self._responder_json(405, {"erro": "Método não permitido."})

    def _tratar_api(self, metodo, url):
        caminho_existe = False
        for metodo_rota, padrao, acao in ROTAS:
            encontrado = padrao.match(url.path)
            if encontrado:
                caminho_existe = True
                if metodo_rota == metodo:
                    break
        else:
            if caminho_existe:
                return self._responder_json(405, {"erro": "Método não permitido."})
            return self._responder_json(404, {"erro": "Rota não encontrada."})

        try:
            requisicao = Requisicao(self._ler_corpo(), parse_qs(url.query), self.headers, encontrado.groupdict())
            status, dados = acao(requisicao)
        except ErroValidacao as erro:
            status, dados = 400, {"erro": str(erro)}
        except NaoEncontrado as erro:
            status, dados = 404, {"erro": str(erro)}
        except ErroHttp as erro:
            status, dados = erro.status, {"erro": erro.mensagem}
        except Exception:
            traceback.print_exc()
            status, dados = 500, {"erro": "Erro interno no servidor. Tente novamente."}
        self._responder_json(status, dados)

    def _ler_corpo(self):
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ErroHttp(400, "Cabeçalho Content-Length inválido.") from None
        if tamanho > TAMANHO_MAXIMO_CORPO:
            raise ErroHttp(413, "Requisição muito grande.")
        if tamanho == 0:
            return {}
        try:
            corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ErroValidacao("JSON inválido.") from None
        if not isinstance(corpo, dict):
            raise ErroValidacao("JSON inválido.")
        return corpo

    def _servir_arquivo(self, caminho):
        if caminho == "/":
            caminho = "/index.html"
        completo = os.path.realpath(os.path.join(PASTA_VIEWS, caminho.lstrip("/")))
        if not completo.startswith(PASTA_VIEWS + os.sep) or not os.path.isfile(completo):
            completo = os.path.join(PASTA_VIEWS, "404.html")
            status = 404
        else:
            status = 200
        with open(completo, "rb") as arquivo:
            conteudo = arquivo.read()
        self.send_response(status)
        self.send_header("Content-Type", TIPOS_ARQUIVO.get(os.path.splitext(completo)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)

    def _responder_json(self, status, dados):
        conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(conteudo)


def criar_servidor(host="127.0.0.1", porta=8000):
    database.inicializar()
    return ThreadingHTTPServer((host, porta), Manipulador)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    porta = int(os.environ.get("PORT", "8000"))
    servidor = criar_servidor(host, porta)
    print(f"Cafe Aroma rodando em http://localhost:{porta}  (Ctrl+C para parar)")
    print(f"Painel administrativo: http://localhost:{porta}/admin.html")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        servidor.server_close()
