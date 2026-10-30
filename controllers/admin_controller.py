"""Controller do painel administrativo (rotas protegidas por login)."""
import secrets
import time

from controllers.base import ErroHttp
from models import administrador, pedido, produto

DURACAO_SESSAO_SEGUNDOS = 8 * 60 * 60
_sessoes = {}  # token -> (login, expira_em)


def _exigir_admin(req):
    token = req.token()
    sessao = _sessoes.get(token) if token else None
    if sessao is None or sessao[1] < time.time():
        _sessoes.pop(token, None)
        raise ErroHttp(401, "Sessão expirada. Faça login novamente.")
    return sessao[0]


def login(req):
    usuario = str(req.corpo.get("login") or "").strip()
    senha = str(req.corpo.get("senha") or "")
    if not administrador.autenticar(usuario, senha):
        raise ErroHttp(401, "Login ou senha incorretos.")
    token = secrets.token_urlsafe(32)
    _sessoes[token] = (usuario, time.time() + DURACAO_SESSAO_SEGUNDOS)
    return 200, {"token": token, "login": usuario}


def logout(req):
    _sessoes.pop(req.token(), None)
    return 200, {"ok": True}


def resumo(req):
    _exigir_admin(req)
    return 200, pedido.resumo_do_dia()


def listar_pedidos(req):
    _exigir_admin(req)
    return 200, pedido.listar(req.parametro_query("status") or None)


def atualizar_status(req):
    _exigir_admin(req)
    return 200, pedido.atualizar_status(int(req.parametros["pedido_id"]), req.corpo.get("status"))


def listar_produtos(req):
    _exigir_admin(req)
    return 200, produto.listar(apenas_ativos=False)


def criar_produto(req):
    _exigir_admin(req)
    return 201, produto.criar(req.corpo)


def editar_produto(req):
    _exigir_admin(req)
    return 200, produto.atualizar(int(req.parametros["produto_id"]), req.corpo)
