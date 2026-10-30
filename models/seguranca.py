"""Funções de hash de senha (PBKDF2-SHA256 com salt aleatório)."""
import hashlib
import hmac
import secrets

ITERACOES = 100_000


def gerar_hash(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    hash_hex = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), ITERACOES).hex()
    return hash_hex, salt


def conferir_senha(senha, hash_salvo, salt):
    hash_calculado, _ = gerar_hash(senha, salt)
    return hmac.compare_digest(hash_calculado, hash_salvo)
