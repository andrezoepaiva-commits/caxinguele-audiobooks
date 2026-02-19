"""
Alexa Custom Skill - Projeto Caxinguele
Lambda Function (AWS Lambda + Python 3.11)

Palavra de confirmacao: CAMBIO
Exemplo de uso:
  "Alexa, abre meus audiobooks"
  -> Alexa: "Ouvindo... pode falar, termine com cambio"
  -> Usuario: "quais documentos eu tenho... cambio"
  -> Alexa lista documentos disponíveis

Deploy:
  1. Compactar esta pasta em .zip
  2. Subir no AWS Lambda
  3. Configurar trigger: Alexa Skills Kit
  4. Copiar ARN do Lambda para o Alexa Developer Console
"""

import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==================== CONFIGURACOES ====================

# URL do feed RSS principal (GitHub Pages)
RSS_BASE_URL = "https://andrezoepaiva-commits.github.io/caxinguele-audiobooks"

# IDs dos feeds RSS por usuario (expandir com Amazon Household)
RSS_FEEDS = {
    "padrao": f"{RSS_BASE_URL}/index.json",  # indice de todos os livros
}

# Palavra de confirmacao de fim de fala
PALAVRA_CAMBIO = "cambio"


# ==================== HANDLERS PRINCIPAIS ====================

def lambda_handler(event, context):
    """Ponto de entrada da Lambda Function"""
    try:
        logger.info(f"Request type: {event.get('request', {}).get('type')}")
        logger.info(f"Full event: {json.dumps(event, default=str)}")

        request_type = event.get("request", {}).get("type", "")

        if request_type == "LaunchRequest":
            return handle_launch(event)
        elif request_type == "IntentRequest":
            return handle_intent(event)
        elif request_type == "SessionEndedRequest":
            return handle_session_ended(event)
        else:
            return build_response("Desculpe, nao entendi o pedido.")

    except Exception as e:
        logger.error(f"ERRO NA LAMBDA: {str(e)}", exc_info=True)
        # Retorna resposta de erro válida para Alexa (não deixa vazio)
        return build_response(
            "Desculpe, houve um erro ao processar sua solicitacao. Tente novamente.",
            should_end_session=True
        )


def handle_launch(event):
    """Abertura da skill: 'Alexa, abre meus audiobooks'"""
    texto = (
        "Biblioteca de audio pronta. "
        "O que deseja? "
        "Termine sempre com a palavra cambio. "
        "Por exemplo: quais documentos tenho, cambio."
    )
    return build_response(
        texto,
        should_end_session=False,
        reprompt="Pode falar seu pedido e terminar com cambio."
    )


def handle_intent(event):
    """Processa todos os intents da skill"""
    intent_name = event.get("request", {}).get("intent", {}).get("name", "")
    slots = event.get("request", {}).get("intent", {}).get("slots", {})

    logger.info(f"Intent: {intent_name}")

    handlers = {
        "ListarDocumentosIntent": handle_listar_documentos,
        "LerDocumentoIntent": handle_ler_documento,
        "FiltrarPorTipoIntent": handle_filtrar_por_tipo,
        "FavoritarIntent": handle_favoritar,
        "MostrarFavoritosIntent": handle_mostrar_favoritos,
        "DocumentoNovosIntent": handle_documentos_novos,
        "AMAZON.HelpIntent": handle_ajuda,
        "AMAZON.StopIntent": handle_stop,
        "AMAZON.CancelIntent": handle_stop,
        "AMAZON.NavigateHomeIntent": handle_stop,
    }

    handler_fn = handlers.get(intent_name)
    if handler_fn:
        return handler_fn(event, slots)

    return build_response(
        "Desculpe, nao entendi esse pedido. "
        "Tente dizer: quais documentos tenho, cambio.",
        should_end_session=False
    )


def handle_session_ended(event):
    """Sessao encerrada"""
    return {"version": "1.0", "response": {}}


# ==================== INTENTS ESPECIFICOS ====================

def handle_listar_documentos(event, slots):
    """'Quais documentos tenho... cambio'"""
    documentos = _buscar_todos_documentos()

    if not documentos:
        return build_response(
            "Sua biblioteca esta vazia. "
            "Peca para o Andre converter um documento para voce.",
            should_end_session=True
        )

    # Agrupa por tipo
    por_tipo = {}
    for doc in documentos:
        tipo = doc.get("categoria", "Documentos")
        if tipo not in por_tipo:
            por_tipo[tipo] = []
        por_tipo[tipo].append(doc)

    # Monta resposta de voz
    total = len(documentos)
    partes = [f"Voce tem {total} documento{'s' if total > 1 else ''}:"]

    for tipo, docs in por_tipo.items():
        qtd = len(docs)
        partes.append(f"{qtd} {tipo.lower()}")

    partes.append("O que deseja ouvir? Termine com cambio.")
    texto = ". ".join(partes)

    return build_response(texto, should_end_session=False,
                          reprompt="Diga o numero ou tipo do documento. Termine com cambio.")


def handle_ler_documento(event, slots):
    """'Le o documento numero dois... cambio'"""
    numero = _extrair_numero(slots, "numero")
    nome = _extrair_texto(slots, "nome_documento")

    documentos = _buscar_todos_documentos()

    if not documentos:
        return build_response(
            "Nao ha documentos disponiveis.",
            should_end_session=True
        )

    # Seleciona documento por numero ou nome
    doc = None
    if numero and 1 <= numero <= len(documentos):
        doc = documentos[numero - 1]
    elif nome:
        # Busca por nome aproximado
        nome_lower = nome.lower()
        for d in documentos:
            if nome_lower in d.get("titulo", "").lower():
                doc = d
                break

    if not doc:
        if numero:
            return build_response(
                f"Nao encontrei o documento numero {numero}. "
                f"Voce tem {len(documentos)} documentos. "
                "Qual numero deseja?",
                should_end_session=False
            )
        # Abre o mais recente
        doc = documentos[0]

    titulo = doc.get("titulo", "Documento sem titulo")
    url = doc.get("url_audio", "")

    if not url:
        return build_response(
            f"Encontrei {titulo} mas o audio nao esta disponivel.",
            should_end_session=True
        )

    # Retorna resposta com audio
    return build_audio_response(titulo, url)


def handle_filtrar_por_tipo(event, slots):
    """'Meus livros... cambio' / 'Artigos de hoje... cambio'"""
    tipo = _extrair_texto(slots, "tipo_documento")

    if not tipo:
        return build_response(
            "Que tipo de documento? Livros, artigos, emails ou documentos?",
            should_end_session=False
        )

    documentos = _buscar_todos_documentos()

    # Mapeia palavras do usuario para categorias
    mapa = {
        "livro": "Livros", "livros": "Livros",
        "artigo": "Artigos e Noticias", "artigos": "Artigos e Noticias",
        "noticia": "Artigos e Noticias", "noticias": "Artigos e Noticias",
        "email": "Emails", "emails": "Emails",
        "documento": "Documentos", "documentos": "Documentos",
    }

    categoria = mapa.get(tipo.lower().strip())
    if not categoria:
        return build_response(
            f"Nao reconheco o tipo {tipo}. "
            "Diga: livros, artigos, emails ou documentos.",
            should_end_session=False
        )

    filtrados = [d for d in documentos if d.get("categoria", "") == categoria]

    if not filtrados:
        return build_response(
            f"Nao ha {tipo} disponivel no momento.",
            should_end_session=True
        )

    titulos = [d.get("titulo", "Sem titulo") for d in filtrados[:5]]
    lista = ". ".join(f"Numero {i+1}: {t}" for i, t in enumerate(titulos))
    suffix = f"E mais {len(filtrados)-5} outros." if len(filtrados) > 5 else ""

    return build_response(
        f"Voce tem {len(filtrados)} {tipo}. {lista}. {suffix} "
        "Qual numero deseja ouvir? Termine com cambio.",
        should_end_session=False
    )


def handle_favoritar(event, slots):
    """'Favorite este... cambio'"""
    # Nota: favoritos requerem estado persistente (DynamoDB)
    return build_response(
        "Documento marcado como favorito. "
        "Para ouvir seus favoritos, diga: mostra meus favoritos, cambio.",
        should_end_session=False
    )


def handle_mostrar_favoritos(event, slots):
    """'Mostra meus favoritos... cambio'"""
    # TODO: integrar com DynamoDB para persistencia
    return build_response(
        "Voce ainda nao tem favoritos. "
        "Durante a leitura, diga: favorite este, cambio.",
        should_end_session=False
    )


def handle_documentos_novos(event, slots):
    """'Documentos novos / de hoje... cambio'"""
    documentos = _buscar_todos_documentos()
    hoje = datetime.now().strftime("%Y-%m-%d")

    novos = [d for d in documentos if d.get("data", "")[:10] == hoje]

    if not novos:
        return build_response(
            "Nao ha documentos novos hoje. "
            "Para ver todos, diga: quais documentos tenho, cambio.",
            should_end_session=False
        )

    titulos = [d.get("titulo", "Sem titulo") for d in novos[:3]]
    lista = ". ".join(f"Numero {i+1}: {t}" for i, t in enumerate(titulos))

    return build_response(
        f"Ha {len(novos)} documento{'s' if len(novos) > 1 else ''} novo hoje. {lista}. "
        "Qual deseja ouvir? Termine com cambio.",
        should_end_session=False
    )


def handle_ajuda(event, slots):
    """'Alexa, ajuda'"""
    return build_response(
        "Sua biblioteca de audio. Voce pode dizer: "
        "quais documentos tenho, cambio. "
        "Le o livro numero um, cambio. "
        "Meus artigos, cambio. "
        "Lembre-se: sempre termine com a palavra cambio. "
        "O que deseja?",
        should_end_session=False,
        reprompt="Diga seu pedido e termine com cambio."
    )


def handle_stop(event, slots):
    """Para e encerra a skill"""
    return build_response(
        "Ate logo! Sua biblioteca esta sempre disponivel.",
        should_end_session=True
    )


# ==================== HELPERS DE DADOS ====================

def _buscar_todos_documentos():
    """
    Busca lista de documentos do feed RSS do GitHub Pages.
    Retorna lista de dicts: {titulo, url_audio, categoria, data}
    """
    try:
        # Busca o indice JSON (gerado pelo pipeline)
        url_index = f"{RSS_BASE_URL}/indice.json"
        logger.info(f"Tentando buscar indice: {url_index}")
        with urllib.request.urlopen(url_index, timeout=10) as response:
            dados = json.loads(response.read().decode("utf-8"))
            documentos = dados.get("documentos", [])
            logger.info(f"Indice encontrado: {len(documentos)} documentos")
            return documentos
    except urllib.error.URLError as e:
        logger.warning(f"URLError ao buscar indice: {e}")
    except Exception as e:
        logger.warning(f"Erro ao buscar indice: {type(e).__name__}: {e}")

    # Fallback: tenta buscar diretamente o RSS principal
    try:
        url_rss = f"{RSS_BASE_URL}/feed.xml"
        logger.info(f"Tentando fallback RSS: {url_rss}")
        with urllib.request.urlopen(url_rss, timeout=10) as response:
            xml_content = response.read().decode("utf-8")
            documentos = _parsear_rss(xml_content)
            logger.info(f"RSS encontrado: {len(documentos)} documentos")
            return documentos
    except Exception as e:
        logger.error(f"Erro ao buscar RSS: {type(e).__name__}: {e}")
        logger.error("Retornando lista vazia (biblioteca vazia)")
        return []


def _parsear_rss(xml_content: str) -> list:
    """Parseia RSS XML e retorna lista de documentos"""
    documentos = []
    try:
        root = ET.fromstring(xml_content)
        channel = root.find("channel")
        if channel is None:
            return []

        categoria = channel.findtext("category", "Documentos")

        for item in channel.findall("item"):
            titulo = item.findtext("title", "Sem titulo")
            enclosure = item.find("enclosure")
            url_audio = enclosure.get("url", "") if enclosure is not None else ""
            pub_date = item.findtext("pubDate", "")

            if url_audio:
                documentos.append({
                    "titulo": titulo,
                    "url_audio": url_audio,
                    "categoria": categoria,
                    "data": pub_date,
                })
    except Exception as e:
        logger.error(f"Erro ao parsear RSS: {e}")

    return documentos


def _extrair_numero(slots: dict, nome: str) -> int:
    """Extrai numero de um slot"""
    try:
        valor = slots.get(nome, {}).get("value", "")
        if valor:
            return int(valor)
    except (ValueError, TypeError):
        pass
    return None


def _extrair_texto(slots: dict, nome: str) -> str:
    """Extrai texto de um slot"""
    try:
        return slots.get(nome, {}).get("value", "") or ""
    except Exception:
        return ""


# ==================== HELPERS DE RESPOSTA ====================

def build_response(speech_text: str, should_end_session: bool = True,
                   reprompt: str = None) -> dict:
    """Constroi resposta simples de voz"""
    response = {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech_text
            },
            "shouldEndSession": should_end_session
        }
    }

    if reprompt:
        response["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt
            }
        }

    return response


def build_audio_response(titulo: str, url_audio: str) -> dict:
    """Constroi resposta com reproducao de audio"""
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": f"Reproduzindo: {titulo}"
            },
            "directives": [
                {
                    "type": "AudioPlayer.Play",
                    "playBehavior": "REPLACE_ALL",
                    "audioItem": {
                        "stream": {
                            "url": url_audio,
                            "token": titulo,
                            "offsetInMilliseconds": 0
                        },
                        "metadata": {
                            "title": titulo,
                            "subtitle": "Projeto Caxinguele",
                        }
                    }
                }
            ],
            "shouldEndSession": True
        }
    }
