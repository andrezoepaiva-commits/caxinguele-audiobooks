"""
Módulo TTS (Text-to-Speech) usando Edge-TTS
Converte texto em áudio com sistema de retry e fallback
"""

import logging
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import edge_tts

from config import (
    VOZES_PT_BR, VOZ_PADRAO, EDGE_TTS_SERVERS,
    AUDIO_CONFIG, NUM_THREADS_TTS, MAX_RETRIES, TTS_TIMEOUT
)
from utils import criar_progress_bar, normalizar_nome_arquivo, EstimadorTempo


# ==================== LISTAGEM DE VOZES ====================

async def _listar_vozes_async(idioma: str = "pt-BR") -> List[dict]:
    """
    Lista vozes disponíveis (async)

    Args:
        idioma: Código do idioma (ex: "pt-BR", "en-US")

    Returns:
        Lista de dicionários com informações das vozes
    """
    vozes = await edge_tts.list_voices()

    # Filtra por idioma
    vozes_filtradas = [
        {
            'nome': v['ShortName'],
            'nome_completo': v['Name'],
            'genero': v['Gender'],
            'idioma': v['Locale'],
        }
        for v in vozes
        if v['Locale'].startswith(idioma)
    ]

    return vozes_filtradas


def listar_vozes_disponiveis(idioma: str = "pt-BR") -> List[dict]:
    """
    Lista vozes disponíveis (interface síncrona)

    Args:
        idioma: Código do idioma (ex: "pt-BR")

    Returns:
        Lista de vozes disponíveis
    """
    return asyncio.run(_listar_vozes_async(idioma))


def exibir_vozes_disponiveis():
    """Exibe vozes disponíveis no console"""
    logging.info("Vozes disponíveis em português brasileiro:")

    for nome_curto, nome_edge in VOZES_PT_BR.items():
        logging.info(f"  - {nome_curto}: {nome_edge}")

    logging.info("\nPara listar TODAS as vozes, use: listar_vozes_disponiveis()")


# ==================== CONVERSÃO TTS (CORE) ====================

async def _converter_tts_async(
    texto: str,
    voz: str,
    arquivo_saida: Path,
    rate: str = "+0%",
    volume: str = "+0%"
) -> bool:
    """
    Converte texto em áudio (async)

    Args:
        texto: Texto a converter
        voz: Nome da voz (ex: "pt-BR-FranciscaNeural")
        arquivo_saida: Path do arquivo MP3 de saída
        rate: Velocidade (ex: "+10%" mais rápido, "-10%" mais lento)
        volume: Volume (ex: "+10%" mais alto, "-10%" mais baixo)

    Returns:
        True se sucesso, False se falhou
    """
    try:
        # Cria comunicator
        communicate = edge_tts.Communicate(texto, voz, rate=rate, volume=volume)

        # Gera áudio
        await communicate.save(str(arquivo_saida))

        return True

    except Exception as e:
        logging.error(f"Erro na conversão TTS: {e}")
        return False


def converter_texto_para_audio(
    texto: str,
    arquivo_saida: Path,
    voz: str = VOZ_PADRAO,
    rate: str = "+0%",
    volume: str = "+0%",
    max_tentativas: int = MAX_RETRIES
) -> bool:
    """
    Converte texto em áudio com sistema de retry

    Args:
        texto: Texto a converter
        arquivo_saida: Path do arquivo MP3 de saída
        voz: Nome da voz
        rate: Velocidade
        volume: Volume
        max_tentativas: Número máximo de tentativas

    Returns:
        True se sucesso, False se falhou após todas as tentativas
    """
    arquivo_saida = Path(arquivo_saida)
    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)

    # Sistema de retry com fallback de servidores
    for tentativa in range(1, max_tentativas + 1):
        try:
            # Executa conversão assíncrona
            sucesso = asyncio.run(
                _converter_tts_async(texto, voz, arquivo_saida, rate, volume)
            )

            if sucesso and arquivo_saida.exists():
                # Verifica tamanho do arquivo
                tamanho = arquivo_saida.stat().st_size
                if tamanho > 1000:  # Pelo menos 1KB
                    return True
                else:
                    logging.warning(f"Arquivo de áudio muito pequeno ({tamanho} bytes)")

        except Exception as e:
            logging.warning(f"Tentativa {tentativa}/{max_tentativas} falhou: {e}")

        # Se falhou e ainda tem tentativas
        if tentativa < max_tentativas:
            delay = 5 * tentativa  # 5s, 10s, 15s...
            logging.info(f"Aguardando {delay}s antes de tentar novamente...")
            time.sleep(delay)

    # Todas as tentativas falharam
    logging.error(f"Falha ao converter áudio após {max_tentativas} tentativas")
    return False


# ==================== CONVERSÃO COM FALLBACK TTS ====================

def converter_com_fallback_local(texto: str, arquivo_saida: Path) -> bool:
    """
    Fallback local usando pyttsx3 (qualidade inferior)

    Usado apenas se Edge-TTS falhar completamente.

    Args:
        texto: Texto a converter
        arquivo_saida: Path do arquivo de saída

    Returns:
        True se sucesso
    """
    try:
        import pyttsx3
    except ImportError:
        logging.error("pyttsx3 não instalado. Instale com: pip install pyttsx3")
        return False

    logging.warning("Usando fallback TTS local (pyttsx3) - qualidade inferior")

    try:
        engine = pyttsx3.init()

        # Tenta configurar voz em português
        vozes = engine.getProperty('voices')
        for voz in vozes:
            if 'portuguese' in voz.name.lower() or 'brazil' in voz.name.lower():
                engine.setProperty('voice', voz.id)
                break

        # Configura taxa e volume
        engine.setProperty('rate', 150)  # Velocidade
        engine.setProperty('volume', 1.0)

        # Salva áudio
        engine.save_to_file(texto, str(arquivo_saida))
        engine.runAndWait()

        return arquivo_saida.exists()

    except Exception as e:
        logging.error(f"Erro no fallback TTS local: {e}")
        return False


# ==================== PROCESSAMENTO DE UM CAPÍTULO ====================

def processar_capitulo(
    numero: int,
    titulo: str,
    texto: str,
    pasta_saida: Path,
    nome_livro: str,
    voz: str = VOZ_PADRAO,
    usar_fallback: bool = True
) -> Optional[Path]:
    """
    Processa um capítulo completo (texto → áudio)

    Args:
        numero: Número do capítulo
        titulo: Título do capítulo
        texto: Texto do capítulo
        pasta_saida: Pasta onde salvar áudio
        nome_livro: Nome do livro (para gerar nome do arquivo)
        voz: Voz a usar
        usar_fallback: Se True, usa fallback local se Edge-TTS falhar

    Returns:
        Path do arquivo de áudio gerado, ou None se falhou
    """
    # Gera nome do arquivo
    # Ex: "Sapiens - Cap 01 - A Revolução Cognitiva.mp3"
    nome_arquivo = f"{nome_livro} - Cap {numero:02d} - {normalizar_nome_arquivo(titulo)}.mp3"
    arquivo_saida = pasta_saida / nome_arquivo

    # Se já existe, pula
    if arquivo_saida.exists():
        logging.info(f"Capítulo {numero} já existe: {arquivo_saida.name}")
        return arquivo_saida

    logging.info(f"Convertendo capítulo {numero}: {titulo} ({len(texto.split())} palavras)")

    # Tenta Edge-TTS
    sucesso = converter_texto_para_audio(texto, arquivo_saida, voz)

    # Fallback local desativado (pyttsx3 fala em voz alta pelo alto-falante no Windows)
    # Se Edge-TTS falhar, o capitulo sera marcado como falha e pode ser reprocessado depois
    # if not sucesso and usar_fallback:
    #     sucesso = converter_com_fallback_local(texto, arquivo_saida)

    if sucesso:
        tamanho_mb = arquivo_saida.stat().st_size / (1024 * 1024)
        logging.info(f"✅ Capítulo {numero} concluído ({tamanho_mb:.1f} MB)")
        return arquivo_saida
    else:
        logging.error(f"❌ Falha ao processar capítulo {numero}")
        return None


# ==================== PROCESSAMENTO PARALELO ====================

def processar_capitulos_paralelo(
    capitulos: List[Tuple[int, str, str]],
    pasta_saida: Path,
    nome_livro: str,
    voz: str = VOZ_PADRAO,
    num_threads: int = NUM_THREADS_TTS,
    usar_fallback: bool = True,
    progress_callback=None
) -> List[Path]:
    """
    Processa múltiplos capítulos em paralelo

    Args:
        capitulos: Lista de tuplas (numero, titulo, texto)
        pasta_saida: Pasta onde salvar áudios
        nome_livro: Nome do livro
        voz: Voz a usar
        num_threads: Número de threads paralelas
        usar_fallback: Se True, usa fallback local em caso de falha

    Returns:
        Lista de Paths dos arquivos gerados (None para falhas)
    """
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    total_capitulos = len(capitulos)
    arquivos_gerados = [None] * total_capitulos

    logging.info(f"Processando {total_capitulos} capítulos em paralelo ({num_threads} threads)")

    # Estimador de tempo
    estimador = EstimadorTempo(total_capitulos)

    # Barra de progresso
    with criar_progress_bar(total_capitulos, "Convertendo TTS") as pbar:

        # ThreadPoolExecutor para processamento paralelo
        with ThreadPoolExecutor(max_workers=num_threads) as executor:

            # Submete todas as tarefas
            futures = {}
            for numero, titulo, texto in capitulos:
                future = executor.submit(
                    processar_capitulo,
                    numero, titulo, texto, pasta_saida, nome_livro, voz, usar_fallback
                )
                futures[future] = numero - 1  # Índice na lista (0-based)

            # Processa resultados conforme completam
            for future in as_completed(futures):
                indice = futures[future]
                numero_cap = indice + 1

                try:
                    resultado = future.result(timeout=TTS_TIMEOUT)
                    arquivos_gerados[indice] = resultado

                    if resultado:
                        estimador.atualizar()
                        pbar.set_description(
                            f"Convertendo TTS (Cap {numero_cap}/{total_capitulos}) - {estimador.tempo_restante()}"
                        )
                    else:
                        pbar.set_description(f"ERRO no capítulo {numero_cap}")

                except Exception as e:
                    logging.error(f"Exceção ao processar capítulo {numero_cap}: {e}")
                    arquivos_gerados[indice] = None

                pbar.update(1)
                concluidos = sum(1 for a in arquivos_gerados if a is not None)
                if progress_callback:
                    progress_callback(concluidos, total_capitulos)

    # Verifica quantos foram bem-sucedidos
    sucesso = sum(1 for a in arquivos_gerados if a is not None)
    falhas = total_capitulos - sucesso

    logging.info(f"Conversão concluída: {sucesso}/{total_capitulos} capítulos (falhas: {falhas})")

    if falhas > 0:
        logging.warning(f"⚠️  {falhas} capítulos falharam na conversão")
        capitulos_falhados = [i+1 for i, a in enumerate(arquivos_gerados) if a is None]
        logging.warning(f"   Capítulos com falha: {capitulos_falhados}")

    return arquivos_gerados


# ==================== NORMALIZAÇÃO DE ÁUDIO ====================

def normalizar_volume_audio(arquivo: Path) -> bool:
    """
    Normaliza o volume de um arquivo de áudio usando ffmpeg

    Args:
        arquivo: Path do arquivo de áudio

    Returns:
        True se sucesso
    """
    try:
        import subprocess

        # Verifica se ffmpeg está disponível
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)

    except (ImportError, subprocess.CalledProcessError, FileNotFoundError):
        logging.warning("ffmpeg não encontrado. Pule normalização de volume.")
        return False

    try:
        import subprocess

        # Arquivo temporário
        arquivo_temp = arquivo.parent / f"{arquivo.stem}_temp.mp3"

        # Comando ffmpeg para normalização
        # loudnorm filter aplica normalização de volume
        comando = [
            'ffmpeg',
            '-i', str(arquivo),
            '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
            '-ar', str(AUDIO_CONFIG['sample_rate']),
            '-ac', str(AUDIO_CONFIG['channels']),
            '-b:a', AUDIO_CONFIG['bitrate'],
            '-y',  # Sobrescreve se existir
            str(arquivo_temp)
        ]

        # Executa
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos
        )

        if resultado.returncode == 0 and arquivo_temp.exists():
            # Substitui arquivo original
            arquivo.unlink()
            arquivo_temp.rename(arquivo)
            return True
        else:
            logging.error(f"Erro ffmpeg: {resultado.stderr}")
            return False

    except Exception as e:
        logging.error(f"Erro ao normalizar áudio: {e}")
        return False


def normalizar_volume_lote(arquivos: List[Path]) -> int:
    """
    Normaliza volume de múltiplos arquivos

    Args:
        arquivos: Lista de arquivos de áudio

    Returns:
        Número de arquivos normalizados com sucesso
    """
    if not AUDIO_CONFIG.get('normalize', False):
        logging.info("Normalização de volume desabilitada (config)")
        return 0

    logging.info(f"Normalizando volume de {len(arquivos)} arquivos...")

    sucesso = 0
    for arquivo in arquivos:
        if arquivo and normalizar_volume_audio(arquivo):
            sucesso += 1

    logging.info(f"✅ {sucesso}/{len(arquivos)} arquivos normalizados")
    return sucesso


# ==================== VALIDAÇÃO DE ÁUDIO ====================

def validar_audio(arquivo: Path, min_tamanho_kb: int = 10) -> bool:
    """
    Valida se arquivo de áudio foi gerado corretamente

    Args:
        arquivo: Path do arquivo
        min_tamanho_kb: Tamanho mínimo em KB

    Returns:
        True se válido
    """
    if not arquivo.exists():
        return False

    tamanho_kb = arquivo.stat().st_size / 1024

    if tamanho_kb < min_tamanho_kb:
        logging.warning(f"Arquivo de áudio muito pequeno: {arquivo.name} ({tamanho_kb:.1f} KB)")
        return False

    return True


# ==================== CÁLCULO DE DURAÇÃO ====================

def estimar_duracao_audio(num_palavras: int, palavras_por_minuto: int = 150) -> str:
    """
    Estima duração do áudio baseado no número de palavras

    Args:
        num_palavras: Número de palavras no texto
        palavras_por_minuto: Velocidade de leitura (padrão: 150)

    Returns:
        String formatada (ex: "2h 30min")
    """
    minutos = num_palavras / palavras_por_minuto
    segundos = minutos * 60

    from utils import formatar_tempo
    return formatar_tempo(segundos)


def obter_duracao_real_audio(arquivo: Path) -> Optional[float]:
    """
    Obtém duração real de um arquivo de áudio

    Requer ffprobe (parte do ffmpeg)

    Args:
        arquivo: Path do arquivo de áudio

    Returns:
        Duração em segundos, ou None se falhou
    """
    try:
        import subprocess
        import json

        comando = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            str(arquivo)
        ]

        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=10)

        if resultado.returncode == 0:
            dados = json.loads(resultado.stdout)
            duracao = float(dados['format']['duration'])
            return duracao

    except Exception as e:
        logging.debug(f"Não foi possível obter duração de {arquivo.name}: {e}")

    return None
