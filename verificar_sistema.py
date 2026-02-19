"""
Script para verificar se o sistema está configurado corretamente
"""

import sys
from pathlib import Path

print("=" * 60)
print("VERIFICACAO DO SISTEMA PDF2AUDIOBOOK")
print("=" * 60)
print()

erros = []
avisos = []
sucessos = []

# ==================== PYTHON ====================

print("[1/8] Verificando versao do Python...")
version = sys.version_info
if version.major >= 3 and version.minor >= 9:
    print(f"  [OK] Python {version.major}.{version.minor}.{version.micro}")
    sucessos.append("Python")
else:
    print(f"  [ERRO] Python {version.major}.{version.minor}.{version.micro}")
    print(f"         Requer Python 3.9+")
    erros.append("Python muito antigo")

print()

# ==================== DEPENDÊNCIAS PRINCIPAIS ====================

dependencias = [
    ("edge-tts", "edge_tts"),
    ("PyMuPDF", "fitz"),
    ("tqdm", "tqdm"),
    ("colorama", "colorama"),
    ("google-auth", "google.auth"),
    ("google-api-python-client", "googleapiclient"),
]

print("[2/8] Verificando dependencias principais...")
for nome_exibicao, nome_import in dependencias:
    try:
        __import__(nome_import)
        print(f"  [OK] {nome_exibicao}")
        sucessos.append(nome_exibicao)
    except ImportError:
        print(f"  [ERRO] {nome_exibicao} nao instalado")
        erros.append(f"{nome_exibicao} faltando")

print()

# ==================== DEPENDÊNCIAS OPCIONAIS ====================

print("[3/8] Verificando dependencias opcionais...")

# OCRmyPDF
try:
    import ocrmypdf
    print("  [OK] ocrmypdf (para PDFs escaneados)")
    sucessos.append("OCRmyPDF")
except ImportError:
    print("  [AVISO] ocrmypdf nao instalado")
    print("          PDFs escaneados nao funcionarao")
    avisos.append("OCRmyPDF faltando")

# pyttsx3 (fallback TTS)
try:
    import pyttsx3
    print("  [OK] pyttsx3 (fallback TTS)")
    sucessos.append("pyttsx3")
except ImportError:
    print("  [AVISO] pyttsx3 nao instalado")
    print("          Sem fallback se Edge-TTS falhar")
    avisos.append("pyttsx3 faltando")

print()

# ==================== CONEXÃO INTERNET ====================

print("[4/8] Verificando conexao com internet...")
try:
    import urllib.request
    urllib.request.urlopen('https://www.google.com', timeout=5)
    print("  [OK] Conexao OK")
    sucessos.append("Internet")
except Exception as e:
    print(f"  [ERRO] Sem conexao: {e}")
    erros.append("Sem internet")

print()

# ==================== EDGE-TTS ====================

print("[5/8] Verificando Edge-TTS (Azure)...")
try:
    from tts_engine import listar_vozes_disponiveis
    vozes = listar_vozes_disponiveis("pt")
    if vozes:
        print(f"  [OK] Edge-TTS funcionando ({len(vozes)} vozes PT)")
        sucessos.append("Edge-TTS")
    else:
        print("  [ERRO] Edge-TTS sem vozes PT")
        erros.append("Edge-TTS sem vozes")
except Exception as e:
    print(f"  [ERRO] Edge-TTS falhou: {e}")
    erros.append("Edge-TTS erro")

print()

# ==================== GOOGLE DRIVE ====================

print("[6/8] Verificando configuracao Google Drive...")
cred_file = Path("credentials.json")
token_file = Path("token.json")

if cred_file.exists():
    print("  [OK] credentials.json encontrado")
    sucessos.append("Google Credentials")
else:
    print("  [AVISO] credentials.json nao encontrado")
    print("          Upload para Google Drive nao funcionara")
    print("          Use --no-upload ou configure Google Drive")
    avisos.append("Google Drive nao configurado")

if token_file.exists():
    print("  [OK] token.json encontrado (ja autenticado)")

print()

# ==================== TESSERACT OCR ====================

print("[7/8] Verificando Tesseract OCR...")
try:
    import subprocess
    resultado = subprocess.run(
        ['tesseract', '--version'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if resultado.returncode == 0:
        versao = resultado.stdout.split('\n')[0]
        print(f"  [OK] {versao}")
        sucessos.append("Tesseract")
    else:
        raise Exception("Tesseract nao responde")
except Exception as e:
    print("  [AVISO] Tesseract nao instalado")
    print("          PDFs escaneados nao funcionarao")
    print("          Instale: https://github.com/UB-Mannheim/tesseract/wiki")
    avisos.append("Tesseract nao instalado")

print()

# ==================== ESTRUTURA DE PASTAS ====================

print("[8/8] Verificando estrutura de pastas...")
pastas = ["audiobooks", "temp", ".checkpoints"]
for pasta in pastas:
    p = Path(pasta)
    if p.exists():
        print(f"  [OK] {pasta}/")
    else:
        print(f"  [INFO] {pasta}/ sera criada automaticamente")

print()

# ==================== RESUMO ====================

print("=" * 60)
print("RESUMO DA VERIFICACAO")
print("=" * 60)
print()

print(f"[OK] Sucessos: {len(sucessos)}")
for s in sucessos[:5]:
    print(f"  - {s}")
if len(sucessos) > 5:
    print(f"  ... e mais {len(sucessos) - 5}")

print()

if avisos:
    print(f"[AVISO] Avisos: {len(avisos)}")
    for a in avisos:
        print(f"  - {a}")
    print()

if erros:
    print(f"[ERRO] Erros criticos: {len(erros)}")
    for e in erros:
        print(f"  - {e}")
    print()
    print("SISTEMA NAO ESTA PRONTO!")
    print("Resolva os erros acima antes de usar.")
else:
    print("[OK] SISTEMA PRONTO PARA USO!")
    print()
    print("Proximos passos:")
    print("  1. python exemplo_teste.py  # Criar PDF teste")
    print("  2. python pipeline_mvp.py --pdf exemplo_teste.pdf --no-upload")
    print()
    print("Ou use seu proprio PDF:")
    print("  python pipeline_mvp.py --pdf seu_livro.pdf")

print()
print("=" * 60)
