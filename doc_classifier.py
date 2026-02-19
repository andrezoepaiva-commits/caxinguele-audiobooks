"""
Classificador inteligente de tipo de documento
3 camadas: extensão → conteúdo (palavras-chave) → fallback (usuário confirma)

Tipos detectados:
  LIVRO, ARTIGO_CIENTIFICO, EMAIL, DOCUMENTO_LEGAL,
  MATERIA_JORNAL, RELATORIO, ARTIGO_NOTICIA, OUTRO
"""

import logging
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


# ==================== TIPOS DE DOCUMENTO ====================

class TipoDocumento:
    LIVRO = "LIVRO"
    ARTIGO_CIENTIFICO = "ARTIGO_CIENTIFICO"
    EMAIL = "EMAIL"
    DOCUMENTO_LEGAL = "DOCUMENTO_LEGAL"
    MATERIA_JORNAL = "MATERIA_JORNAL"
    ARTIGO_NOTICIA = "ARTIGO_NOTICIA"
    RELATORIO = "RELATORIO"
    OUTRO = "OUTRO"


# Ícones para cada tipo (usados na GUI e Alexa)
ICONES_TIPO = {
    TipoDocumento.LIVRO: "📚",
    TipoDocumento.ARTIGO_CIENTIFICO: "🔬",
    TipoDocumento.EMAIL: "📧",
    TipoDocumento.DOCUMENTO_LEGAL: "⚖️",
    TipoDocumento.MATERIA_JORNAL: "📰",
    TipoDocumento.ARTIGO_NOTICIA: "📰",
    TipoDocumento.RELATORIO: "📊",
    TipoDocumento.OUTRO: "📄",
}

# Nomes amigáveis para exibição
NOMES_TIPO = {
    TipoDocumento.LIVRO: "Livro",
    TipoDocumento.ARTIGO_CIENTIFICO: "Artigo Científico",
    TipoDocumento.EMAIL: "Email",
    TipoDocumento.DOCUMENTO_LEGAL: "Documento Legal",
    TipoDocumento.MATERIA_JORNAL: "Matéria de Jornal",
    TipoDocumento.ARTIGO_NOTICIA: "Artigo/Notícia",
    TipoDocumento.RELATORIO: "Relatório",
    TipoDocumento.OUTRO: "Documento",
}

# Pasta no Google Drive para cada tipo
PASTA_TIPO = {
    TipoDocumento.LIVRO: "Livros",
    TipoDocumento.ARTIGO_CIENTIFICO: "Artigos e Noticias",
    TipoDocumento.EMAIL: "Emails",
    TipoDocumento.DOCUMENTO_LEGAL: "Documentos",
    TipoDocumento.MATERIA_JORNAL: "Artigos e Noticias",
    TipoDocumento.ARTIGO_NOTICIA: "Artigos e Noticias",
    TipoDocumento.RELATORIO: "Documentos",
    TipoDocumento.OUTRO: "Documentos",
}


@dataclass
class ClassificacaoDocumento:
    """Resultado da classificação"""
    tipo: str
    confianca: float  # 0.0 a 1.0
    icone: str
    nome: str
    pasta_drive: str
    metodo: str  # "extensao", "conteudo", "fallback"

    def __repr__(self):
        return f"{self.icone} {self.nome} (confiança: {self.confianca:.0%}, método: {self.metodo})"


# ==================== CLASSIFICAÇÃO PRINCIPAL ====================

def classificar_documento(caminho: Path, texto: str = "", num_paginas: int = 0) -> ClassificacaoDocumento:
    """
    Classifica o tipo do documento em 3 camadas:
      1. Por extensão do arquivo
      2. Por análise de conteúdo (palavras-chave)
      3. Fallback (retorna OUTRO, GUI pode pedir confirmação)

    Args:
        caminho: Path do arquivo
        texto: Texto extraído (opcional, para análise de conteúdo)
        num_paginas: Número de páginas (opcional, ajuda na classificação)

    Returns:
        ClassificacaoDocumento com tipo, confiança e metadata
    """
    caminho = Path(caminho)
    extensao = caminho.suffix.lower()

    # ─── CAMADA 1: Por extensão (alta confiança para formatos específicos) ───
    resultado_extensao = _classificar_por_extensao(extensao)
    if resultado_extensao and resultado_extensao.confianca >= 0.9:
        logging.info(f"Classificado por extensão: {resultado_extensao}")
        return resultado_extensao

    # ─── CAMADA 2: Por conteúdo (análise de palavras-chave) ───
    if texto:
        resultado_conteudo = _classificar_por_conteudo(texto, num_paginas)
        if resultado_conteudo and resultado_conteudo.confianca >= 0.5:
            logging.info(f"Classificado por conteúdo: {resultado_conteudo}")
            return resultado_conteudo

    # Se extensão deu resultado com confiança menor, usa ela
    if resultado_extensao:
        logging.info(f"Classificado por extensão (confiança menor): {resultado_extensao}")
        return resultado_extensao

    # ─── CAMADA 3: Fallback ───
    logging.info("Classificação incerta — fallback para OUTRO")
    return _criar_classificacao(TipoDocumento.OUTRO, 0.3, "fallback")


# ==================== CAMADA 1: POR EXTENSÃO ====================

def _classificar_por_extensao(extensao: str) -> Optional[ClassificacaoDocumento]:
    """Classifica baseado apenas na extensão do arquivo"""

    mapa = {
        # Extensões com tipo muito provável
        '.epub': (TipoDocumento.LIVRO, 0.95),
        '.mobi': (TipoDocumento.LIVRO, 0.95),
        '.eml': (TipoDocumento.EMAIL, 0.95),
        '.msg': (TipoDocumento.EMAIL, 0.95),
        # Extensões ambíguas (confiança menor)
        '.pdf': (TipoDocumento.OUTRO, 0.3),
        '.docx': (TipoDocumento.OUTRO, 0.3),
        '.rtf': (TipoDocumento.OUTRO, 0.3),
        '.odt': (TipoDocumento.OUTRO, 0.3),
        '.txt': (TipoDocumento.OUTRO, 0.3),
        '.md': (TipoDocumento.ARTIGO_NOTICIA, 0.5),
        '.html': (TipoDocumento.ARTIGO_NOTICIA, 0.6),
        '.htm': (TipoDocumento.ARTIGO_NOTICIA, 0.6),
        # Imagens (OCR — tipo incerto)
        '.jpg': (TipoDocumento.OUTRO, 0.2),
        '.jpeg': (TipoDocumento.OUTRO, 0.2),
        '.png': (TipoDocumento.OUTRO, 0.2),
        '.tiff': (TipoDocumento.OUTRO, 0.2),
        '.tif': (TipoDocumento.OUTRO, 0.2),
        '.bmp': (TipoDocumento.OUTRO, 0.2),
        '.webp': (TipoDocumento.OUTRO, 0.2),
    }

    if extensao in mapa:
        tipo, confianca = mapa[extensao]
        return _criar_classificacao(tipo, confianca, "extensao")

    return None


# ==================== CAMADA 2: POR CONTEÚDO ====================

# Palavras-chave por tipo (quanto mais encontrar, maior a confiança)
PALAVRAS_CHAVE = {
    TipoDocumento.ARTIGO_CIENTIFICO: [
        "abstract", "methodology", "references", "doi:",
        "introduction", "conclusion", "et al.",
        "resumo", "metodologia", "referências", "introdução",
        "resultados e discussão", "revisão bibliográfica",
        "palavras-chave", "keywords",
    ],
    TipoDocumento.LIVRO: [
        "capítulo", "capítulo 1", "capítulo 2", "chapter",
        "epílogo", "prólogo", "prefácio", "posfácio",
        "índice", "sumário", "agradecimentos",
        "parte i", "parte ii", "parte 1", "parte 2",
    ],
    TipoDocumento.EMAIL: [
        "de:", "para:", "assunto:", "cc:", "cco:",
        "from:", "to:", "subject:", "reply-to:",
        "encaminhado", "forwarded", "re:", "fw:",
    ],
    TipoDocumento.DOCUMENTO_LEGAL: [
        "contrato", "cláusula", "partes:", "artigo",
        "parágrafo", "inciso", "alínea", "lei nº",
        "decreto", "portaria", "resolução",
        "testemunhas", "foro", "assinaturas",
        "contratante", "contratado",
    ],
    TipoDocumento.MATERIA_JORNAL: [
        "redação:", "correspondente:", "reportagem",
        "entrevista", "edição", "publicado em",
        "atualizado em", "fonte:", "agência",
        "segundo fontes", "apuração",
    ],
    TipoDocumento.RELATORIO: [
        "relatório", "resultados:", "conclusão:",
        "recomendações", "diagnóstico", "análise",
        "indicadores", "métricas", "período:",
        "trimestre", "semestre", "quadro",
    ],
}


def _normalizar_para_busca(texto: str) -> str:
    """Remove acentos e normaliza para comparação de palavras-chave"""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


def _classificar_por_conteudo(texto: str, num_paginas: int = 0) -> Optional[ClassificacaoDocumento]:
    """Classifica baseado em palavras-chave no conteúdo"""
    texto_lower = texto.lower()
    texto_norm = _normalizar_para_busca(texto)  # Versão sem acentos para comparação

    # Conta matches para cada tipo (busca com e sem acento)
    scores = {}
    for tipo, palavras in PALAVRAS_CHAVE.items():
        matches = 0
        for palavra in palavras:
            p_lower = palavra.lower()
            p_norm = _normalizar_para_busca(palavra)
            # Verifica tanto com acento quanto sem
            if p_lower in texto_lower or (p_norm != p_lower and p_norm in texto_norm):
                matches += 1
        total = len(palavras)
        scores[tipo] = matches / total if total > 0 else 0

    # Pega o tipo com maior score
    melhor_tipo = max(scores, key=scores.get)
    melhor_score = scores[melhor_tipo]

    # Ajustes por número de páginas
    if num_paginas > 30 and melhor_tipo != TipoDocumento.ARTIGO_CIENTIFICO:
        # Documentos muito longos são provavelmente livros
        if scores[TipoDocumento.LIVRO] > 0.1:
            melhor_tipo = TipoDocumento.LIVRO
            melhor_score = max(melhor_score, 0.6)

    if melhor_score < 0.15:
        return None  # Não confiante o suficiente

    # Converte score para confiança (0.5 a 0.95)
    confianca = min(0.95, 0.5 + melhor_score * 0.5)

    return _criar_classificacao(melhor_tipo, confianca, "conteudo")


# ==================== HELPERS ====================

def _criar_classificacao(tipo: str, confianca: float, metodo: str) -> ClassificacaoDocumento:
    """Cria objeto ClassificacaoDocumento"""
    return ClassificacaoDocumento(
        tipo=tipo,
        confianca=confianca,
        icone=ICONES_TIPO.get(tipo, "📄"),
        nome=NOMES_TIPO.get(tipo, "Documento"),
        pasta_drive=PASTA_TIPO.get(tipo, "Documentos"),
        metodo=metodo,
    )


def obter_opcoes_tipo_gui() -> list:
    """
    Retorna opções de tipo para o seletor da GUI (fallback camada 3).
    Formato: [(icone + nome, tipo_enum), ...]
    """
    return [
        (f"{ICONES_TIPO[TipoDocumento.LIVRO]} Livro", TipoDocumento.LIVRO),
        (f"{ICONES_TIPO[TipoDocumento.ARTIGO_NOTICIA]} Artigo/Notícia", TipoDocumento.ARTIGO_NOTICIA),
        (f"{ICONES_TIPO[TipoDocumento.EMAIL]} Email", TipoDocumento.EMAIL),
        (f"{ICONES_TIPO[TipoDocumento.DOCUMENTO_LEGAL]} Documento Legal", TipoDocumento.DOCUMENTO_LEGAL),
        (f"{ICONES_TIPO[TipoDocumento.RELATORIO]} Relatório", TipoDocumento.RELATORIO),
        (f"{ICONES_TIPO[TipoDocumento.OUTRO]} Outro", TipoDocumento.OUTRO),
    ]
