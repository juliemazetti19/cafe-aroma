"""Objetos compartilhados pelos controllers."""


class ErroHttp(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


class Requisicao:
    """Dados da requisição HTTP já interpretados pelo roteador."""

    def __init__(self, corpo, query, cabecalhos, parametros):
        self.corpo = corpo
        self.query = query
        self.cabecalhos = cabecalhos
        self.parametros = parametros

    def token(self):
        autorizacao = (self.cabecalhos.get("Authorization") if self.cabecalhos else None) or ""
        return autorizacao[7:].strip() if autorizacao.startswith("Bearer ") else None

    def parametro_query(self, nome, padrao=None):
        valores = self.query.get(nome)
        return valores[0] if valores else padrao
