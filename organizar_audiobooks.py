"""
Script para organizar audiobooks em estrutura de pastas
"""

import os
import shutil
from pathlib import Path

# Pasta base dos audiobooks
BASE_DIR = Path(__file__).parent / "audiobooks"

# Estrutura de organização
ESTRUTURA = {
    "Animacao": [
        "Animated Storytelling - Liz Blazer"
    ],
    "Direcao": [],
    "Narrativa": [],
    "_Novos": []  # Audiobooks recém-convertidos
}

def criar_estrutura():
    """Cria estrutura de pastas organizada"""

    print("=" * 60)
    print("ORGANIZANDO AUDIOBOOKS")
    print("=" * 60)
    print()

    # Cria pastas de categoria
    for categoria in ESTRUTURA.keys():
        pasta_categoria = BASE_DIR / categoria
        pasta_categoria.mkdir(exist_ok=True)
        print(f"[OK] Pasta criada: {categoria}/")

    print()
    print("Estrutura criada:")
    print()
    print("audiobooks/")
    print("├── Animacao/")
    print("├── Direcao/")
    print("├── Narrativa/")
    print("└── _Novos/")
    print()

def mover_animated_storytelling():
    """Move arquivos do Animated Storytelling para pasta organizada"""

    print("=" * 60)
    print("MOVENDO: Animated Storytelling")
    print("=" * 60)
    print()

    # Pasta destino
    destino = BASE_DIR / "Animacao" / "Animated Storytelling - Liz Blazer"
    destino.mkdir(parents=True, exist_ok=True)

    # Busca arquivos do Animated Storytelling
    arquivos_movidos = 0

    for arquivo in BASE_DIR.glob("*.mp3"):
        # Pega apenas arquivos que começam com " - Cap" (do livro)
        if arquivo.name.startswith(" - Cap"):
            # Move para pasta destino
            destino_arquivo = destino / arquivo.name.replace(" - ", "")
            shutil.move(str(arquivo), str(destino_arquivo))
            print(f"[OK] Movido: {destino_arquivo.name}")
            arquivos_movidos += 1

    print()
    print(f"Total: {arquivos_movidos} arquivos organizados")
    print(f"Pasta: {destino}")
    print()

def listar_estrutura():
    """Lista estrutura final"""

    print("=" * 60)
    print("ESTRUTURA FINAL")
    print("=" * 60)
    print()

    for categoria in sorted(ESTRUTURA.keys()):
        pasta_cat = BASE_DIR / categoria

        if pasta_cat.exists():
            livros = [d for d in pasta_cat.iterdir() if d.is_dir()]

            print(f"📁 {categoria}/")
            if livros:
                for livro in livros:
                    num_arquivos = len(list(livro.glob("*.mp3")))
                    print(f"   └── {livro.name}/ ({num_arquivos} arquivos)")
            else:
                print(f"   └── (vazio)")
            print()

if __name__ == '__main__':
    criar_estrutura()
    mover_animated_storytelling()
    listar_estrutura()

    print("=" * 60)
    print("[OK] ORGANIZACAO CONCLUIDA!")
    print("=" * 60)
