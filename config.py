"""
Configurações centralizadas do sistema PDF2Audiobook
Sistema para converter PDFs em audiobooks acessíveis via Alexa
"""

import os
from pathlib import Path

# Carrega .env se existir (sem depender de python-dotenv)
def _carregar_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for linha in env_file.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, _, valor = linha.partition("=")
                os.environ.setdefault(chave.strip(), valor.strip())

_carregar_env()

# ==================== DIRETÓRIOS ====================

# Diretório base do projeto
BASE_DIR = Path(__file__).parent.absolute()

# Diretório para arquivos temporários
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Diretório para audiobooks gerados
OUTPUT_DIR = BASE_DIR / "audiobooks"
OUTPUT_DIR.mkdir(exist_ok=True)

# Diretório para checkpoints (para retomar processamento)
CHECKPOINT_DIR = BASE_DIR / ".checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)

# ==================== VOZES TTS (Edge-TTS) ====================

# Vozes neurais português disponíveis
VOZES_PT_BR = {
    # Brasil (sotaque brasileiro)
    "francisca": "pt-BR-FranciscaNeural",  # Feminina, jovem, natural
    "camila": "pt-BR-CamilaNeural",        # Feminina, madura, profissional
    "antonio": "pt-BR-AntonioNeural",      # Masculino, claro
    "thalita": "pt-BR-ThalitaMultilingualNeural",  # Feminina, suave
    # Portugal (sotaque português)
    "raquel": "pt-PT-RaquelNeural",        # Feminina, clara
    "duarte": "pt-PT-DuarteNeural",        # Masculino, profissional
}

# Voz padrão (recomendada) - armazenar como CHAVE, não como valor
VOZ_PADRAO = "francisca"

# ==================== SERVIDORES EDGE-TTS (FALLBACK) ====================

# Lista de servidores Edge-TTS para retry automático
# Se um falhar, tenta o próximo automaticamente
EDGE_TTS_SERVERS = [
    None,           # Servidor padrão (Azure automático)
    "westeurope",   # Europa Ocidental
    "eastus",       # Estados Unidos Leste
]

# ==================== CONFIGURAÇÕES DE ÁUDIO ====================

AUDIO_CONFIG = {
    # Bitrate (qualidade vs tamanho)
    # 64k = boa qualidade, economiza espaço
    # 128k = alta qualidade, mais espaço
    "bitrate": "64k",

    # Canais de áudio
    # 1 = mono (recomendado para audiobooks)
    # 2 = estéreo
    "channels": 1,

    # Taxa de amostragem (Hz)
    # 24000 = padrão Edge-TTS, boa qualidade
    # 48000 = alta qualidade
    "sample_rate": 24000,

    # Formato de saída
    "format": "mp3",

    # Normalização de volume (evita partes muito baixas/altas)
    "normalize": True,
}

# ==================== PROCESSAMENTO PDF ====================

PDF_CONFIG = {
    # Detecção automática de OCR
    # Se True, verifica se o PDF precisa de OCR e aplica automaticamente
    "auto_ocr": True,

    # Idioma para OCR (Tesseract)
    "ocr_language": "por",  # Português

    # Limpar texto automaticamente
    # Remove headers, footers, números de página, etc.
    "auto_cleanup": True,

    # Máximo de palavras por chunk de áudio
    # Chunks menores = mais arquivos, mais controle
    # Chunks maiores = menos arquivos, menos controle
    "max_chunk_words": 3000,
}

# ==================== PROCESSAMENTO PARALELO ====================

# Número de threads para processamento TTS paralelo
# 3 = bom equilíbrio (processa 3 capítulos simultaneamente)
# Mais threads = mais rápido, mas mais memória RAM
NUM_THREADS_TTS = 3

# ==================== RETRY E TIMEOUTS ====================

# Número máximo de tentativas para operações que podem falhar
MAX_RETRIES = 3

# Tempo de espera entre tentativas (segundos)
RETRY_DELAY = 5

# Tempo de espera entre tentativas (cresce exponencialmente)
# Tentativa 1: 5s
# Tentativa 2: 15s (5s * 3)
# Tentativa 3: 45s (15s * 3)
RETRY_EXPONENTIAL = True

# Timeout para upload de arquivos (segundos)
UPLOAD_TIMEOUT = 300  # 5 minutos

# Timeout para conversão TTS por chunk (segundos)
TTS_TIMEOUT = 120  # 2 minutos

# ==================== GOOGLE DRIVE ====================

GDRIVE_CONFIG = {
    # Arquivo de credenciais Google Drive
    "credentials_file": BASE_DIR / "credentials.json",

    # Arquivo de token (gerado após primeira autenticação)
    "token_file": BASE_DIR / "token.json",

    # Pasta raiz no Google Drive para audiobooks
    "root_folder": "Audiobooks - Alexa",

    # Tornar arquivos públicos automaticamente
    "make_public": True,
}

# ==================== LOGGING ====================

LOG_CONFIG = {
    # Nível de log
    # DEBUG = tudo
    # INFO = informações importantes
    # WARNING = avisos
    # ERROR = apenas erros
    "level": "INFO",

    # Mostrar cores no terminal
    "colored": True,

    # Salvar logs em arquivo
    "save_to_file": True,

    # Arquivo de log
    "log_file": BASE_DIR / "pdf2audiobook.log",
}

# ==================== FEATURES ESPECIAIS ====================

# Criar checkpoint automático para retomar processamento
ENABLE_CHECKPOINTS = True

# Arquivo de checkpoint
CHECKPOINT_FILE = CHECKPOINT_DIR / ".checkpoint_mvp.json"

# Exibir barra de progresso
SHOW_PROGRESS_BAR = True

# Notificar quando concluir (beep)
NOTIFY_ON_COMPLETE = True

# Estimativa de tempo restante
SHOW_TIME_ESTIMATE = True

# ==================== VALIDAÇÕES ====================

# Tamanho máximo de PDF aceito (MB)
MAX_PDF_SIZE_MB = 500

# Mínimo de páginas para ser considerado um livro
# (reduzido para 2 para permitir testes rápidos)
MIN_PAGES = 2

# ==================== GITHUB PAGES (RSS) ====================

import os

GITHUB_CONFIG = {
    "token": os.getenv("GITHUB_TOKEN", ""),  # Use variável de ambiente GITHUB_TOKEN
    "user": "andrezoepaiva-commits",
    "repo": "caxinguele-audiobooks",
    "pages_url": "https://andrezoepaiva-commits.github.io/caxinguele-audiobooks",
}

# ==================== SPOTIFY (PODCAST) ====================

SPOTIFY_CONFIG = {
    "podcast_url": "https://open.spotify.com/show/4L5UdNXsjzAct7njPwVuoQ",
    "podcast_email": "andrefmdepaiva@gmail.com",
}

# ==================== MYPOD (ALEXA) ====================

MYPOD_CONFIG = {
    # URL do MyPod
    "url": "https://mypodapp.com",

    # Gerar instruções de setup automaticamente
    "generate_instructions": True,

    # Nome do arquivo de instruções
    "instructions_file": "README_MyPod.txt",
}

# ==================== PERFIS DE DESTINATÁRIO ====================

# Perfis de usuário para o seletor "Enviar para:"
PERFIS_USUARIOS = {
    "eu": {
        "nome": "Eu (André)",
        "gdrive_root": "Audiobooks - Alexa",
        "rss_repo": "caxinguele-audiobooks",
    },
    "amigo": {
        "nome": "Meu Amigo",
        "gdrive_root": "Audiobooks - Alexa",  # Mesma pasta (compartilhada via Household)
        "rss_repo": "caxinguele-audiobooks",
    },
}

DESTINATARIO_PADRAO = "eu"

# ==================== TAMANHO MÁXIMO DE DOCUMENTOS ====================

# Tamanho máximo aceito para qualquer formato (MB)
MAX_DOC_SIZE_MB = 500

# ==================== MENSAGENS DO SISTEMA ====================

MESSAGES = {
    "welcome": """
===========================================================
     Projeto Caxinguele - Audiobooks para Alexa

  Converte documentos em audiobooks acessiveis via voz
  Formatos: PDF, Word, EPUB, Email, Imagem e mais
===========================================================
    """,

    "success": "[OK] Concluido com sucesso!",
    "error": "[ERRO]",
    "warning": "[AVISO]",
    "info": "[INFO]",
    "processing": "Processando...",
}
