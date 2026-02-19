"""
Script de configuração rápida do GitHub Token
Execute uma vez antes de usar o sistema com upload
"""
import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ENV_FILE = Path(__file__).parent / ".env"

print()
print("=" * 55)
print("  CONFIGURAÇÃO DO GITHUB TOKEN — Projeto Caxinguele")
print("=" * 55)
print()
print("O GitHub Token permite publicar o RSS automaticamente.")
print()
print("Para obter o token:")
print("  1. Acesse: https://github.com/settings/tokens")
print("  2. Clique em 'Generate new token (classic)'")
print("  3. Nome: Caxinguele-Audiobooks")
print("  4. Marque APENAS: repo")
print("  5. Clique 'Generate token'")
print("  6. COPIE o token (começa com ghp_)")
print()

token = input("Cole seu token aqui e aperte Enter: ").strip()

if not token:
    print("\n❌ Token vazio. Tente novamente.")
    sys.exit(1)

if not token.startswith("ghp_") and not token.startswith("github_pat_"):
    print("\n⚠️  Token não parece válido (deve começar com ghp_ ou github_pat_)")
    confirmar = input("Salvar mesmo assim? (s/N): ").strip().lower()
    if confirmar != "s":
        sys.exit(1)

# Salva no .env
with open(ENV_FILE, "w", encoding="utf-8") as f:
    f.write(f"GITHUB_TOKEN={token}\n")

print()
print("✅ Token salvo em .env")
print()
print("Teste rápido...")

# Testa o token
try:
    from github import Github, GithubException
    g = Github(token)
    user = g.get_user()
    print(f"✅ Token válido! Usuário: {user.login}")
except Exception as e:
    print(f"⚠️  Não foi possível validar agora: {e}")
    print("   (Token foi salvo mesmo assim — pode ser problema de rede)")

print()
print("=" * 55)
print("  Pronto! Agora o sistema vai publicar no GitHub.")
print("  Execute: python audiobook_gui.py")
print("=" * 55)
print()
