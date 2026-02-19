"""
Módulo para processamento de arquivos PDF
Extrai texto, TOC (Table of Contents), detecta necessidade de OCR
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import fitz  # PyMuPDF

from config import PDF_CONFIG, MAX_PDF_SIZE_MB, MIN_PAGES
from utils import validar_pdf, limpar_texto_para_tts, normalizar_nome_arquivo


# ==================== ESTRUTURA DE DADOS ====================

class LivroProcessado:
    """Representa um livro processado"""

    def __init__(self, caminho: Path):
        self.caminho = caminho
        self.titulo = ""
        self.autor = ""
        self.num_paginas = 0
        self.tamanho_mb = 0
        self.capitulos: List[Capitulo] = []
        self.metadata: Dict = {}
        self.precisou_ocr = False

    def __repr__(self):
        return f"<Livro: {self.titulo} - {self.num_paginas} páginas, {len(self.capitulos)} capítulos>"


class Capitulo:
    """Representa um capítulo do livro"""

    def __init__(self, numero: int, titulo: str, texto: str, pagina_inicio: int):
        self.numero = numero
        self.titulo = titulo
        self.texto = texto
        self.pagina_inicio = pagina_inicio
        self.palavras = len(texto.split())

    def __repr__(self):
        return f"<Capítulo {self.numero}: {self.titulo} ({self.palavras} palavras)>"


# ==================== EXTRAÇÃO DE METADATA ====================

def extrair_metadata(pdf_doc: fitz.Document) -> Dict:
    """
    Extrai metadata do PDF (título, autor, etc.)

    Args:
        pdf_doc: Documento PyMuPDF

    Returns:
        Dicionário com metadata
    """
    metadata = pdf_doc.metadata or {}

    return {
        'titulo': metadata.get('title', 'Título Desconhecido'),
        'autor': metadata.get('author', 'Autor Desconhecido'),
        'assunto': metadata.get('subject', ''),
        'criador': metadata.get('creator', ''),
        'produtor': metadata.get('producer', ''),
        'data_criacao': metadata.get('creationDate', ''),
    }


# ==================== DETECÇÃO DE OCR ====================

def precisa_ocr(pdf_doc: fitz.Document, amostras: int = 5) -> bool:
    """
    Detecta se o PDF precisa de OCR (é escaneado)

    Verifica se as primeiras páginas têm texto extraível.
    Se não tiver, provavelmente é imagem escaneada.

    Args:
        pdf_doc: Documento PyMuPDF
        amostras: Número de páginas para verificar

    Returns:
        True se precisa OCR, False caso contrário
    """
    num_paginas_verificar = min(amostras, len(pdf_doc))
    texto_total = ""

    for num_pagina in range(num_paginas_verificar):
        pagina = pdf_doc[num_pagina]
        texto = pagina.get_text()
        texto_total += texto

    # Remove espaços em branco
    texto_limpo = texto_total.strip()

    # Se extraiu menos de 100 caracteres nas primeiras páginas, provavelmente precisa OCR
    if len(texto_limpo) < 100:
        logging.info(f"Detectado PDF escaneado (apenas {len(texto_limpo)} caracteres extraídos)")
        return True

    logging.info("PDF tem texto extraível (não precisa OCR)")
    return False


def aplicar_ocr(caminho_pdf: Path) -> Path:
    """
    Aplica OCR no PDF usando ocrmypdf

    Args:
        caminho_pdf: Path do PDF original

    Returns:
        Path do PDF com OCR aplicado
    """
    try:
        import ocrmypdf
    except ImportError:
        logging.error("ocrmypdf não instalado. Instale com: pip install ocrmypdf")
        raise

    # Cria nome do arquivo de saída
    caminho_ocr = caminho_pdf.parent / f"{caminho_pdf.stem}_ocr.pdf"

    logging.info(f"Aplicando OCR no PDF (isso pode demorar)...")

    # Configurações OCR
    idioma = PDF_CONFIG['ocr_language']  # 'por' para português

    try:
        ocrmypdf.ocr(
            caminho_pdf,
            caminho_ocr,
            language=idioma,
            skip_text=True,  # Pula páginas que já têm texto
            force_ocr=False,
            optimize=1,
            progress_bar=True
        )

        logging.info(f"OCR concluído! PDF salvo em: {caminho_ocr}")
        return caminho_ocr

    except Exception as e:
        logging.error(f"Erro ao aplicar OCR: {e}")
        raise


# ==================== EXTRAÇÃO DE TOC (TABLE OF CONTENTS) ====================

def extrair_toc_nativo(pdf_doc: fitz.Document) -> List[Dict]:
    """
    Extrai Table of Contents nativo do PDF

    Args:
        pdf_doc: Documento PyMuPDF

    Returns:
        Lista de capítulos [{'nivel': 1, 'titulo': '...', 'pagina': 10}, ...]
    """
    toc = pdf_doc.get_toc()

    if not toc:
        logging.warning("PDF não tem TOC nativo")
        return []

    # Converte para formato mais amigável
    capitulos = []
    for item in toc:
        nivel, titulo, pagina = item
        capitulos.append({
            'nivel': nivel,
            'titulo': titulo.strip(),
            'pagina': pagina - 1  # PyMuPDF usa 0-indexed
        })

    logging.info(f"TOC nativo extraído: {len(capitulos)} entradas")
    return capitulos


def detectar_capitulos_por_padroes(pdf_doc: fitz.Document) -> List[Dict]:
    """
    Detecta capítulos por padrões comuns no texto

    Quando o PDF não tem TOC nativo, tenta detectar capítulos
    procurando por padrões como "Capítulo 1", "CAPÍTULO I", etc.

    Args:
        pdf_doc: Documento PyMuPDF

    Returns:
        Lista de capítulos detectados
    """
    # Padrões comuns para capítulos
    padroes = [
        r'^Capítulo\s+(\d+|[IVX]+)',  # Capítulo 1, Capítulo I
        r'^CAPÍTULO\s+(\d+|[IVX]+)',  # CAPÍTULO 1
        r'^Cap\.\s+(\d+)',            # Cap. 1
        r'^Chapter\s+(\d+|[IVX]+)',   # Chapter 1 (inglês)
        r'^(\d+)\.\s+[A-Z]',          # 1. Título Capitalizado
    ]

    capitulos = []
    num_capitulo = 1

    for num_pagina in range(len(pdf_doc)):
        pagina = pdf_doc[num_pagina]
        texto = pagina.get_text()

        # Verifica primeiras linhas da página
        linhas = texto.split('\n')[:5]  # Primeiras 5 linhas

        for linha in linhas:
            linha = linha.strip()
            for padrao in padroes:
                if re.match(padrao, linha, re.IGNORECASE):
                    capitulos.append({
                        'nivel': 1,
                        'titulo': linha,
                        'pagina': num_pagina
                    })
                    num_capitulo += 1
                    break

    if capitulos:
        logging.info(f"Detectados {len(capitulos)} capítulos por padrões de texto")
    else:
        logging.warning("Não foi possível detectar capítulos automaticamente")

    return capitulos


def criar_capitulos_artificiais(pdf_doc: fitz.Document, palavras_por_capitulo: int = 3000) -> List[Dict]:
    """
    Cria capítulos artificiais dividindo o livro em partes iguais

    Usado quando não conseguimos detectar capítulos de nenhuma forma.

    Args:
        pdf_doc: Documento PyMuPDF
        palavras_por_capitulo: Aproximadamente quantas palavras por capítulo

    Returns:
        Lista de capítulos artificiais
    """
    num_paginas = len(pdf_doc)

    # Estima páginas por capítulo (assumindo ~300 palavras por página)
    palavras_por_pagina = 300
    paginas_por_capitulo = int(palavras_por_capitulo / palavras_por_pagina)

    # Garante pelo menos 10 páginas por capítulo
    paginas_por_capitulo = max(10, paginas_por_capitulo)

    capitulos = []
    num_capitulo = 1

    for pagina_inicio in range(0, num_paginas, paginas_por_capitulo):
        capitulos.append({
            'nivel': 1,
            'titulo': f"Parte {num_capitulo}",
            'pagina': pagina_inicio
        })
        num_capitulo += 1

    logging.info(f"Criados {len(capitulos)} capítulos artificiais (~{paginas_por_capitulo} páginas cada)")
    return capitulos


# ==================== EXTRAÇÃO DE TEXTO ====================

def extrair_texto_por_paginas(pdf_doc: fitz.Document, pagina_inicio: int, pagina_fim: int) -> str:
    """
    Extrai texto de um intervalo de páginas

    Args:
        pdf_doc: Documento PyMuPDF
        pagina_inicio: Página inicial (0-indexed)
        pagina_fim: Página final (0-indexed, exclusiva)

    Returns:
        Texto concatenado
    """
    texto_completo = []

    for num_pagina in range(pagina_inicio, min(pagina_fim, len(pdf_doc))):
        pagina = pdf_doc[num_pagina]
        texto = pagina.get_text()
        texto_completo.append(texto)

    return '\n\n'.join(texto_completo)


def limpar_texto_pdf(texto: str) -> str:
    """
    Limpa texto extraído do PDF

    Remove elementos comuns de PDFs que atrapalham leitura:
    - Números de página
    - Headers/footers repetitivos
    - Hífens de quebra de linha

    Args:
        texto: Texto original

    Returns:
        Texto limpo
    """
    # Remove hífens de quebra de linha
    # "pala-\nvra" -> "palavra"
    texto = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', texto)

    # Remove números de página isolados
    # Remove linhas que são apenas números
    linhas = texto.split('\n')
    linhas_limpas = []

    for linha in linhas:
        # Pula linhas que são apenas números (possíveis números de página)
        if re.match(r'^\s*\d+\s*$', linha):
            continue
        linhas_limpas.append(linha)

    texto = '\n'.join(linhas_limpas)

    # Usa a limpeza geral de texto para TTS
    texto = limpar_texto_para_tts(texto)

    return texto


# ==================== FUNÇÃO PRINCIPAL ====================

def processar_pdf(caminho_pdf: Path) -> LivroProcessado:
    """
    Processa um PDF completo e extrai estrutura

    Este é o ponto de entrada principal deste módulo.

    Workflow:
    1. Valida PDF
    2. Extrai metadata
    3. Detecta se precisa OCR
    4. Extrai/detecta capítulos
    5. Extrai texto de cada capítulo
    6. Limpa texto

    Args:
        caminho_pdf: Path do arquivo PDF

    Returns:
        Objeto LivroProcessado com toda estrutura
    """
    caminho_pdf = Path(caminho_pdf)
    logging.info(f"Processando PDF: {caminho_pdf.name}")

    # 1. Validação
    valido, mensagem = validar_pdf(caminho_pdf)
    if not valido:
        raise ValueError(mensagem)

    tamanho_mb = caminho_pdf.stat().st_size / (1024 * 1024)
    if tamanho_mb > MAX_PDF_SIZE_MB:
        raise ValueError(f"PDF muito grande ({tamanho_mb:.1f} MB). Máximo: {MAX_PDF_SIZE_MB} MB")

    logging.info(mensagem)

    # 2. Abre PDF
    try:
        pdf_doc = fitz.open(caminho_pdf)
    except Exception as e:
        raise ValueError(f"Erro ao abrir PDF: {e}")

    num_paginas = len(pdf_doc)
    if num_paginas < MIN_PAGES:
        raise ValueError(f"PDF muito curto ({num_paginas} páginas). Mínimo: {MIN_PAGES}")

    logging.info(f"PDF tem {num_paginas} páginas")

    # 3. Extrai metadata
    metadata = extrair_metadata(pdf_doc)
    logging.info(f"Título: {metadata['titulo']}")
    logging.info(f"Autor: {metadata['autor']}")

    # 4. Verifica necessidade de OCR
    precisou_ocr = False
    if PDF_CONFIG['auto_ocr'] and precisa_ocr(pdf_doc):
        logging.info("Aplicando OCR automático...")
        caminho_pdf_ocr = aplicar_ocr(caminho_pdf)

        # Reabre PDF com OCR
        pdf_doc.close()
        pdf_doc = fitz.open(caminho_pdf_ocr)
        precisou_ocr = True

    # 5. Extrai/detecta capítulos
    toc_capitulos = extrair_toc_nativo(pdf_doc)

    if not toc_capitulos:
        # Tenta detectar por padrões
        toc_capitulos = detectar_capitulos_por_padroes(pdf_doc)

    if not toc_capitulos:
        # Cria capítulos artificiais
        toc_capitulos = criar_capitulos_artificiais(
            pdf_doc,
            palavras_por_capitulo=PDF_CONFIG['max_chunk_words']
        )

    # Filtra apenas capítulos de nível 1 (principais)
    toc_nivel1 = [cap for cap in toc_capitulos if cap['nivel'] == 1]
    logging.info(f"Total de capítulos a processar: {len(toc_nivel1)}")

    # 6. Extrai texto de cada capítulo
    capitulos_processados = []

    for i, cap_info in enumerate(toc_nivel1):
        num_capitulo = i + 1
        titulo = cap_info['titulo']
        pagina_inicio = cap_info['pagina']

        # Determina página final (início do próximo capítulo ou fim do livro)
        if i + 1 < len(toc_nivel1):
            pagina_fim = toc_nivel1[i + 1]['pagina']
        else:
            pagina_fim = num_paginas

        # Extrai texto
        logging.info(f"Extraindo capítulo {num_capitulo}/{len(toc_nivel1)}: {titulo}")
        texto = extrair_texto_por_paginas(pdf_doc, pagina_inicio, pagina_fim)

        # Limpa texto
        if PDF_CONFIG['auto_cleanup']:
            texto = limpar_texto_pdf(texto)

        # Cria objeto Capitulo
        capitulo = Capitulo(
            numero=num_capitulo,
            titulo=titulo,
            texto=texto,
            pagina_inicio=pagina_inicio
        )

        capitulos_processados.append(capitulo)
        logging.info(f"  → {capitulo.palavras} palavras extraídas")

    # 7. Cria objeto LivroProcessado
    livro = LivroProcessado(caminho_pdf)
    livro.titulo = metadata['titulo']
    livro.autor = metadata['autor']
    livro.num_paginas = num_paginas
    livro.tamanho_mb = tamanho_mb
    livro.capitulos = capitulos_processados
    livro.metadata = metadata
    livro.precisou_ocr = precisou_ocr

    # Fecha documento
    pdf_doc.close()

    # Log final
    total_palavras = sum(cap.palavras for cap in capitulos_processados)
    logging.info(f"✅ PDF processado com sucesso!")
    logging.info(f"   Total: {len(capitulos_processados)} capítulos, {total_palavras:,} palavras")

    return livro


# ==================== DIVISÃO EM CHUNKS ====================

def dividir_capitulo_em_chunks(capitulo: Capitulo, max_palavras: int = 3000) -> List[Tuple[str, str]]:
    """
    Divide um capítulo em chunks menores se necessário

    Útil para capítulos muito longos que podem causar timeout no TTS.

    Args:
        capitulo: Objeto Capitulo
        max_palavras: Máximo de palavras por chunk

    Returns:
        Lista de tuplas (titulo_chunk, texto_chunk)
    """
    if capitulo.palavras <= max_palavras:
        # Capítulo cabe em um único chunk
        return [(capitulo.titulo, capitulo.texto)]

    # Precisa dividir
    logging.info(f"Dividindo capítulo '{capitulo.titulo}' em chunks ({capitulo.palavras} palavras)")

    # Divide por parágrafos
    paragrafos = capitulo.texto.split('\n\n')
    chunks = []
    chunk_atual = []
    palavras_chunk_atual = 0

    for paragrafo in paragrafos:
        palavras_paragrafo = len(paragrafo.split())

        if palavras_chunk_atual + palavras_paragrafo > max_palavras and chunk_atual:
            # Salva chunk atual
            texto_chunk = '\n\n'.join(chunk_atual)
            titulo_chunk = f"{capitulo.titulo} - Parte {len(chunks) + 1}"
            chunks.append((titulo_chunk, texto_chunk))

            # Reset
            chunk_atual = [paragrafo]
            palavras_chunk_atual = palavras_paragrafo
        else:
            chunk_atual.append(paragrafo)
            palavras_chunk_atual += palavras_paragrafo

    # Adiciona último chunk
    if chunk_atual:
        texto_chunk = '\n\n'.join(chunk_atual)
        titulo_chunk = f"{capitulo.titulo} - Parte {len(chunks) + 1}"
        chunks.append((titulo_chunk, texto_chunk))

    logging.info(f"  → Dividido em {len(chunks)} chunks")
    return chunks
