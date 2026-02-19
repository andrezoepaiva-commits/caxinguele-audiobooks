"""
Upload automatico de arquivos RSS para o GitHub Pages
Usa PyGithub para criar/atualizar arquivos no repositorio
"""

import logging
from pathlib import Path
from typing import Optional

from github import Github, GithubException

from config import GITHUB_CONFIG


def obter_repo():
    """Conecta ao repositorio GitHub e retorna o objeto repo"""
    g = Github(GITHUB_CONFIG["token"])
    repo = g.get_repo(f"{GITHUB_CONFIG['user']}/{GITHUB_CONFIG['repo']}")
    return repo


def upload_arquivo_github(caminho_local: Path, nome_remoto: Optional[str] = None) -> str:
    """
    Faz upload ou atualiza um arquivo no GitHub.
    Se o arquivo ja existir, substitui. Se nao existir, cria.

    Args:
        caminho_local: Caminho do arquivo local
        nome_remoto: Nome do arquivo no GitHub (se None, usa o mesmo nome)

    Returns:
        URL publica do arquivo no GitHub Pages
    """
    caminho_local = Path(caminho_local)
    if not caminho_local.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {caminho_local}")

    nome_remoto = nome_remoto or caminho_local.name

    with open(caminho_local, "rb") as f:
        conteudo = f.read()

    repo = obter_repo()

    # Verifica se o arquivo ja existe (para atualizar em vez de criar)
    try:
        arquivo_existente = repo.get_contents(nome_remoto)
        repo.update_file(
            path=nome_remoto,
            message=f"Atualiza {nome_remoto}",
            content=conteudo,
            sha=arquivo_existente.sha
        )
        logging.info(f"[OK] GitHub atualizado: {nome_remoto}")
    except GithubException:
        # Arquivo nao existe, cria novo
        repo.create_file(
            path=nome_remoto,
            message=f"Adiciona {nome_remoto}",
            content=conteudo
        )
        logging.info(f"[OK] GitHub criado: {nome_remoto}")

    url = f"https://{GITHUB_CONFIG['user']}.github.io/{GITHUB_CONFIG['repo']}/{nome_remoto}"
    return url


def publicar_rss(caminho_xml: Path, caminho_capa: Optional[Path] = None) -> str:
    """
    Publica o arquivo RSS (e imagem de capa) no GitHub Pages.

    Args:
        caminho_xml: Caminho do arquivo .xml
        caminho_capa: Caminho da imagem de capa (opcional)

    Returns:
        URL publica do RSS
    """
    # Sobe a capa primeiro (se fornecida)
    if caminho_capa and caminho_capa.exists():
        upload_arquivo_github(caminho_capa)
        logging.info(f"Capa publicada: {caminho_capa.name}")

    # Sobe o RSS
    url_rss = upload_arquivo_github(caminho_xml)
    logging.info(f"RSS publicado: {url_rss}")

    return url_rss
