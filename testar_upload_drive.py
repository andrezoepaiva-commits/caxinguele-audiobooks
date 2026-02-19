"""
Script para testar autenticação e upload no Google Drive
"""

import sys
from pathlib import Path

print("=" * 60)
print("TESTE DE UPLOAD - GOOGLE DRIVE")
print("=" * 60)
print()

# Importa módulos
try:
    from cloud_uploader import obter_servico_drive
    from cloud_uploader import obter_ou_criar_pasta, upload_arquivo
    print("[OK] Modulos importados")
except Exception as e:
    print(f"[ERRO] Falha ao importar: {e}")
    sys.exit(1)

print()
print("Passo 1: Autenticando com Google Drive...")
print("(Uma janela do navegador vai abrir para voce autorizar)")
print()

try:
    service = obter_servico_drive()
    print("[OK] Autenticacao bem-sucedida!")
except Exception as e:
    print(f"[ERRO] Falha na autenticacao: {e}")
    sys.exit(1)

print()
print("Passo 2: Criando estrutura de pastas...")
print()

try:
    # Pasta raiz: Audiobooks - Projeto Caxinguele
    pasta_raiz = obter_ou_criar_pasta(service, "Audiobooks - Projeto Caxinguele")
    print(f"[OK] Pasta raiz criada/encontrada")

    # Pasta de categoria: Animacao
    pasta_animacao = obter_ou_criar_pasta(service, "Animacao", pasta_raiz)
    print(f"[OK] Pasta Animacao criada/encontrada")

    # Pasta do livro
    pasta_livro = obter_ou_criar_pasta(
        service,
        "Animated Storytelling - Liz Blazer",
        pasta_animacao
    )
    print(f"[OK] Pasta do livro criada/encontrada")

except Exception as e:
    print(f"[ERRO] Falha ao criar pastas: {e}")
    sys.exit(1)

print()
print("Passo 3: Upload de arquivo de teste...")
print()

# Busca primeiro arquivo MP3 do livro
base = Path("audiobooks/Animacao/Animated Storytelling - Liz Blazer")
arquivos = list(base.glob("*.mp3"))

if not arquivos:
    print("[ERRO] Nenhum arquivo MP3 encontrado")
    sys.exit(1)

# Pega primeiro arquivo (teste)
arquivo_teste = arquivos[0]
print(f"Arquivo de teste: {arquivo_teste.name}")
print(f"Tamanho: {arquivo_teste.stat().st_size / (1024*1024):.1f} MB")
print()

try:
    resultado = upload_arquivo(
        service,
        arquivo_teste,
        pasta_livro,
        tornar_publico=True
    )

    if resultado:
        print("[OK] Upload bem-sucedido!")
        print()
        print("Link direto (para MyPod):")
        print(resultado['direct_url'])
        print()
        print("=" * 60)
        print("[SUCESSO] Sistema Google Drive funcionando!")
        print("=" * 60)
    else:
        print("[ERRO] Upload falhou")

except Exception as e:
    print(f"[ERRO] Falha no upload: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
