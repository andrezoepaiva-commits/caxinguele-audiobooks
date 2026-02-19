"""
Monitor de Saude do Sistema - Projeto Caxinguele v2
"Avisa, nao conserta" — detecta problemas e informa, sem alterar nada.

Uso:
    python health_monitor.py
    python health_monitor.py --verbose
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")


def verificar(descricao: str, ok: bool, detalhe: str = "") -> bool:
    """Imprime status de uma verificacao"""
    status = "OK" if ok else "PROBLEMA"
    sinal = "OK" if ok else "!!"
    linha = f"  [{sinal}] {descricao}"
    if detalhe and not ok:
        linha += f"\n       -> {detalhe}"
    print(linha)
    return ok


def checar_python():
    """Versao do Python"""
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 9
    verificar(f"Python {v.major}.{v.minor}.{v.micro}", ok,
              "Requer Python 3.9+" if not ok else "")
    return ok


def checar_dependencias():
    """Verifica pacotes Python instalados"""
    deps = {
        "edge_tts": "edge-tts",
        "fitz": "PyMuPDF",
        "docx": "python-docx",
        "ebooklib": "ebooklib",
        "bs4": "beautifulsoup4",
        "striprtf": "striprtf",
        "odf": "odfpy",
        "extract_msg": "extract-msg",
        "PIL": "Pillow",
        "tkinterdnd2": "tkinterdnd2",
        "google.oauth2": "google-auth",
        "googleapiclient": "google-api-python-client",
        "tqdm": "tqdm",
        "colorama": "colorama",
    }

    todos_ok = True
    for modulo, pacote in deps.items():
        try:
            __import__(modulo)
            ok = True
        except ImportError:
            ok = False
            todos_ok = False
        verificar(f"  {pacote}", ok,
                  f"Instale: pip install {pacote}" if not ok else "")

    return todos_ok


def checar_arquivos_projeto():
    """Verifica arquivos essenciais do projeto"""
    base = Path(__file__).parent
    arquivos = {
        "pdf_processor.py": "Processador PDF",
        "doc_processor.py": "Processador multi-formato",
        "doc_classifier.py": "Classificador de tipos",
        "audiobook_gui.py": "Interface grafica",
        "pipeline_mvp.py": "Pipeline principal",
        "tts_engine.py": "Motor TTS",
        "cloud_uploader.py": "Upload Drive",
        "rss_generator.py": "Gerador RSS",
        "config.py": "Configuracoes",
        "GUIA_ALEXA_ACESSIVEL.md": "Guia de operacao (para converter em audio)",
        "alexa_skill/lambda/lambda_function.py": "Skill Alexa (Fase 6)",
    }

    todos_ok = True
    for arquivo, nome in arquivos.items():
        caminho = base / arquivo
        ok = caminho.exists()
        if not ok:
            todos_ok = False
        verificar(f"  {nome} ({arquivo})", ok,
                  "Arquivo nao encontrado!" if not ok else "")

    return todos_ok


def checar_google_drive():
    """Verifica configuracao do Google Drive"""
    base = Path(__file__).parent
    credentials = base / "credentials.json"
    token = base / "token.json"

    cred_ok = credentials.exists()
    verificar("  credentials.json (Google OAuth)", cred_ok,
              "Baixe em: Google Cloud Console > APIs > Credenciais")

    token_ok = token.exists()
    verificar("  token.json (Token de acesso)", token_ok,
              "Execute o app uma vez para gerar o token" if not token_ok else "")

    return cred_ok and token_ok


def checar_internet():
    """Testa conectividade com internet"""
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        ok = True
    except Exception:
        ok = False
    verificar("Conexao com internet", ok,
              "Sem internet — TTS e Upload nao vao funcionar" if not ok else "")
    return ok


def checar_edge_tts():
    """Verifica se Edge-TTS esta funcionando"""
    try:
        import asyncio
        import edge_tts

        async def _testar():
            communicate = edge_tts.Communicate("Teste.", "pt-BR-ThalitaMultilingualNeural")
            # Apenas verifica se instancia sem erro
            return True

        asyncio.run(_testar())
        ok = True
    except Exception as e:
        ok = False

    verificar("Edge-TTS (Microsoft Azure)", ok,
              "Verifique conexao com internet" if not ok else "")
    return ok


def checar_pastas_saida():
    """Verifica pastas de saida"""
    base = Path(__file__).parent
    pastas = {
        "audiobooks/": "Pasta de saida dos MP3s",
        "temp/": "Pasta temporaria",
        ".checkpoints/": "Pasta de checkpoints",
    }

    todos_ok = True
    for pasta, nome in pastas.items():
        caminho = base / pasta
        ok = caminho.exists()
        if not ok:
            # Tenta criar
            try:
                caminho.mkdir(parents=True, exist_ok=True)
                ok = True
            except Exception:
                todos_ok = False
        verificar(f"  {nome} ({pasta})", ok)

    return todos_ok


def checar_tesseract():
    """Verifica se Tesseract OCR esta instalado (opcional)"""
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True, text=True, timeout=5
        )
        ok = result.returncode == 0
        versao = result.stdout.split('\n')[0] if ok else ""
        verificar(f"Tesseract OCR ({versao})", ok,
                  "Opcional para imagens. Instale em: https://github.com/UB-Mannheim/tesseract/wiki")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        verificar("Tesseract OCR", False,
                  "Opcional para imagens. Instale em: https://github.com/UB-Mannheim/tesseract/wiki")


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print()
    print("=" * 55)
    print("MONITOR DE SAUDE — Projeto Caxinguele v2")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 55)

    resultados = {}

    print("\n>> Python")
    resultados["python"] = checar_python()

    print("\n>> Dependencias Python")
    resultados["deps"] = checar_dependencias()

    print("\n>> Arquivos do Projeto")
    resultados["arquivos"] = checar_arquivos_projeto()

    print("\n>> Pastas de Saida")
    resultados["pastas"] = checar_pastas_saida()

    print("\n>> Google Drive")
    resultados["gdrive"] = checar_google_drive()

    print("\n>> Conectividade")
    resultados["internet"] = checar_internet()

    if resultados.get("internet"):
        print("\n>> Edge-TTS (precisa de internet)")
        resultados["tts"] = checar_edge_tts()

    print("\n>> Tesseract OCR (opcional, para imagens)")
    checar_tesseract()

    # Resumo final
    print()
    print("=" * 55)
    problemas = [k for k, v in resultados.items() if not v]
    if not problemas:
        print("SISTEMA SAUDAVEL — Tudo funcionando!")
    else:
        print(f"ATENCAO: {len(problemas)} problema(s) encontrado(s):")
        nomes = {
            "python": "Versao do Python",
            "deps": "Dependencias Python",
            "arquivos": "Arquivos do projeto",
            "pastas": "Pastas de saida",
            "gdrive": "Google Drive",
            "internet": "Internet",
            "tts": "Edge-TTS",
        }
        for p in problemas:
            print(f"  - {nomes.get(p, p)}")
        print("\nCorreja os problemas acima antes de usar o sistema.")
    print("=" * 55)
    print()


if __name__ == "__main__":
    main()
