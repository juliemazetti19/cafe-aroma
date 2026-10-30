"""Model de Administrador (funcionário da cafeteria que gerencia pedidos)."""
from models.database import conexao
from models.seguranca import conferir_senha


def autenticar(login, senha):
    with conexao() as con:
        linha = con.execute("SELECT senha_hash, salt FROM administrador WHERE login = ?", (login,)).fetchone()
    return linha is not None and conferir_senha(senha, linha["senha_hash"], linha["salt"])
