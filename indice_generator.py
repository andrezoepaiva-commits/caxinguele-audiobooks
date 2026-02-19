"""
Gerador de indice JSON para a Custom Skill Alexa
Cria indice.json no GitHub Pages com todos os documentos

O indice.json e consumido pela Lambda Function para listar
documentos sem precisar parsear multiplos RSS.

Formato:
{
  "documentos": [
    {
      "titulo": "Sapiens",
      "url_audio": "https://...",
      "categoria": "Livros",
      "data": "2026-02-19",
      "duracao_min": 180
    },
    ...
  ],
  "atualizado_em": "2026-02-19T10:00:00"
}
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def gerar_indice(pasta_rss: Path, pasta_saida: Path = None) -> Path:
    """
    Le todos os arquivos RSS na pasta e gera indice.json consolidado.

    Args:
        pasta_rss: Pasta com arquivos .xml de RSS
        pasta_saida: Pasta de saida (default: mesma pasta do RSS)

    Returns:
        Path do arquivo indice.json gerado
    """
    import xml.etree.ElementTree as ET

    if pasta_saida is None:
        pasta_saida = pasta_rss

    documentos = []
    ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"

    # Le todos os RSS da pasta
    for arquivo_rss in sorted(pasta_rss.glob("*.xml")):
        try:
            tree = ET.parse(str(arquivo_rss))
            root = tree.getroot()
            channel = root.find("channel")

            if channel is None:
                continue

            titulo_feed = channel.findtext("title", arquivo_rss.stem)
            categoria = channel.findtext("category", "Documentos")

            # Pega todos os episodios
            for item in channel.findall("item"):
                titulo = item.findtext("title", "Sem titulo")
                enclosure = item.find("enclosure")
                url_audio = enclosure.get("url", "") if enclosure is not None else ""
                pub_date = item.findtext("pubDate", "")

                # Converte data para formato simples
                data_simples = _parsear_data(pub_date)

                if url_audio:
                    documentos.append({
                        "titulo": titulo,
                        "titulo_feed": titulo_feed,
                        "url_audio": url_audio,
                        "categoria": categoria,
                        "data": data_simples,
                        "rss_arquivo": arquivo_rss.name,
                    })

        except Exception as e:
            logging.warning(f"Erro ao ler {arquivo_rss.name}: {e}")

    # Ordena por data (mais recente primeiro)
    documentos.sort(key=lambda d: d.get("data", ""), reverse=True)

    # Gera indice.json
    indice = {
        "documentos": documentos,
        "total": len(documentos),
        "atualizado_em": datetime.now().isoformat(),
        "versao": "2.0",
    }

    arquivo_indice = pasta_saida / "indice.json"
    with open(arquivo_indice, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

    logging.info(f"Indice gerado: {len(documentos)} documentos -> {arquivo_indice}")
    return arquivo_indice


def _parsear_data(pub_date: str) -> str:
    """Converte data RSS (RFC 2822) para formato YYYY-MM-DD"""
    if not pub_date:
        return datetime.now().strftime("%Y-%m-%d")

    # Tenta parsear formato RFC 2822: "Thu, 19 Feb 2026 10:00:00 +0000"
    formatos = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S +0000",
        "%Y-%m-%d",
    ]

    for fmt in formatos:
        try:
            dt = datetime.strptime(pub_date.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return datetime.now().strftime("%Y-%m-%d")


def adicionar_ao_indice(arquivo_indice: Path, novo_documento: Dict) -> bool:
    """
    Adiciona um documento ao indice existente (evita reprocessar tudo).

    Args:
        arquivo_indice: Path do indice.json
        novo_documento: Dict com titulo, url_audio, categoria, data

    Returns:
        True se adicionado, False se ja existia
    """
    if not arquivo_indice.exists():
        # Cria indice do zero
        indice = {"documentos": [], "total": 0, "atualizado_em": "", "versao": "2.0"}
    else:
        with open(arquivo_indice, encoding="utf-8") as f:
            indice = json.load(f)

    # Verifica se ja existe
    url_nova = novo_documento.get("url_audio", "")
    for doc in indice.get("documentos", []):
        if doc.get("url_audio") == url_nova:
            logging.info(f"Documento ja no indice: {novo_documento.get('titulo')}")
            return False

    # Adiciona no inicio (mais recente primeiro)
    indice["documentos"].insert(0, novo_documento)
    indice["total"] = len(indice["documentos"])
    indice["atualizado_em"] = datetime.now().isoformat()

    with open(arquivo_indice, "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

    logging.info(f"Adicionado ao indice: {novo_documento.get('titulo')}")
    return True


if __name__ == "__main__":
    # Teste: gera indice a partir dos RSS na pasta audiobooks/
    from pathlib import Path

    pasta = Path("audiobooks")
    if pasta.exists():
        arquivo = gerar_indice(pasta)
        print(f"Indice gerado: {arquivo}")
    else:
        print("Pasta audiobooks/ nao encontrada")
