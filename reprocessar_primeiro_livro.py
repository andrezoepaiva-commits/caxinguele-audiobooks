"""
Reprocessa o primeiro livro (Animated Storytelling - Liz Blazer):
- Faz upload dos capitulos faltantes no Google Drive
- Regenera o RSS completo corrigido
- Publica no GitHub Pages
"""

import sys
import logging
from pathlib import Path

# Configura logging simples
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

# Pasta dos MP3s do primeiro livro
PASTA_LIVRO = Path(__file__).parent / "audiobooks" / "Animacao" / "Animated Storytelling - Liz Blazer"
NOME_LIVRO = "Animated Storytelling - Liz Blazer"
DESCRICAO = "Audiobook do livro Animated Storytelling de Liz Blazer - Projeto Caxinguele"


def main():
    print("=" * 60)
    print("Reprocessando: Animated Storytelling - Liz Blazer")
    print("=" * 60)

    # Verifica se a pasta existe
    if not PASTA_LIVRO.exists():
        print(f"[ERRO] Pasta nao encontrada: {PASTA_LIVRO}")
        sys.exit(1)

    # Lista MP3s ordenados
    arquivos_mp3 = sorted([
        f for f in PASTA_LIVRO.iterdir()
        if f.suffix.lower() == ".mp3" and f.stat().st_size > 0
    ])

    print(f"\nEncontrados {len(arquivos_mp3)} capitulos:")
    for f in arquivos_mp3:
        print(f"  {f.name}")

    # --- PASSO 1: Upload no Google Drive ---
    print(f"\n[1/3] Verificando/Enviando para Google Drive...")

    from cloud_uploader import upload_audiobook
    resultados = upload_audiobook(arquivos_mp3, NOME_LIVRO)

    if not resultados:
        print("[ERRO] Falha no upload para Google Drive")
        sys.exit(1)

    print(f"[OK] {len(resultados)}/{len(arquivos_mp3)} capitulos no Drive")

    # --- PASSO 2: Gerar RSS corrigido ---
    print(f"\n[2/3] Gerando RSS corrigido...")

    from rss_generator import gerar_rss_livro
    pasta_saida = Path(__file__).parent / "temp"
    pasta_saida.mkdir(exist_ok=True)

    arquivo_rss = gerar_rss_livro(resultados, NOME_LIVRO, pasta_saida, DESCRICAO)
    print(f"[OK] RSS gerado: {arquivo_rss.name}")

    # Mostra preview do XML (primeiras linhas)
    with open(arquivo_rss, "r", encoding="utf-8") as f:
        linhas = f.readlines()[:10]
    print("\nPreview do RSS:")
    print("".join(linhas))

    # --- PASSO 3: Publicar no GitHub ---
    print(f"\n[3/3] Publicando no GitHub Pages...")

    from github_uploader import publicar_rss
    from pathlib import Path as P
    capa = P(__file__).parent / "capa_podcast.jpg"

    ok = publicar_rss(arquivo_rss, capa if capa.exists() else None)

    if ok:
        print("\n" + "=" * 60)
        print("[OK] Primeiro livro reprocessado com sucesso!")
        print(f"\nURL do RSS no GitHub:")
        print(f"https://andrezoepaiva-commits.github.io/caxinguele-audiobooks/{arquivo_rss.name}")
        print("\nO Spotify deve atualizar automaticamente em alguns minutos.")
        print("=" * 60)
    else:
        print("[AVISO] RSS gerado mas publicacao no GitHub falhou.")
        print(f"Arquivo local: {arquivo_rss}")


if __name__ == "__main__":
    main()
