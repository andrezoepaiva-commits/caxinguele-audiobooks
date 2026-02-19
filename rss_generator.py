"""
Gerador de RSS para audiobooks no GitHub Pages
Cria um arquivo XML por livro, compativel com qualquer app de podcast
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# URL base do GitHub Pages
GITHUB_USER = "andrezoepaiva-commits"
GITHUB_REPO = "caxinguele-audiobooks"
BASE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}"
PODCAST_EMAIL = "andrezoepaiva@gmail.com"
ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
CAPA_URL = f"{BASE_URL}/capa_podcast.jpg"


ET.register_namespace("itunes", ITUNES)
ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")


def gerar_rss_livro(
    resultados_upload: List[Dict],
    nome_livro: str,
    pasta_saida: Path,
    descricao: str = ""
) -> Path:
    """
    Gera arquivo RSS para um livro.

    Args:
        resultados_upload: Lista com dicts {nome, direct_url} dos capitulos
        nome_livro: Nome do livro (vira titulo do podcast)
        pasta_saida: Pasta onde salvar o arquivo .xml
        descricao: Descricao opcional do livro

    Returns:
        Caminho do arquivo RSS gerado
    """

    # Nome do arquivo: remove caracteres especiais
    nome_arquivo = nome_livro.lower()
    nome_arquivo = nome_arquivo.replace(" ", "-")
    for char in ".,!?:;/\\()[]{}\"'":
        nome_arquivo = nome_arquivo.replace(char, "")
    nome_arquivo = nome_arquivo + ".xml"

    arquivo_rss = pasta_saida / nome_arquivo

    # Monta o XML
    rss = ET.Element("rss", {"version": "2.0"})

    channel = ET.SubElement(rss, "channel")

    # Informacoes do podcast (livro)
    ET.SubElement(channel, "title").text = nome_livro
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = descricao or f"Audiobook: {nome_livro} - Projeto Caxinguele"
    ET.SubElement(channel, "language").text = "pt-BR"
    ET.SubElement(channel, f"{{{ITUNES}}}author").text = "Projeto Caxinguele"
    owner = ET.SubElement(channel, f"{{{ITUNES}}}owner")
    ET.SubElement(owner, f"{{{ITUNES}}}name").text = "Projeto Caxinguele"
    ET.SubElement(owner, f"{{{ITUNES}}}email").text = PODCAST_EMAIL
    ET.SubElement(channel, f"{{{ITUNES}}}explicit").text = "false"
    ET.SubElement(channel, f"{{{ITUNES}}}image", {"href": CAPA_URL})
    img_block = ET.SubElement(channel, "image")
    ET.SubElement(img_block, "url").text = CAPA_URL
    ET.SubElement(img_block, "title").text = nome_livro
    ET.SubElement(img_block, "link").text = BASE_URL
    ET.SubElement(channel, f"{{{ITUNES}}}category", {"text": "Books"})

    # Episodios (capitulos)
    for i, resultado in enumerate(resultados_upload, 1):
        nome_cap = resultado.get("nome", f"Capitulo {i:02d}")
        # Remove extensao .mp3 do titulo
        titulo_cap = nome_cap.replace(".mp3", "").strip()
        # Remove o "- Cap XX -" do inicio para ficar mais limpo
        if " - " in titulo_cap:
            partes = titulo_cap.split(" - ", 2)
            if len(partes) >= 3:
                titulo_cap = partes[2].strip()

        url_audio = resultado.get("direct_url", resultado.get("url", ""))

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"{i:02d}. {titulo_cap}"
        ET.SubElement(item, "description").text = f"Capitulo {i} de {nome_livro}"
        ET.SubElement(item, "guid").text = f"{nome_livro}-cap{i:02d}"
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        ET.SubElement(item, f"{{{ITUNES}}}episode").text = str(i)
        ET.SubElement(item, f"{{{ITUNES}}}episodeType").text = "full"
        ET.SubElement(item, "enclosure", {
            "url": url_audio,
            "type": "audio/mpeg",
            "length": "0"
        })

    # Salva o arquivo com formatacao legivel
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")

    with open(arquivo_rss, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

    return arquivo_rss


if __name__ == "__main__":
    # Gera o RSS do Animated Storytelling com os links reais
    resultados = [
        {"nome": "- Cap 01 - 1. Pre-producao - Parte 1.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1nAza8X0wna2PBjDm7CJN28NwfnOyAOIi"},
        {"nome": "- Cap 02 - 1. Pre-producao - Parte 2.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=14DHlQiRUMTUsGZr7fg2Yi7vHzL_matvY"},
        {"nome": "- Cap 05 - 6. Comece a construir.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1j8uM5lQyGKrRseSVIuAo0GCZodpeyotH"},
        {"nome": "- Cap 06 - 2. Contacao de historias - Parte 1.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1X_IBKE05t8SHR5T1XI6tyUH6JXlRc62j"},
        {"nome": "- Cap 07 - 2. Contacao de historias - Parte 2.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1RMfy0pjs0brssArC2R2Bc40ibDwwIRV7"},
        {"nome": "- Cap 08 - 3. Storyboard - Parte 1.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1k8WeKu_7DgdTTJN8LjG7lNaJvOKoB5te"},
        {"nome": "- Cap 09 - 3. Storyboard - Parte 2.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1QGgQN8vmurpvCMC5qOyEtmh9GrIIzxXj"},
        {"nome": "- Cap 11 - 7. Tempo use um cronometro.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1G6V07BV3EqnJWHPISnF4aFg11YB4nSN7"},
        {"nome": "- Cap 12 - 4. Sentido de cor.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1PAynda7ljlhhhRmL6WIQJZJR9FQCVsPh"},
        {"nome": "- Cap 13 - 5. Ciencia Estranha.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1p_Uhn_umMiqTwBmsTkC4aIPsE5yredq1"},
        {"nome": "- Cap 17 - 7. Experimente movimento.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1rQvMTXS0B2lVgv1npjz9unIEu1MYZar9"},
        {"nome": "- Cap 18 - 6. Ideias solidas - Parte 1.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1ewAcLJHvUl2KDg1BhuSJBdrjq7rUNUvM"},
        {"nome": "- Cap 19 - 6. Ideias solidas - Parte 2.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1aoZcoy798ivDMZrOVlr2Dy-soKKOIrgY"},
        {"nome": "- Cap 22 - 4. Musica como efeitos sonoros.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=18XtB7GSQ7AZUflw2cTGipc8LFt2FGxZ5"},
        {"nome": "- Cap 23 - 7. Projete o Pais das Maravilhas.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=13MzZEt5xMr41SXQPwQ-3xDjh1lH3_gfO"},
        {"nome": "- Cap 24 - 8. Tecnica - Parte 1.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1TBXQ6YiAIaHIHcg8cJPVbaldbdsOd4nO"},
        {"nome": "- Cap 25 - 8. Tecnica - Parte 2.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=15zUDTYcuwm76-NMN3GShKh11sEeVdXbX"},
        {"nome": "- Cap 26 - 1. Considere o formato.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1Yy43j5Z5XKogUCP52f3erXZoYBCUq7kh"},
        {"nome": "- Cap 27 - 9. Animar.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1zJoWnqXdx2OJH-G4k0yezif1pDQ_-sad"},
        {"nome": "- Cap 28 - 10. Mostre e conte - Parte 1.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1hIA8yyj2uyl-_4vQtzC7ZHWpASziTd8g"},
        {"nome": "- Cap 29 - 10. Mostre e conte - Parte 2.mp3", "direct_url": "https://drive.google.com/uc?export=download&id=1q8OmbYZ5HVS8yJor8OlDaW3v8AbzNUkA"},
    ]

    pasta = Path(".")
    arquivo = gerar_rss_livro(resultados, "Animated Storytelling - Liz Blazer", pasta)
    print(f"[OK] RSS gerado: {arquivo}")
    print(f"Apos subir para o GitHub, a URL sera:")
    print(f"https://andrezoepaiva-commits.github.io/caxinguele-audiobooks/{arquivo.name}")
