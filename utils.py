"""
Funções utilitárias para o sistema PDF2Audiobook
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import timedelta

from colorama import Fore, Style, init as colorama_init
from tqdm import tqdm

# Inicializar colorama (cores no Windows)
colorama_init(autoreset=True)


# ==================== LOGGING COLORIDO ====================

class ColoredFormatter(logging.Formatter):
    """Formatter com cores para diferentes níveis de log"""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Adiciona cor baseado no nível
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        return super().format(record)


def setup_logging(level: str = "INFO", colored: bool = True, log_file: Optional[Path] = None):
    """
    Configura o sistema de logging

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        colored: Se True, usa cores no terminal
        log_file: Caminho para arquivo de log (opcional)
    """
    # Remove handlers existentes
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Define o nível
    root_logger.setLevel(getattr(logging, level.upper()))

    # Handler para console
    console_handler = logging.StreamHandler()
    if colored:
        console_formatter = ColoredFormatter(
            '%(levelname)s | %(message)s'
        )
    else:
        console_formatter = logging.Formatter(
            '%(levelname)s | %(message)s'
        )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Handler para arquivo (se especificado)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


# ==================== VALIDAÇÃO DE ARQUIVOS ====================

def validar_pdf(caminho: Path) -> Tuple[bool, str]:
    """
    Valida se o arquivo PDF existe e pode ser processado

    Args:
        caminho: Path do arquivo PDF

    Returns:
        Tupla (sucesso: bool, mensagem: str)
    """
    caminho = Path(caminho)

    # Verifica se existe
    if not caminho.exists():
        return False, f"Arquivo não encontrado: {caminho}"

    # Verifica extensão
    if caminho.suffix.lower() != '.pdf':
        return False, f"Arquivo não é PDF: {caminho.suffix}"

    # Verifica se é arquivo (não diretório)
    if not caminho.is_file():
        return False, f"Caminho não é um arquivo: {caminho}"

    # Verifica tamanho
    tamanho_mb = caminho.stat().st_size / (1024 * 1024)
    if tamanho_mb == 0:
        return False, "Arquivo PDF vazio"

    return True, f"PDF válido ({tamanho_mb:.1f} MB)"


# ==================== FORMATAÇÃO ====================

def formatar_tempo(segundos: float) -> str:
    """
    Formata segundos em formato legível

    Args:
        segundos: Tempo em segundos

    Returns:
        String formatada (ex: "2h 30min", "45min", "30s")
    """
    if segundos < 60:
        return f"{int(segundos)}s"

    minutos = int(segundos / 60)
    if minutos < 60:
        return f"{minutos}min"

    horas = minutos // 60
    minutos_restantes = minutos % 60

    if minutos_restantes == 0:
        return f"{horas}h"
    else:
        return f"{horas}h {minutos_restantes}min"


def formatar_tamanho(bytes: int) -> str:
    """
    Formata bytes em formato legível

    Args:
        bytes: Tamanho em bytes

    Returns:
        String formatada (ex: "1.5 MB", "500 KB")
    """
    if bytes < 1024:
        return f"{bytes} B"

    kb = bytes / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"

    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"

    gb = mb / 1024
    return f"{gb:.1f} GB"


def normalizar_nome_arquivo(texto: str) -> str:
    """
    Normaliza texto para ser usado como nome de arquivo

    Remove caracteres especiais, espaços extras, etc.

    Args:
        texto: Texto a ser normalizado

    Returns:
        Texto normalizado
    """
    # Remove caracteres não permitidos em nomes de arquivo
    texto = re.sub(r'[<>:"/\\|?*]', '', texto)

    # Remove espaços extras
    texto = re.sub(r'\s+', ' ', texto)

    # Remove espaços no início e fim
    texto = texto.strip()

    # Limita tamanho (máximo 100 caracteres)
    if len(texto) > 100:
        texto = texto[:100]

    return texto


# ==================== PROGRESS BAR ====================

def criar_progress_bar(total: int, desc: str) -> tqdm:
    """
    Cria uma barra de progresso customizada

    Args:
        total: Total de iterações
        desc: Descrição da barra

    Returns:
        Objeto tqdm
    """
    return tqdm(
        total=total,
        desc=desc,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
        colour='green'
    )


# ==================== LIMPEZA DE TEXTO ====================

def limpar_texto_para_tts(texto: str) -> str:
    """
    Limpa texto para ser processado pelo TTS

    Remove elementos que podem atrapalhar a leitura natural:
    - URLs
    - Emails
    - Códigos de programação
    - Caracteres especiais excessivos

    Args:
        texto: Texto original

    Returns:
        Texto limpo
    """
    # Remove URLs
    texto = re.sub(r'https?://\S+', '', texto)

    # Remove emails
    texto = re.sub(r'\S+@\S+', '', texto)

    # Remove múltiplas linhas em branco
    texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)

    # Remove espaços extras
    texto = re.sub(r' +', ' ', texto)

    # Remove underscores e asteriscos (markdown)
    texto = texto.replace('_', ' ').replace('*', '')

    # Normaliza travessões
    texto = texto.replace('—', '-').replace('–', '-')

    return texto.strip()


# ==================== DETECÇÃO DE IDIOMA ====================

def detectar_idioma(texto: str) -> str:
    """
    Detecta o idioma de um texto (simples, baseado em palavras comuns)

    Args:
        texto: Texto a ser analisado

    Returns:
        Código do idioma ("pt-BR", "en-US", etc.)
    """
    # Palavras comuns em português
    palavras_pt = ['que', 'não', 'uma', 'para', 'com', 'mais', 'por', 'como', 'mas', 'dos']

    # Palavras comuns em inglês
    palavras_en = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'with', 'that', 'this']

    # Converte para minúsculas
    texto_lower = texto.lower()

    # Conta ocorrências
    count_pt = sum(1 for palavra in palavras_pt if f' {palavra} ' in texto_lower)
    count_en = sum(1 for palavra in palavras_en if f' {palavra} ' in texto_lower)

    # Decide baseado em qual teve mais ocorrências
    if count_pt > count_en:
        return "pt-BR"
    else:
        return "en-US"


# ==================== CHECKPOINT ====================

def salvar_checkpoint(checkpoint_file: Path, dados: dict):
    """
    Salva checkpoint do processamento

    Args:
        checkpoint_file: Path do arquivo de checkpoint
        dados: Dicionário com dados a salvar
    """
    # Adiciona timestamp
    dados['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

    # Salva como JSON
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

    logging.debug(f"Checkpoint salvo: {checkpoint_file}")


def carregar_checkpoint(checkpoint_file: Path) -> Optional[dict]:
    """
    Carrega checkpoint do processamento

    Args:
        checkpoint_file: Path do arquivo de checkpoint

    Returns:
        Dicionário com dados do checkpoint ou None se não existir
    """
    if not checkpoint_file.exists():
        return None

    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        logging.debug(f"Checkpoint carregado: {checkpoint_file}")
        return dados
    except Exception as e:
        logging.warning(f"Erro ao carregar checkpoint: {e}")
        return None


def limpar_checkpoint(checkpoint_file: Path):
    """
    Remove arquivo de checkpoint

    Args:
        checkpoint_file: Path do arquivo de checkpoint
    """
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        logging.debug(f"Checkpoint removido: {checkpoint_file}")


# ==================== LIMPEZA DE ARQUIVOS TEMPORÁRIOS ====================

def limpar_arquivos_temp(pasta: Path, padrao: str = "*"):
    """
    Remove arquivos temporários de uma pasta

    Args:
        pasta: Path da pasta
        padrao: Padrão de arquivos a remover (ex: "*.tmp", "*.wav")
    """
    if not pasta.exists():
        return

    arquivos_removidos = 0
    for arquivo in pasta.glob(padrao):
        if arquivo.is_file():
            try:
                arquivo.unlink()
                arquivos_removidos += 1
            except Exception as e:
                logging.warning(f"Erro ao remover {arquivo}: {e}")

    if arquivos_removidos > 0:
        logging.info(f"Removidos {arquivos_removidos} arquivos temporários de {pasta}")


# ==================== RETRY COM EXPONENTIAL BACKOFF ====================

def retry_com_backoff(funcao, max_tentativas: int = 3, delay_inicial: int = 5, exponencial: bool = True):
    """
    Executa função com retry e exponential backoff

    Args:
        funcao: Função a executar (sem parênteses, será chamada)
        max_tentativas: Número máximo de tentativas
        delay_inicial: Delay inicial entre tentativas (segundos)
        exponencial: Se True, delay cresce exponencialmente

    Returns:
        Resultado da função

    Raises:
        Exception: Se todas as tentativas falharem
    """
    delay = delay_inicial
    ultima_excecao = None

    for tentativa in range(1, max_tentativas + 1):
        try:
            return funcao()
        except Exception as e:
            ultima_excecao = e
            if tentativa < max_tentativas:
                logging.warning(f"Tentativa {tentativa}/{max_tentativas} falhou: {e}. Tentando novamente em {delay}s...")
                time.sleep(delay)

                if exponencial:
                    delay *= 3  # Cresce exponencialmente
            else:
                logging.error(f"Todas as {max_tentativas} tentativas falharam.")

    # Se chegou aqui, todas falharam
    raise ultima_excecao


# ==================== NOTIFICAÇÃO SONORA ====================

def notificar_conclusao():
    """Emite beep de notificação (multiplataforma)"""
    try:
        import sys
        if sys.platform == 'win32':
            import winsound
            winsound.Beep(1000, 500)  # Frequência 1000Hz, duração 500ms
        else:
            # Linux/Mac
            print('\a')  # Bell character
    except:
        pass  # Silenciosamente falha se não conseguir


# ==================== ESTIMATIVA DE TEMPO ====================

class EstimadorTempo:
    """Classe para estimar tempo restante de processamento"""

    def __init__(self, total_items: int):
        self.total_items = total_items
        self.items_processados = 0
        self.tempo_inicio = time.time()

    def atualizar(self, items_processados: int = 1):
        """Atualiza contador de items processados"""
        self.items_processados += items_processados

    def tempo_restante(self) -> str:
        """
        Calcula tempo restante estimado

        Returns:
            String formatada (ex: "45min restantes")
        """
        if self.items_processados == 0:
            return "calculando..."

        tempo_decorrido = time.time() - self.tempo_inicio
        tempo_por_item = tempo_decorrido / self.items_processados
        items_restantes = self.total_items - self.items_processados

        segundos_restantes = tempo_por_item * items_restantes
        return formatar_tempo(segundos_restantes) + " restantes"

    def tempo_total(self) -> str:
        """
        Retorna tempo total decorrido

        Returns:
            String formatada
        """
        tempo_decorrido = time.time() - self.tempo_inicio
        return formatar_tempo(tempo_decorrido)
