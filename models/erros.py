"""Exceções de domínio lançadas pela camada Model."""


class ErroValidacao(Exception):
    """Dado de entrada inválido (o servidor responde HTTP 400)."""


class NaoEncontrado(Exception):
    """Registro inexistente (o servidor responde HTTP 404)."""
