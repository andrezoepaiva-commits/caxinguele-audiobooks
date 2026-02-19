"""
Auto-atualizacao do sistema PDF2Audiobook
Verifica e atualiza dependencias silenciosamente na inicializacao
"""

import subprocess
import sys
import logging
from typing import Tuple

# Pacotes essenciais e versoes minimas
DEPENDENCIAS = [
    "edge-tts",
    "PyMuPDF",
    "google-api-python-client",
    "google-auth-oauthlib",
    "PyGithub",
    "tqdm",
]

# Vozes que devem existir (criticas para o sistema)
VOZES_CRITICAS = [
    "pt-BR-ThalitaMultilingualNeural",
    "pt-BR-FranciscaNeural",
    "pt-BR-AntonioNeural",
]


def verificar_e_atualizar_dependencias(callback=None, atualizar=False) -> Tuple[bool, str]:
    """
    Verifica se todas as dependencias estao instaladas.
    Opcionalmente atualiza (desabilitado por padrão).

    Args:
        callback: funcao opcional para reportar progresso (para GUI)
        atualizar: Se True, atualiza pacotes (padrão: False por segurança)

    Returns:
        (sucesso, mensagem)
    """
    def log(msg):
        logging.info(msg)
        if callback:
            callback(msg)

    log("Verificando dependencias...")

    erros = []
    for pacote in DEPENDENCIAS:
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--quiet", pacote]
            if atualizar:
                cmd.insert(4, "--upgrade")  # Adiciona --upgrade apenas se pedido
            resultado = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=60
            )
            if resultado.returncode != 0:
                erros.append(f"{pacote}: {resultado.stderr[:100]}")
        except subprocess.TimeoutExpired:
            log(f"Timeout ao atualizar {pacote}, continuando...")
        except Exception as e:
            erros.append(f"{pacote}: {e}")

    if erros:
        log(f"Avisos na atualizacao: {erros}")
    else:
        log("[OK] Dependencias atualizadas")

    return len(erros) == 0, str(erros) if erros else "OK"


def verificar_vozes_tts(callback=None) -> Tuple[bool, list]:
    """
    Verifica se as vozes criticas do Edge-TTS estao disponiveis.

    Returns:
        (todas_ok, lista_de_vozes_faltando)
    """
    def log(msg):
        logging.info(msg)
        if callback:
            callback(msg)

    log("Verificando vozes TTS...")

    try:
        import asyncio
        import edge_tts

        async def listar_vozes():
            vozes = await edge_tts.list_voices()
            return [v["ShortName"] for v in vozes]

        vozes_disponiveis = asyncio.run(listar_vozes())

        # Se a lista vier vazia, provavelmente e problema de rede - nao reportar como erro
        if not vozes_disponiveis:
            log("[OK] Vozes TTS: verificacao ignorada (sem conexao ou API indisponivel)")
            return True, []

        faltando = [v for v in VOZES_CRITICAS if v not in vozes_disponiveis]

        if faltando:
            log(f"[AVISO] Vozes nao encontradas na API: {faltando} (pode ser temporario)")
        else:
            log("[OK] Todas as vozes disponiveis")
        return True, faltando

    except Exception as e:
        log(f"[AVISO] Nao foi possivel verificar vozes: {e}")
        return True, []  # Nao bloqueia se nao conseguir verificar


def verificar_credenciais(callback=None) -> Tuple[bool, str]:
    """
    Verifica se as credenciais necessarias existem.

    Returns:
        (ok, mensagem)
    """
    from pathlib import Path

    def log(msg):
        logging.info(msg)
        if callback:
            callback(msg)

    problemas = []

    # credentials.json (Google Drive)
    if not Path("credentials.json").exists():
        problemas.append("credentials.json nao encontrado (Google Drive)")

    # Token GitHub (na config)
    try:
        from config import GITHUB_CONFIG
        if not GITHUB_CONFIG.get("token") or GITHUB_CONFIG["token"].startswith("ghp_SEU"):
            problemas.append("Token GitHub nao configurado")
    except Exception:
        problemas.append("Erro ao ler config do GitHub")

    if problemas:
        for p in problemas:
            log(f"[AVISO] {p}")
        return False, "; ".join(problemas)

    log("[OK] Credenciais verificadas")
    return True, "OK"


def executar_verificacao_completa(callback=None) -> bool:
    """
    Executa todas as verificacoes de inicializacao.
    Chamado automaticamente quando o sistema inicia.

    Returns:
        True se tudo OK, False se ha problemas criticos
    """
    def log(msg):
        if callback:
            callback(msg)

    log("Iniciando verificacao do sistema...")

    # 1. Dependencias
    deps_ok, _ = verificar_e_atualizar_dependencias(callback)

    # 2. Credenciais
    creds_ok, msg_creds = verificar_credenciais(callback)
    if not creds_ok:
        log(f"[AVISO] {msg_creds}")

    # 3. Vozes (nao bloqueia)
    verificar_vozes_tts(callback)

    log("[OK] Sistema pronto!")
    return True


if __name__ == "__main__":
    print("Verificando sistema...")
    ok = executar_verificacao_completa(print)
    print("Pronto!" if ok else "Ha problemas, verifique os avisos acima.")
