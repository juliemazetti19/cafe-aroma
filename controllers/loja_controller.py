"""Controller da loja (rotas públicas usadas pelo cliente)."""
from models import pedido, produto


def listar_categorias(req):
    return 200, produto.listar_categorias()


def listar_produtos(req):
    return 200, produto.listar(apenas_ativos=True)


def configuracoes(req):
    return 200, {"taxa_entrega": pedido.TAXA_ENTREGA_CENTAVOS / 100, "quantidade_maxima": pedido.QUANTIDADE_MAXIMA}


def criar_pedido(req):
    return 201, pedido.criar(req.corpo)


def consultar_pedido(req):
    return 200, pedido.buscar_por_codigo(req.parametros["codigo"], publico=True)
