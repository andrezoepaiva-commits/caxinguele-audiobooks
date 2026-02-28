"""
  Super Alexa — Projeto Caxinguele v2
  Lambda Function (AWS Lambda + Python 3.11)

  Navegacao multi-nivel com state machine:
    nivel=menu     → amigo escolhe CATEGORIA pelo numero
    nivel=submenu  → amigo escolhe OPCAO dentro da categoria
    nivel=item     → amigo ouve detalhes e pode EDITAR
    nivel=editar   → amigo edita campo de um item

  Padrao universal: toda listagem termina com:
    [penultimo] Repetir opcoes
    [ultimo]    Voltar ao menu principal

  Menus editaveis por voz: [3] Favoritos, [5] Calendario, [8] Reunioes, [10] Listas
  """

import json
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==================== CONFIGURACOES ====================

RSS_BASE_URL = "https://andrezoepaiva-commits.github.io/caxinguele-audiobooks"

# Menu padrao sincronizado com o Labirinto de Numeros
# Numeracao sequencial: 0-8 sao opcoes, 9 = voltar ao menu principal
MENU_DEFAULT = [
      {"numero": 0, "nome": "Organizacoes Mentais",           "tipo": "gravacao"},
      {"numero": 1, "nome": "Ultimas Atualizacoes",           "tipo": "recentes"},
      {"numero": 2, "nome": "Livros",                          "tipo": "filtro",  "categoria": "Livros"},
      {"numero": 3, "nome": "Favoritos Importantes",           "tipo": "favoritos"},
      {"numero": 4, "nome": "Musica",                          "tipo": "musica"},
      {"numero": 5, "nome": "Calendario e Compromissos",       "tipo": "calendario"},
      {"numero": 6,  "nome": "Reunioes Caxinguele",             "tipo": "reunioes"},
      {"numero": 7,  "nome": "YouTube e Videos",                "tipo": "youtube"},
      {"numero": 9,  "nome": "Configuracoes",                   "tipo": "configuracoes"},
      {"numero": 10, "nome": "Organizacoes da Mente em Listas", "tipo": "listas_mentais"},
]

# Numeros especiais reservados para navegacao
NUM_REPETIR = 98
NUM_VOLTAR  = 99

# DynamoDB para persistencia de capitulo entre sessoes
DYNAMODB_TABLE           = "caxinguele_progresso"
DYNAMODB_LISTENING_TABLE = "caxinguele_listening_history"  # tempo de leitura por sessao
TOKEN_SEPARADOR = "|||"  # usado no token do AudioPlayer: "livro_base|||capitulo_idx"

# YouTube e WhatsApp (variaveis de ambiente configuradas no Lambda Console)
import os
YOUTUBE_API_KEY   = os.environ.get("YOUTUBE_API_KEY", "")
WHATSAPP_TOKEN    = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WHATSAPP_DEST     = os.environ.get("WHATSAPP_DEST", "")  # numero do usuario


# ==================== PONTO DE ENTRADA ====================

def lambda_handler(event, context):
      try:
          request_type = event.get("request", {}).get("type", "")
          logger.info(f"Request: {request_type}")

          if request_type == "LaunchRequest":
              return handle_launch(event)
          elif request_type == "IntentRequest":
              return handle_intent(event)
          elif request_type == "SessionEndedRequest":
              return {"version": "1.0", "response": {}}
          # Controles do AudioPlayer (botoes no app ou comandos de voz durante musica)
          elif request_type == "PlaybackController.NextCommandIssued":
              return handle_playback_next(event)
          elif request_type == "PlaybackController.PreviousCommandIssued":
              return handle_playback_prev(event)
          elif request_type == "AudioPlayer.PlaybackStarted":
              return handle_playback_started(event)
          elif request_type == "AudioPlayer.PlaybackStopped":
              return handle_playback_stopped(event)
          elif request_type in ("AudioPlayer.PlaybackFinished", "AudioPlayer.PlaybackNearlyFinished",
                                 "AudioPlayer.PlaybackFailed"):
              return {"version": "1.0", "response": {}}
          else:
              return _resp("Desculpe, nao entendi.")

      except Exception as e:
          logger.error(f"ERRO CRITICO: {str(e)}", exc_info=True)
          return _resp("Houve um erro. Tente novamente.", end=True)


# ==================== LAUNCH ====================

def handle_launch(event):
      """Abertura: mostra menu principal (nivel 1). Carrega progresso salvo."""
      documentos, menu = _buscar_dados_completos()
      user_id = _get_user_id(event)
      progresso = _carregar_progresso(user_id)

      texto = _enumerar_menu_principal(menu, documentos)
      session = {
          "nivel":      "menu",
          "todos_docs": json.dumps(documentos),
          "menu":       json.dumps(menu),
          "user_id":    user_id,
          "progresso":  json.dumps(progresso),
      }

      _registrar_uso("_abertura", "launch", len(documentos))
      return _resp(texto, end=False, reprompt="Diga o numero.", session=session)


# ==================== DISPATCHER ====================

def handle_intent(event):
      intent_name = event.get("request", {}).get("intent", {}).get("name", "")
      slots = event.get("request", {}).get("intent", {}).get("slots", {})
      session = event.get("session", {}).get("attributes", {}) or {}

      nivel = session.get("nivel", "menu")
      logger.info(f"Intent: {intent_name} | Nivel: {nivel}")

      # Intents built-in
      if intent_name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
          return _resp("Ate logo!", end=True)
      if intent_name == "AMAZON.PauseIntent":
          # Para o audio e mostra menu de opcoes
          stop_directive = {"type": "AudioPlayer.Stop"}

          # Recupera contexto do token do AudioPlayer
          audio_ctx = event.get("context", {}).get("AudioPlayer", {})
          token = audio_ctx.get("token", "")
          livro_titulo = ""
          cap_num = 1

          if TOKEN_SEPARADOR in token:
              partes_token = token.split(TOKEN_SEPARADOR)
              livro_base_token = partes_token[0]
              try:
                  cap_idx = int(partes_token[1])
                  cap_num = cap_idx + 1
              except Exception:
                  cap_idx = 0
              # Ignora token de música (começa com "MUSICA") — só exibe título para livros
              if not livro_base_token.startswith("MUSICA"):
                  livro_titulo = livro_base_token

          texto_livro = f"{livro_titulo}, capitulo {cap_num}. " if livro_titulo else ""
          texto = (
              f"Audio pausado. {texto_livro}"
              "1 para pular para o proximo capitulo. "
              "2 para voltar ao capitulo anterior. "
              "3 para velocidade. "
              f"{NUM_REPETIR} para repetir opcoes. {NUM_VOLTAR} para menu principal. "
              "O que deseja fazer?"
          )

          new_session = {
              **session,
              "nivel": "submenu",
              "menu_tipo": "playback_pausado",
              "audio_token": token,
              "livro_titulo_pausado": livro_titulo,
              "capitulo_pausado": str(cap_num - 1),
          }
          return {
              "version": "1.0",
              "response": {
                  "outputSpeech": {"type": "PlainText", "text": texto},
                  "reprompt": {"outputSpeech": {"type": "PlainText", "text": "Diga uma opcao."}},
                  "directives": [stop_directive],
                  "shouldEndSession": False,
              },
              "sessionAttributes": new_session,
          }
      if intent_name == "AMAZON.ResumeIntent":
          # Retoma — por ora, diz para reabrir a skill
          return _resp(
              "Para retomar, diga: Alexa, abre super alexa. "
              "E depois escolha o menu que voce estava.",
              end=True)
      if intent_name == "AMAZON.HelpIntent":
          return _handle_ajuda(session)
      if intent_name in ("ListarDocumentosIntent", "AMAZON.NavigateHomeIntent"):
          return _voltar_nivel_anterior(session)

      # Pular/voltar capitulo por voz durante leitura
      if intent_name == "AMAZON.NextIntent":
          return _pular_capitulo_sessao(session, direcao=+1)
      if intent_name == "AMAZON.PreviousIntent":
          return _pular_capitulo_sessao(session, direcao=-1)

      # Intent principal: numero
      if intent_name == "SelecionarNumeroIntent":
          numero = _extrair_numero(slots, "numero")
          # Se AMAZON.NUMBER nao preencheu, tenta extrair da fala bruta
          if numero is None:
              numero = _extrair_numero_da_fala(event)
          if numero is None:
              return _resp("Nao entendi o numero. Diga por exemplo: numero nove.",
                            end=False, session=session)
          return _roteador_numero(numero, session)

      # Atalhos de voz
      if intent_name == "FiltrarPorTipoIntent":
          return _handle_filtrar_tipo(slots, session)
      if intent_name == "DocumentoNovosIntent":
          return _handle_novidades(session)
      if intent_name == "LerDocumentoIntent":
          return _handle_ler_documento(slots, session)

      # YouTube: busca por voz (YoutubeSearchIntent serve para busca E adicionar canal)
      if intent_name == "YoutubeSearchIntent":
          query = (slots.get("query", {}).get("value", "") or "").strip()
          if not query:
              return _resp("Nao entendi. Tente novamente.", end=False, session=session)

          # Se estamos no fluxo de adicionar canal, usa a query como nome do canal
          if session.get("menu_tipo") == "youtube_canais_adicionar":
              canal = _buscar_canal_youtube_api(query)
              if not canal:
                  return _resp(
                      f"Canal {query} nao encontrado. Tente outro nome. "
                      f"{NUM_VOLTAR} para voltar.",
                      end=False, session=session)
              user_id = session.get("user_id", "")
              canais = _get_canais_youtube(user_id)
              if any(c.get("channel_id") == canal["channel_id"] for c in canais):
                  return _resp(
                      f"Canal {canal['nome']} ja esta salvo. {NUM_VOLTAR} para voltar.",
                      end=False, session={**session, "menu_tipo": "youtube_canais"})
              canais.append(canal)
              _salvar_canais_youtube(user_id, canais)
              return _resp(
                  f"Canal {canal['nome']} adicionado. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "menu_tipo": "youtube_canais"})

          # Busca normal no YouTube
          videos = _buscar_youtube_api(query, max_results=5)
          if not videos:
              return _resp(
                  f"Nenhum resultado para {query}. Tente outra busca. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          partes = []
          for i, v in enumerate(videos, 1):
              partes.append(f"{i}. {v['titulo']}, {v.get('duracao', '')}")
          texto = (
              f"Resultados para {query}. {len(videos)} videos. "
              f"{'. '.join(partes)}. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
              "Diga o numero do video."
          )
          new_session = {
              **session,
              "nivel": "submenu",
              "menu_tipo": "youtube_busca",
              "youtube_videos": json.dumps(videos),
          }
          return _resp(texto, end=False, reprompt="Diga o numero.", session=new_session)

      # Fallback: tenta extrair numero da fala bruta
      if intent_name == "AMAZON.FallbackIntent":
          fala_bruta = event.get("request", {}).get("intent", {}).get("slots", {})
          # Tenta extrair numero de qualquer texto
          numero = _extrair_numero_da_fala(event)
          if numero is not None:
              return _roteador_numero(numero, session)
          return _resp("Nao entendi. Tente dizer o numero, por exemplo: numero dois.",
                        end=False, session=session)

      # Ultimo recurso: tenta extrair numero da fala bruta (inputTranscript)
      numero = _extrair_numero_da_fala(event)
      if numero is not None:
          logger.info(f"Catch-all: extraiu {numero} de intent {intent_name}")
          return _roteador_numero(numero, session)
      logger.warning(f"Intent nao tratado: {intent_name} | slots: {slots}")
      return _resp("Nao entendi. Diga o numero ou diga voltar.",
                    end=False, session=session)


# ==================== ROTEADOR DE NUMEROS ====================

def _roteador_numero(numero, session):
      """Decide o que fazer com base no nivel atual e no numero escolhido."""
      nivel = session.get("nivel", "menu")

      # Comandos universais de navegacao
      if numero == NUM_REPETIR:
          return _repetir_opcoes(session)
      if numero == NUM_VOLTAR:
          return _voltar_nivel_anterior(session)

      if nivel == "menu":
          return _selecionar_menu(numero, session)
      elif nivel == "submenu":
          return _selecionar_submenu(numero, session)
      elif nivel == "item":
          return _selecionar_acao_item(numero, session)
      elif nivel == "editar":
          return _selecionar_campo_editar(numero, session)
      else:
          return _voltar_menu_principal(session)


# ==================== NIVEL: MENU PRINCIPAL ====================

def _selecionar_menu(numero, session):
      """Amigo escolheu um menu principal pelo numero."""
      menu = _obter_json(session, "menu") or list(MENU_DEFAULT)
      todos_docs = _obter_json(session, "todos_docs") or []

      cat = next((c for c in menu if c.get("numero") == numero), None)
      if not cat:
          return _resp(f"Numero {numero} invalido. " + _enumerar_menu_principal(menu, todos_docs),
                        end=False, session=session)

      tipo = cat.get("tipo", "filtro")
      nome = cat["nome"]
      _registrar_uso(nome, "categoria_selecionada")

      # ---------- Menu 0: Gravacao (so funciona no app, nao na Alexa) ----------
      if tipo == "gravacao":
          return _resp(
              f"{nome}. Para gravar organizacoes mentais, use o aplicativo no celular. "
              "Diga outro numero ou diga voltar.",
              end=False, session=session)

      # ---------- Menu 1: Ultimas Atualizacoes (feed) ----------
      if tipo == "recentes":
          docs = _docs_recentes(todos_docs)
          if not docs:
              return _resp("Nao ha novidades recentes. Diga outro numero.",
                            end=False, session=session)
          return _listar_docs_como_submenu(docs, nome, session)

      # ---------- Menu 2: Livros → submenu de categorias ----------
      if tipo == "filtro":
          return _menu_livros_categorias(session)

      # ---------- Menu 3: Favoritos ----------
      if tipo == "favoritos":
          return _menu_favoritos(session)

      # ---------- Menu 4: Musica ----------
      if tipo == "musica":
          return _menu_musicas(session)

      # ---------- Menu 5: Calendario e Compromissos ----------
      if tipo == "calendario":
          return _menu_calendario(session)

      # ---------- Menu 6: Reunioes Caxinguele ----------
      if tipo == "reunioes":
          return _menu_reunioes(session)

      # ---------- Menu 9: Configuracoes ----------
      if tipo == "configuracoes":  # numero 9
          return _resp(
              f"{nome}. 1 para Velocidade da Fala. "
              "2 para Guia do Usuario. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
              end=False,
              session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})

      # ---------- Menu 10: Listas Mentais ----------
      if tipo == "listas_mentais":
          return _menu_listas(session)

      # ---------- Menu 7: YouTube e Videos ----------
      if tipo == "youtube":
          return _menu_youtube(session)

      # ---------- Voltar ao Menu Principal (tipo legado) ----------
      if tipo == "voltar_menu":
          return _voltar_menu_principal(session)

      # Fallback: tipo desconhecido
      return _resp(f"{nome}. Este menu ainda nao esta disponivel por voz. Diga outro numero.",
                    end=False, session=session)


# ==================== DYNAMODB: PERSISTENCIA DE PROGRESSO ====================

_dynamo_client = None

def _get_user_id(event):
      """Extrai o user_id da Alexa (identifica o usuario atraves das sessoes)."""
      try:
          uid = event.get("context", {}).get("System", {}).get("user", {}).get("userId", "")
          return uid[:60] if uid else "usuario_default"
      except Exception:
          return "usuario_default"


def _get_dynamo():
      global _dynamo_client
      if _dynamo_client is None:
          _dynamo_client = boto3.resource("dynamodb", region_name="us-east-1")
      return _dynamo_client


def _carregar_progresso(user_id):
      """Carrega progresso salvo do usuario (qual capitulo estava em cada livro)."""
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          resp = table.get_item(Key={"user_id": user_id})
          return resp.get("Item", {}).get("progresso", {})
      except Exception as e:
          logger.info(f"Progresso nao encontrado (normal na 1a vez): {e}")
          return {}


def _salvar_progresso(user_id, livro_base, capitulo_idx):
      """Salva em qual capitulo o usuario esta."""
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="SET progresso.#livro = :cap",
              ExpressionAttributeNames={"#livro": livro_base},
              ExpressionAttributeValues={":cap": int(capitulo_idx)},
          )
          logger.info(f"Progresso salvo: {livro_base} cap {capitulo_idx}")
      except Exception as e:
          logger.warning(f"Erro ao salvar progresso: {e}")


# ==================== DYNAMODB: TEMPO DE LEITURA ====================

def _registrar_sessao_inicio(user_id, token, timestamp):
      """Cria entrada de sessao de escuta com tempo_inicio (sem tempo_fim ainda)."""
      try:
          # Extrai nome do documento a partir do token (ex: "Livro_Base|||0")
          partes = token.split(TOKEN_SEPARADOR) if TOKEN_SEPARADOR in token else [token, "0"]
          documento = partes[0].replace("_", " ")

          table = _get_dynamo().Table(DYNAMODB_LISTENING_TABLE)
          table.put_item(Item={
              "user_id":       user_id,
              "data_sessao":   timestamp,  # Sort key = timestamp de inicio
              "documento":     documento,
              "token":         token,
              "tempo_inicio":  timestamp,
              "tempo_fim":     None,
              "minutos_ouvidos": 0,
              "status":        "em_andamento",
          })
          logger.info(f"Sessao inicio registrada: {documento} @ {timestamp}")
      except Exception as e:
          logger.warning(f"Erro ao registrar inicio de sessao: {e}")


def _registrar_sessao_fim(user_id, token, timestamp_fim):
      """Busca a sessao aberta e calcula minutos_ouvidos."""
      try:
          from boto3.dynamodb.conditions import Key as DynKey
          table = _get_dynamo().Table(DYNAMODB_LISTENING_TABLE)

          # Busca sessoes em andamento para este usuario com este token
          resp = table.query(
              KeyConditionExpression=DynKey("user_id").eq(user_id),
              FilterExpression="token = :t AND #s = :s",
              ExpressionAttributeNames={"#s": "status"},
              ExpressionAttributeValues={":t": token, ":s": "em_andamento"},
              ScanIndexForward=False,  # mais recente primeiro
              Limit=1,
          )
          itens = resp.get("Items", [])
          if not itens:
              return  # Nao havia sessao aberta

          sessao = itens[0]
          data_sessao = sessao["data_sessao"]
          tempo_inicio_str = sessao.get("tempo_inicio", data_sessao)

          # Calcula minutos ouvidos
          try:
              t_inicio = datetime.fromisoformat(tempo_inicio_str.replace("Z", "+00:00"))
              t_fim    = datetime.fromisoformat(timestamp_fim.replace("Z", "+00:00"))
              minutos  = max(0, int((t_fim - t_inicio).total_seconds() / 60))
          except Exception:
              minutos = 0

          # Atualiza entrada com tempo_fim e minutos
          table.update_item(
              Key={"user_id": user_id, "data_sessao": data_sessao},
              UpdateExpression="SET tempo_fim = :tf, minutos_ouvidos = :m, #s = :s",
              ExpressionAttributeNames={"#s": "status"},
              ExpressionAttributeValues={
                  ":tf": timestamp_fim,
                  ":m":  minutos,
                  ":s":  "concluida",
              }
          )
          logger.info(f"Sessao fim: {sessao['documento']} — {minutos} min")
      except Exception as e:
          logger.warning(f"Erro ao registrar fim de sessao: {e}")


def _calcular_tempo_leitura(user_id, periodo="mes"):
      """
      Retorna estatisticas de tempo de leitura para o periodo.
      periodo: 'mes' | 'semana' | 'hoje'
      Retorna dict: total_minutos, horas_minutos, media_por_dia, top_documentos
      """
      try:
          from boto3.dynamodb.conditions import Key as DynKey
          table = _get_dynamo().Table(DYNAMODB_LISTENING_TABLE)

          # Define corte de data
          agora = datetime.utcnow()
          if periodo == "mes":
              corte = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
          elif periodo == "semana":
              corte = agora - timedelta(days=agora.weekday())
              corte = corte.replace(hour=0, minute=0, second=0, microsecond=0)
          else:  # hoje
              corte = agora.replace(hour=0, minute=0, second=0, microsecond=0)

          corte_str = corte.isoformat() + "Z"

          resp = table.query(
              KeyConditionExpression=DynKey("user_id").eq(user_id) & DynKey("data_sessao").gte(corte_str),
              FilterExpression="#s = :s",
              ExpressionAttributeNames={"#s": "status"},
              ExpressionAttributeValues={":s": "concluida"},
          )
          sessoes = resp.get("Items", [])

          total = sum(int(s.get("minutos_ouvidos", 0)) for s in sessoes)
          horas  = total // 60
          minutos_rest = total % 60
          horas_str = f"{horas}h {minutos_rest}min" if horas > 0 else f"{minutos_rest}min"

          dias = max(1, (agora - corte).days + 1)
          media = round(total / dias)

          # Top documentos
          contagem = {}
          for s in sessoes:
              doc = s.get("documento", "Desconhecido")
              contagem[doc] = contagem.get(doc, 0) + int(s.get("minutos_ouvidos", 0))

          total_para_pct = max(total, 1)
          top = sorted(
              [{"documento": d, "minutos": m, "percentual": int(m / total_para_pct * 100)}
               for d, m in contagem.items()],
              key=lambda x: -x["minutos"]
          )[:5]

          return {
              "total_minutos":   total,
              "horas_minutos":   horas_str,
              "media_por_dia":   media,
              "top_documentos":  top,
          }
      except Exception as e:
          logger.warning(f"Erro ao calcular tempo de leitura: {e}")
          return {"total_minutos": 0, "horas_minutos": "0min", "media_por_dia": 0, "top_documentos": []}


# ==================== HELPERS DE CAPITULOS ====================

def _extrair_livro_base(titulo):
      """Extrai o nome base do livro removendo 'Cap XX' e tudo depois.
      Ex: '(anonymous) - Cap 01 - CAPITULO 1 Introducao.mp3' → '(anonymous)'
      """
      titulo = titulo.strip()
      if titulo.lower().endswith(".mp3"):
          titulo = titulo[:-4]
      match = re.match(r"^(.+?)\s*[-–]\s*Cap(?:itulo|ítulo)?\s*\d+", titulo, re.IGNORECASE)
      if match:
          return match.group(1).strip()
      # Fallback: tudo antes do primeiro " - "
      partes = titulo.split(" - ")
      return partes[0].strip() if len(partes) > 1 else titulo


def _extrair_num_capitulo(titulo):
      """Extrai o número do capítulo de um título. Ex: 'Cap 03' → 3."""
      match = re.search(r"Cap(?:itulo|ítulo)?\s*(\d+)", titulo, re.IGNORECASE)
      return int(match.group(1)) if match else 999


def _agrupar_livros(docs):
      """Agrupa documentos por livro_base, retorna lista de livros com seus capítulos."""
      livros_dict = {}
      for doc in docs:
          livro_base = _extrair_livro_base(doc.get("titulo", ""))
          if livro_base not in livros_dict:
              livros_dict[livro_base] = []
          livros_dict[livro_base].append(doc)

      # Ordena capítulos dentro de cada livro
      for livro_base in livros_dict:
          livros_dict[livro_base].sort(
              key=lambda d: _extrair_num_capitulo(d.get("titulo", ""))
          )

      # Monta lista de livros
      livros = []
      for livro_base, caps in livros_dict.items():
          livros.append({
              "livro_base":       livro_base,
              "titulo":           livro_base if livro_base.lower() not in ("anonymous", "untitled", "") else "Livro sem nome",
              "total_capitulos":  len(caps),
              "capitulos":        caps,
              "url_audio":        caps[0].get("url_audio", ""),  # primeiro capitulo
          })
      return livros


def _pular_capitulo_sessao(session, direcao):
      """Pula para próximo/anterior capítulo ou música com base na sessao ativa."""
      # Se estiver tocando musica, pula na playlist
      musica_atual = session.get("musica_atual")
      if musica_atual is not None:
          musicas = _obter_json(session, "musicas") or _buscar_musicas_json()
          musicas_com_url = [m for m in musicas if m.get("url")]
          idx = int(musica_atual) + direcao
          if idx < 0:
              idx = len(musicas_com_url) - 1  # volta para ultima
          if idx >= len(musicas_com_url):
              idx = 0  # volta para primeira
          if musicas_com_url:
              m = musicas_com_url[idx]
              titulo = m.get("titulo", f"Musica {idx + 1}")
              token = f"MUSICA{TOKEN_SEPARADOR}{idx}"
              new_session = {**session, "musica_atual": str(idx)}
              return _build_audio(titulo, m["url"], token=token, session_extra=new_session)
          return _resp("Nenhuma musica disponivel.", end=False, session=session)

      capitulos = _obter_json(session, "capitulos_livro") or []
      cap_atual = int(session.get("capitulo_atual", "0"))
      livro_base = session.get("livro_base", "")
      novo_cap = cap_atual + direcao

      if not capitulos:
          return _resp(
              "Nao ha capitulos em reproducao. Diga o numero do menu.",
              end=False, session=session)
      if novo_cap < 0:
          return _resp(
              "Este eh o primeiro capitulo. Diga 1 para comecar novamente.",
              end=False, session=session)
      if novo_cap >= len(capitulos):
          return _resp(
              "Fim do livro! Voce ouviu todos os capitulos. "
              f"{NUM_VOLTAR} para voltar ao menu.",
              end=False, session=session)

      cap = capitulos[novo_cap]
      titulo = _titulo_curto(cap.get("titulo", f"Capitulo {novo_cap + 1}"))
      url = cap.get("url_audio", "")
      user_id = session.get("user_id", "")

      if url:
          if user_id and livro_base:
              _salvar_progresso(user_id, livro_base, novo_cap)
          token = f"{livro_base}{TOKEN_SEPARADOR}{novo_cap}"
          new_session = {**session, "capitulo_atual": str(novo_cap)}
          return _build_audio(titulo, url, token=token, session_extra=new_session)

      return _resp(
          f"Capitulo {novo_cap + 1} sem audio disponivel. "
          f"Tente outro ou diga {NUM_VOLTAR} para voltar.",
          end=False, session=session)


def handle_playback_started(event):
      """Quando AudioPlayer comeca a tocar, salva progresso e registra inicio de sessao."""
      try:
          token = event.get("request", {}).get("token", "")
          user_id = _get_user_id(event)
          timestamp = event.get("request", {}).get("timestamp", datetime.utcnow().isoformat() + "Z")
          if TOKEN_SEPARADOR in token and user_id:
              partes = token.split(TOKEN_SEPARADOR)
              # Nao salva progresso de musica, so de livros/artigos
              if partes[0] != "MUSICA":
                  livro_base = partes[0]
                  capitulo_idx = int(partes[1])
                  _salvar_progresso(user_id, livro_base, capitulo_idx)
                  # Registra inicio da sessao de escuta para calcular tempo depois
                  _registrar_sessao_inicio(user_id, token, timestamp)
      except Exception as e:
          logger.warning(f"Erro ao salvar progresso no playback: {e}")
      return {"version": "1.0", "response": {}}


def handle_playback_stopped(event):
      """Quando usuario para o audio, calcula e salva minutos ouvidos no DynamoDB."""
      try:
          token = event.get("request", {}).get("token", "")
          user_id = _get_user_id(event)
          timestamp = event.get("request", {}).get("timestamp", datetime.utcnow().isoformat() + "Z")
          # Nao rastreia paradas de musica
          if TOKEN_SEPARADOR in token and token.split(TOKEN_SEPARADOR)[0] != "MUSICA":
              _registrar_sessao_fim(user_id, token, timestamp)
      except Exception as e:
          logger.warning(f"Erro ao registrar parada de audio: {e}")
      return {"version": "1.0", "response": {}}


def handle_playback_next(event):
      """Botão 'próxima faixa' no app durante reprodução de MP3."""
      try:
          token = event.get("request", {}).get("token", "")
          user_id = _get_user_id(event)
          if TOKEN_SEPARADOR in token:
              partes = token.split(TOKEN_SEPARADOR)
              tipo_audio = partes[0]
              idx_atual = int(partes[1])

              # --- Musica: proxima da playlist ---
              if tipo_audio == "MUSICA":
                  musicas = _buscar_musicas_json()
                  musicas_com_url = [m for m in musicas if m.get("url")]
                  novo_idx = idx_atual + 1
                  if novo_idx < len(musicas_com_url):
                      m = musicas_com_url[novo_idx]
                      titulo = m.get("titulo", f"Musica {novo_idx + 1}")
                      novo_token = f"MUSICA{TOKEN_SEPARADOR}{novo_idx}"
                      return _build_audio(titulo, m["url"], token=novo_token)
                  # Fim da playlist: volta para a primeira
                  if musicas_com_url:
                      m = musicas_com_url[0]
                      titulo = m.get("titulo", "Musica 1")
                      novo_token = f"MUSICA{TOKEN_SEPARADOR}0"
                      return _build_audio(titulo, m["url"], token=novo_token)

              # --- Livros: proximo capitulo ---
              else:
                  livro_base = tipo_audio
                  cap_atual = idx_atual
                  documentos, _ = _buscar_dados_completos()
                  docs_livro = [d for d in documentos if _extrair_livro_base(d.get("titulo","")) == livro_base]
                  docs_livro.sort(key=lambda d: _extrair_num_capitulo(d.get("titulo","")))
                  novo_cap = cap_atual + 1
                  if novo_cap < len(docs_livro):
                      cap = docs_livro[novo_cap]
                      titulo = _titulo_curto(cap.get("titulo", f"Capitulo {novo_cap + 1}"))
                      url = cap.get("url_audio", "")
                      novo_token = f"{livro_base}{TOKEN_SEPARADOR}{novo_cap}"
                      if url:
                          _salvar_progresso(user_id, livro_base, novo_cap)
                          return _build_audio(titulo, url, token=novo_token)
      except Exception as e:
          logger.warning(f"Erro handle_playback_next: {e}")
      return {"version": "1.0", "response": {}}


def handle_playback_prev(event):
      """Botão 'faixa anterior' no app durante reprodução de MP3."""
      try:
          token = event.get("request", {}).get("token", "")
          user_id = _get_user_id(event)
          if TOKEN_SEPARADOR in token:
              partes = token.split(TOKEN_SEPARADOR)
              tipo_audio = partes[0]
              idx_atual = int(partes[1])

              # --- Musica: anterior da playlist ---
              if tipo_audio == "MUSICA":
                  musicas = _buscar_musicas_json()
                  musicas_com_url = [m for m in musicas if m.get("url")]
                  novo_idx = idx_atual - 1
                  if novo_idx >= 0 and novo_idx < len(musicas_com_url):
                      m = musicas_com_url[novo_idx]
                      titulo = m.get("titulo", f"Musica {novo_idx + 1}")
                      novo_token = f"MUSICA{TOKEN_SEPARADOR}{novo_idx}"
                      return _build_audio(titulo, m["url"], token=novo_token)
                  # Ja na primeira: vai para ultima
                  if musicas_com_url:
                      ultimo = len(musicas_com_url) - 1
                      m = musicas_com_url[ultimo]
                      titulo = m.get("titulo", f"Musica {ultimo + 1}")
                      novo_token = f"MUSICA{TOKEN_SEPARADOR}{ultimo}"
                      return _build_audio(titulo, m["url"], token=novo_token)

              # --- Livros: capitulo anterior ---
              else:
                  livro_base = tipo_audio
                  cap_atual = idx_atual
                  documentos, _ = _buscar_dados_completos()
                  docs_livro = [d for d in documentos if _extrair_livro_base(d.get("titulo","")) == livro_base]
                  docs_livro.sort(key=lambda d: _extrair_num_capitulo(d.get("titulo","")))
                  novo_cap = cap_atual - 1
                  if novo_cap >= 0:
                      cap = docs_livro[novo_cap]
                      titulo = _titulo_curto(cap.get("titulo", f"Capitulo {novo_cap + 1}"))
                      url = cap.get("url_audio", "")
                      novo_token = f"{livro_base}{TOKEN_SEPARADOR}{novo_cap}"
                      if url:
                          _salvar_progresso(user_id, livro_base, novo_cap)
                          return _build_audio(titulo, url, token=novo_token)
      except Exception as e:
          logger.warning(f"Erro handle_playback_prev: {e}")
      return {"version": "1.0", "response": {}}


# ==================== MENU [4]: MUSICAS CAXINGUELE ====================

# URLs das musicas — após upload para o Google Drive ou S3, atualize aqui
MUSICAS_CAXINGUELE = [
    {"numero": 1, "titulo": "Música 1",  "url": ""},
    {"numero": 2, "titulo": "Música 2",  "url": ""},
    {"numero": 3, "titulo": "Música 3",  "url": ""},
    {"numero": 4, "titulo": "Música 4",  "url": ""},
    {"numero": 5, "titulo": "Música 5",  "url": ""},
    {"numero": 6, "titulo": "Música 6",  "url": ""},
    {"numero": 7, "titulo": "Música 7",  "url": ""},
    {"numero": 8, "titulo": "Música 8",  "url": ""},
]


def _buscar_musicas_json():
      """Tenta buscar musicas.json do GitHub Pages. Fallback para dict local."""
      try:
          url = f"{RSS_BASE_URL}/musicas.json"
          with urllib.request.urlopen(url, timeout=8) as response:
              dados = json.loads(response.read().decode("utf-8"))
              return dados.get("musicas", [])
      except Exception:
          return MUSICAS_CAXINGUELE  # fallback para o dict hardcoded


def _menu_musicas(session):
      """Lista musicas Caxinguele numeradas. Tenta ler de musicas.json primeiro."""
      todas = _buscar_musicas_json()
      musicas = [m for m in todas if m.get("url")]
      if not musicas:
          return _resp(
              "Musicas Caxinguele. As musicas estao sendo preparadas. "
              "Em breve estao disponiveis aqui. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session=session)
      partes = [f"{m['numero']}. {m['titulo']}" for m in musicas]
      texto = (
          f"Musicas Caxinguele. {len(musicas)} musica{'s' if len(musicas) > 1 else ''} disponivel{'is' if len(musicas) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual numero quer ouvir?"
      )
      new_session = {
          **session,
          "nivel":     "submenu",
          "menu_tipo": "musicas",
          "musicas":   json.dumps(musicas),
      }
      return _resp(texto, end=False, reprompt="Diga o numero da musica.", session=new_session)


# ==================== MENU [2]: LIVROS ====================

# ==================== MENU [2]: LIVROS COM CATEGORIAS ====================

# Categorias de livros — o "filtro" deve bater com o campo "categoria" dos documentos no indice.json
# Por enquanto todos os livros têm categoria="Livros", então ambas as categorias filtram por "Livros"
# Futuramente: criar subcategorias no pipeline de upload (ex: "Livros: Inteligencia Sensorial")
LIVROS_CATEGORIAS = [
      {
          "numero": 1,
          "nome": "Inteligencia Sensorial",
          "nome_display": "Livros: Inteligencia Sensorial",
          "filtro_subcategoria": "Livros: Inteligencia Sensorial",
      },
      {
          "numero": 2,
          "nome": "Geral",
          "nome_display": "Livros: Geral",
          "filtro_subcategoria": "Livros: Geral",
      },
]


def _menu_livros_categorias(session):
      """Submenu de categorias de livros. Amigo escolhe categoria → lista de livros."""
      partes = [f"{cat['numero']} para {cat['nome_display']}" for cat in LIVROS_CATEGORIAS]
      texto = (
          "Livros. Escolha a categoria. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar ao menu principal."
      )
      new_session = {
          **session,
          "nivel":     "submenu",
          "menu_tipo": "livros_categorias",
      }
      return _resp(texto, end=False, reprompt="Diga o numero da categoria.", session=new_session)


def _menu_livros(docs_brutos, session, categoria_nome=""):
      """Lista livros únicos (agrupados por titulo base). Amigo escolhe → opcoes do livro."""
      livros = _agrupar_livros(docs_brutos)
      if not livros:
          return _resp(
              f"Nenhum livro catalogado em {categoria_nome}. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session={**session, "nivel": "submenu", "menu_tipo": "livros_categorias"})

      partes = []
      for i, livro in enumerate(livros, 1):
          n_caps = livro["total_capitulos"]
          caps_txt = f"{n_caps} capitulos" if n_caps > 1 else "1 capitulo"
          partes.append(f"{i}. {livro['titulo']}, {caps_txt}")

      texto = (
          f"Livros {categoria_nome}. "
          f"Voce tem {len(livros)} livro{'s' if len(livros) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual livro quer ouvir?"
      )
      new_session = {
          **session,
          "nivel":             "submenu",
          "menu_tipo":         "livros",
          "livros_dados":      json.dumps(livros),
          "livros_categoria":  categoria_nome,
      }
      return _resp(texto, end=False, reprompt="Diga o numero do livro.", session=new_session)


# ==================== MENU [9]: YOUTUBE E VIDEOS ====================

def _menu_youtube(session):
      """Submenu principal do YouTube: ultimas atualizacoes, busca, gerenciar canais."""
      texto = (
          "YouTube e Videos. "
          "1 para Ultimas Atualizacoes dos seus canais. "
          "2 para Pesquisar no YouTube. "
          "3 para Meus Canais. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar ao menu principal."
      )
      new_session = {
          **session,
          "nivel":     "submenu",
          "menu_tipo": "youtube",
      }
      return _resp(texto, end=False, reprompt="Diga o numero.", session=new_session)


def _buscar_videos_canal_rss(channel_id, max_videos=5):
      """Busca videos recentes de um canal via RSS (gratuito, sem API key)."""
      url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
      try:
          with urllib.request.urlopen(url, timeout=10) as response:
              xml_data = response.read().decode("utf-8")
          root = ET.fromstring(xml_data)
          ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}
          entries = root.findall("atom:entry", ns)[:max_videos]
          videos = []
          for entry in entries:
              titulo = entry.find("atom:title", ns)
              video_id = entry.find("yt:videoId", ns)
              published = entry.find("atom:published", ns)
              autor = entry.find("atom:author/atom:name", ns)
              if titulo is not None and video_id is not None:
                  videos.append({
                      "titulo": titulo.text,
                      "video_id": video_id.text,
                      "url": f"https://www.youtube.com/watch?v={video_id.text}",
                      "canal": autor.text if autor is not None else "",
                      "data": published.text[:10] if published is not None else "",
                  })
          return videos
      except Exception as e:
          logger.warning(f"Erro RSS YouTube canal {channel_id}: {e}")
          return []


def _buscar_youtube_api(query, max_results=5):
      """Busca videos no YouTube via Data API v3. Filtra Shorts (< 2 min)."""
      if not YOUTUBE_API_KEY:
          return []
      try:
          # Busca
          q_encoded = urllib.parse.quote(query)
          search_url = (
              f"https://www.googleapis.com/youtube/v3/search"
              f"?part=snippet&type=video&q={q_encoded}"
              f"&maxResults={max_results * 2}&key={YOUTUBE_API_KEY}"
              f"&relevanceLanguage=pt&regionCode=BR"
          )
          with urllib.request.urlopen(search_url, timeout=10) as response:
              data = json.loads(response.read().decode("utf-8"))
          items = data.get("items", [])
          if not items:
              return []

          # Busca duracoes para filtrar Shorts
          video_ids = ",".join([item["id"]["videoId"] for item in items])
          details_url = (
              f"https://www.googleapis.com/youtube/v3/videos"
              f"?part=contentDetails,snippet&id={video_ids}&key={YOUTUBE_API_KEY}"
          )
          with urllib.request.urlopen(details_url, timeout=10) as response:
              details = json.loads(response.read().decode("utf-8"))

          videos = []
          for v in details.get("items", []):
              duration = v.get("contentDetails", {}).get("duration", "PT0S")
              # Filtra Shorts (< 2 min)
              segundos = _parse_duration_iso(duration)
              if segundos < 120:
                  continue
              snippet = v.get("snippet", {})
              videos.append({
                  "titulo": snippet.get("title", "Sem titulo"),
                  "video_id": v["id"],
                  "url": f"https://www.youtube.com/watch?v={v['id']}",
                  "canal": snippet.get("channelTitle", ""),
                  "duracao": _formatar_duracao(segundos),
                  "duracao_seg": segundos,
              })
              if len(videos) >= max_results:
                  break
          return videos
      except Exception as e:
          logger.warning(f"Erro YouTube API: {e}")
          return []


def _parse_duration_iso(duration_str):
      """Converte duracao ISO 8601 (PT1H2M30S) para segundos."""
      import re as _re
      match = _re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
      if not match:
          return 0
      h = int(match.group(1) or 0)
      m = int(match.group(2) or 0)
      s = int(match.group(3) or 0)
      return h * 3600 + m * 60 + s


def _formatar_duracao(segundos):
      """Formata segundos para texto falado (ex: '1 hora e 23 minutos')."""
      h = segundos // 3600
      m = (segundos % 3600) // 60
      partes = []
      if h > 0:
          partes.append(f"{h} hora{'s' if h > 1 else ''}")
      if m > 0:
          partes.append(f"{m} minuto{'s' if m > 1 else ''}")
      return " e ".join(partes) if partes else "menos de 1 minuto"


def _resumir_video_youtube(video_id):
      """Busca transcricao do video via youtube-transcript-api.

      Extrai legendas (automaticas ou manuais) do YouTube e retorna
      a transcricao como texto para a Alexa ler em voz alta.
      Prioriza portugues, depois ingles.
      """
      if not video_id:
          return "Video invalido. Tente outro video."

      try:
          from youtube_transcript_api import YouTubeTranscriptApi
          api = YouTubeTranscriptApi()
          # Tenta buscar legendas em portugues primeiro, depois ingles
          transcript = api.fetch(video_id, languages=['pt', 'pt-BR', 'en'])
          # Junta todos os segmentos de legenda em um unico texto
          texto_completo = " ".join([snippet.text for snippet in transcript])
          if not texto_completo.strip():
              return "Video possui legendas mas estao vazias. Tente outro video."
          # Limita a 3000 caracteres para Alexa nao ficar muito longo
          resumo = texto_completo[:3000]
          if len(texto_completo) > 3000:
              resumo += "... Transcricao resumida por ser muito longa."
          return f"Transcricao do video. {resumo}"
      except ImportError:
          logger.warning("youtube-transcript-api nao instalada no Lambda")
          return "Funcionalidade de resumo indisponivel no momento. Tente novamente mais tarde."
      except Exception as e:
          logger.info(f"Falha ao buscar legendas para {video_id}: {e}")
          return ("Este video nao possui legendas disponiveis. "
                  "Tente um video que tenha legendas ativadas no YouTube.")



def _enviar_whatsapp(mensagem):
      """Envia mensagem via WhatsApp Cloud API (Meta)."""
      if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID or not WHATSAPP_DEST:
          return False
      try:
          url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
          payload = json.dumps({
              "messaging_product": "whatsapp",
              "to": WHATSAPP_DEST,
              "type": "text",
              "text": {"body": mensagem}
          }).encode("utf-8")
          req = urllib.request.Request(url, data=payload, method="POST", headers={
              "Authorization": f"Bearer {WHATSAPP_TOKEN}",
              "Content-Type": "application/json",
          })
          with urllib.request.urlopen(req, timeout=10) as response:
              return response.status == 200
      except Exception as e:
          logger.warning(f"Erro WhatsApp: {e}")
          return False


def _get_canais_youtube(user_id):
      """Busca canais YouTube salvos do usuario no DynamoDB."""
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          resp = table.get_item(Key={"user_id": user_id})
          item = resp.get("Item", {})
          return json.loads(item.get("canais_youtube", "[]"))
      except Exception:
          return []


def _salvar_canais_youtube(user_id, canais):
      """Salva canais YouTube do usuario no DynamoDB."""
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="SET canais_youtube = :c",
              ExpressionAttributeValues={":c": json.dumps(canais)},
          )
          return True
      except Exception as e:
          logger.warning(f"Erro salvando canais YouTube: {e}")
          return False


def _buscar_canal_youtube_api(nome_canal):
      """Busca canal no YouTube por nome via API v3."""
      if not YOUTUBE_API_KEY:
          return None
      try:
          q_encoded = urllib.parse.quote(nome_canal)
          url = (
              f"https://www.googleapis.com/youtube/v3/search"
              f"?part=snippet&type=channel&q={q_encoded}"
              f"&maxResults=1&key={YOUTUBE_API_KEY}"
          )
          with urllib.request.urlopen(url, timeout=10) as response:
              data = json.loads(response.read().decode("utf-8"))
          items = data.get("items", [])
          if items:
              snippet = items[0].get("snippet", {})
              return {
                  "channel_id": items[0]["id"]["channelId"],
                  "nome": snippet.get("channelTitle", nome_canal),
              }
      except Exception as e:
          logger.warning(f"Erro buscando canal YouTube: {e}")
      return None


def _menu_youtube_canais(session):
      """Submenu de gerenciamento de canais YouTube."""
      texto = (
          "Meus Canais. "
          "1 para ver seus canais. "
          "2 para adicionar canal. "
          "3 para remover canal. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
      )
      return _resp(texto, end=False, reprompt="Diga o numero.",
                    session={**session, "nivel": "submenu", "menu_tipo": "youtube_canais"})


# ==================== MENU [8]: CONFIGURACOES — VOZES E VELOCIDADES ====================

def _menu_config_vozes(session):
      """Lista vozes disponiveis para o amigo escolher (vozes pt-BR de melhor qualidade)."""
      # Vozes de melhor qualidade: 3 do AWS Polly + 3 do Azure
      vozes = [
          "Camila, feminina, a mais natural e fluida, AWS Polly",
          "Vitoria, feminina, muito natural e suave, AWS Polly",
          "Thiago, masculino, natural e claro, AWS Polly",
          "Francisca, feminina jovem, expressiva e natural, Azure",
          "Thalita, feminina, suave e delicada, Azure",
          "Antonio, masculino, claro e articulado, Azure",
      ]
      partes = [f"{i} para {v}" for i, v in enumerate(vozes, 1)]
      texto = (
          "Escolher Voz de Hoje. "
          f"Ha {len(vozes)} opcoes de voz brasileira de qualidade. {'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
      )
      return _resp(texto, end=False, reprompt="Diga o numero da voz.",
                    session={**session, "nivel": "submenu", "menu_tipo": "config_vozes"})


def _menu_config_velocidades(session):
      """Lista velocidades de fala disponiveis."""
      velocidades = ["Muito Devagar", "Devagar", "Normal", "Rapido", "Muito Rapido"]
      partes = [f"{i} para {v}" for i, v in enumerate(velocidades, 1)]
      texto = (
          "Velocidade da Fala. "
          f"Ha {len(velocidades)} opcoes. {'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
      )
      return _resp(texto, end=False, reprompt="Diga o numero da velocidade.",
                    session={**session, "nivel": "submenu", "menu_tipo": "config_velocidades"})


# ==================== MENU [3]: FAVORITOS ====================

def _menu_favoritos(session):
      """Lista sublistas de favoritos. Amigo escolhe → ve itens → pode remover."""
      sublistas = [
          "Salvos para Escutar Mais Tarde",
          "Noticias e Artigos Favoritados",
          "Emails Favoritados",
          "Documentos Importantes",
      ]
      partes = [f"{i} para {s}" for i, s in enumerate(sublistas, 1)]
      texto = (
          f"Favoritos Importantes. "
          f"Voce tem {len(sublistas)} categorias. {', '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar ao menu principal. "
          "Qual numero?"
      )
      new_session = {
          **session,
          "nivel":      "submenu",
          "menu_tipo":  "favoritos",
          "sublistas":  json.dumps(sublistas),
      }
      return _resp(texto, end=False, reprompt="Diga o numero.", session=new_session)


# ==================== MENU [5]: CALENDARIO ====================

def _menu_calendario(session):
      """Lista compromissos numerados. Amigo escolhe → ouve detalhes → pode editar."""
      compromissos = _buscar_compromissos()

      if not compromissos:
          return _resp(
              "Calendario. Voce nao tem compromissos agendados. "
              "Diga outro numero ou diga voltar.",
              end=False, session=session)

      # Ordena: mais proximo primeiro
      compromissos = _ordenar_compromissos(compromissos)
      partes = []
      for i, c in enumerate(compromissos, 1):
          partes.append(f"{i}: {c.get('titulo', '?')}, dia {c.get('data', '?')} as {c.get('hora', '?')}")

      texto = (
          f"Calendario e Compromissos. "
          f"Voce tem {len(compromissos)} compromisso{'s' if len(compromissos) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual compromisso quer ver?"
      )
      new_session = {
          **session,
          "nivel":          "submenu",
          "menu_tipo":      "calendario",
          "compromissos":   json.dumps(compromissos),
      }
      return _resp(texto, end=False, reprompt="Diga o numero do compromisso.", session=new_session)


# ==================== MENU [8]: REUNIOES ====================

def _menu_reunioes(session):
      """Lista reunioes numeradas (recente → antiga). Amigo escolhe → modo de escuta."""
      reunioes = _buscar_reunioes()

      if not reunioes:
          return _resp(
              "Reunioes Caxinguele. Nenhuma reuniao registrada ainda. "
              "Diga outro numero ou diga voltar.",
              end=False, session=session)

      # Ordena: mais recente primeiro
      reunioes = _ordenar_reunioes(reunioes)
      partes = []
      for i, r in enumerate(reunioes, 1):
          # Formato: "Reuniao do dia DD/MM/YYYY" — usa data se disponivel, titulo como fallback
          data = r.get('data', '')
          titulo = r.get('titulo', '')
          if data:
              descricao = f"Reuniao do dia {data}"
          elif titulo:
              descricao = titulo
          else:
              descricao = f"Reuniao {i}"
          partes.append(f"{i}. {descricao}")

      texto = (
          f"Reunioes Caxinguele. "
          f"Voce tem {len(reunioes)} reunia{'o' if len(reunioes) == 1 else 'oes'} registrada{'s' if len(reunioes) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual reuniao quer ouvir?"
      )
      new_session = {
          **session,
          "nivel":     "submenu",
          "menu_tipo": "reunioes",
          "reunioes":  json.dumps(reunioes),
      }
      return _resp(texto, end=False, reprompt="Diga o numero da reuniao.", session=new_session)


# ==================== MENU [10]: LISTAS MENTAIS ====================

def _menu_listas(session):
      """Lista as listas do amigo. Escolhe → itens → pode editar/remover."""
      listas = _buscar_listas()

      if not listas:
          return _resp(
              "Organizacoes da Mente em Listas. Voce nao tem listas ainda. "
              "Diga outro numero ou diga voltar.",
              end=False, session=session)

      nomes = list(listas.keys())
      partes = []
      for i, nome in enumerate(nomes, 1):
          qtd = len(listas[nome])
          partes.append(f"{i}: {nome}, com {qtd} ite{'m' if qtd == 1 else 'ns'}")

      texto = (
          f"Organizacoes da Mente em Listas. "
          f"Voce tem {len(nomes)} lista{'s' if len(nomes) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual lista?"
      )
      new_session = {
          **session,
          "nivel":       "submenu",
          "menu_tipo":   "listas",
          "listas":      json.dumps(listas),
          "nomes_listas": json.dumps(nomes),
      }
      return _resp(texto, end=False, reprompt="Diga o numero da lista.", session=new_session)


# ==================== NIVEL: SUBMENU ====================

def _selecionar_submenu(numero, session):
      """Amigo escolheu uma opcao dentro de um menu."""
      menu_tipo = session.get("menu_tipo", "")
      logger.info(f"_selecionar_submenu: numero={numero} | menu_tipo='{menu_tipo}' | nivel={session.get('nivel', '?')} | keys={list(session.keys())}")

      # ---------- Musicas: amigo escolheu musica ----------
      if menu_tipo == "musicas":
          musicas = _obter_json(session, "musicas") or []
          if numero == NUM_REPETIR:
              return _menu_musicas(session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          musica = next((m for m in musicas if m.get("numero") == numero), None)
          if not musica:
              return _resp(
                  f"Numero invalido. Diga um numero entre 1 e {len(musicas)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          url = musica.get("url", "")
          titulo = musica.get("titulo", f"Musica {numero}")
          if url:
              _registrar_uso(titulo, "play_musica")
              # Encontra o indice na lista de musicas com URL (playlist)
              musicas_com_url = [m for m in musicas if m.get("url")]
              idx = next((i for i, m in enumerate(musicas_com_url) if m.get("numero") == numero), 0)
              token = f"MUSICA{TOKEN_SEPARADOR}{idx}"
              new_session = {**session, "musica_atual": str(idx)}
              return _build_audio(titulo, url, token=token, session_extra=new_session)
          return _resp(f"{titulo} ainda nao disponivel. Diga outro numero.", end=False, session=session)

      # ---------- Livros categorias: amigo escolheu categoria → lista livros ----------
      if menu_tipo == "livros_categorias":
          if numero == NUM_REPETIR:
              return _menu_livros_categorias(session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          cat = next((c for c in LIVROS_CATEGORIAS if c["numero"] == numero), None)
          if not cat:
              return _resp(
                  f"Numero invalido. Escolha entre 1 e {len(LIVROS_CATEGORIAS)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          cat_nome = cat["nome"]
          filtro_sub = cat.get("filtro_subcategoria", "")
          todos_docs = _obter_json(session, "todos_docs") or []
          docs_livros = [
              d for d in todos_docs
              if d.get("subcategoria", "") == filtro_sub
              or d.get("categoria", "") == filtro_sub  # compatibilidade retroativa
          ]
          return _menu_livros(docs_livros, session, categoria_nome=cat_nome)

      # ---------- Livros: amigo escolheu qual livro → mostra opcoes ----------
      if menu_tipo == "livros":
          livros = _obter_json(session, "livros_dados") or []
          if numero == NUM_REPETIR:
              # Remonta lista de livros a partir dos docs originais
              categoria_nome = session.get("livros_categoria", "")
              todos_docs = _obter_json(session, "todos_docs") or []
              cat_info = next((c for c in LIVROS_CATEGORIAS if c["nome"] == categoria_nome), None)
              filtro_sub = cat_info["filtro_subcategoria"] if cat_info else "Livros: Geral"
              docs_livros = [d for d in todos_docs if d.get("subcategoria","") == filtro_sub or d.get("categoria","") == filtro_sub]
              return _menu_livros(docs_livros, session, categoria_nome=categoria_nome)
          if numero == NUM_VOLTAR:
              return _menu_livros_categorias(session)
          if not (1 <= numero <= len(livros)):
              return _resp(
                  f"Numero invalido. Ha {len(livros)} livros. Diga um numero entre 1 e {len(livros)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)

          livro = livros[numero - 1]
          titulo_livro = livro["titulo"]
          capitulos = livro.get("capitulos", [])
          livro_base = livro.get("livro_base", titulo_livro)
          n_caps = livro["total_capitulos"]

          # Verifica progresso salvo no DynamoDB
          progresso = _obter_json(session, "progresso") or {}
          cap_salvo = progresso.get(livro_base, None)
          opcao_continuar = ""
          if cap_salvo is not None and cap_salvo > 0:
              opcao_continuar = f"2 para Continuar do Capitulo {cap_salvo + 1}. "

          texto = (
              f"{titulo_livro}. {n_caps} capitulo{'s' if n_caps > 1 else ''}. "
              "1 para Comecar do Inicio. "
              f"{opcao_continuar}"
              "3 para Escolher Capitulo. "
              "4 para Sinopse. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":           "item",
              "menu_tipo":       "livros",
              "livro_base":      livro_base,
              "livro_titulo":    titulo_livro,
              "capitulos_livro": json.dumps(capitulos),
              "capitulo_atual":  str(cap_salvo if cap_salvo is not None else 0),
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Livros capitulos: amigo escolheu capitulo especifico ----------
      if menu_tipo == "livros_capitulos":
          capitulos = _obter_json(session, "capitulos_livro") or []
          livro_base = session.get("livro_base", "")
          titulo_livro = session.get("livro_titulo", "Livro")
          user_id = session.get("user_id", "")
          if numero == NUM_REPETIR:
              partes = [f"{i}. {_titulo_curto(c.get('titulo', f'Cap {i}'))}" for i, c in enumerate(capitulos, 1)]
              return _resp(
                  f"{titulo_livro}. {'. '.join(partes)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _resp(
                  f"{titulo_livro}. 1 para Comecar do Inicio. 3 para Escolher Capitulo. 4 para Sinopse. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "item", "menu_tipo": "livros"})
          if not (1 <= numero <= len(capitulos)):
              return _resp(
                  f"Numero invalido. Ha {len(capitulos)} capitulos. Diga um numero entre 1 e {len(capitulos)}.",
                  end=False, session=session)
          cap_idx = numero - 1
          cap = capitulos[cap_idx]
          url = cap.get("url_audio", "")
          cap_titulo = _titulo_curto(cap.get("titulo", f"Capitulo {numero}"))
          if url:
              token = f"{livro_base}{TOKEN_SEPARADOR}{cap_idx}"
              new_session = {**session, "capitulo_atual": str(cap_idx)}
              _registrar_uso(cap_titulo, "play_livro_capitulo")
              return _build_audio(cap_titulo, url, token=token, session_extra=new_session)
          return _resp(f"Capitulo {numero} sem audio disponivel.", end=False, session=session)

      # ---------- Calendario: amigo escolheu compromisso ----------
      if menu_tipo == "calendario":
          compromissos = _obter_json(session, "compromissos") or []
          if not (1 <= numero <= len(compromissos)):
              return _resp(
                  f"Numero invalido. Ha {len(compromissos)} compromissos. Qual?",
                  end=False, session=session)
          comp = compromissos[numero - 1]
          texto = (
              f"Compromisso {numero}: {comp.get('titulo', '?')}. "
              f"Data: {comp.get('data', '?')}. Hora: {comp.get('hora', '?')}. "
              f"Descricao: {comp.get('descricao', 'sem descricao')}. "
              f"O que quer fazer? "
              f"1 para editar este compromisso. "
              f"2 para remover este compromisso. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":          "item",
              "menu_tipo":      "calendario",
              "item_idx":       str(numero - 1),
              "item_dados":     json.dumps(comp),
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Reunioes: amigo escolheu reuniao → modo de escuta ----------
      if menu_tipo == "reunioes":
          reunioes = _obter_json(session, "reunioes") or []
          if numero == NUM_REPETIR:
              return _menu_reunioes(session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          if not (1 <= numero <= len(reunioes)):
              return _resp(
                  f"Numero invalido. Ha {len(reunioes)} reunioes. Diga um numero entre 1 e {len(reunioes)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          reu = reunioes[numero - 1]
          data_reu = reu.get('data', '')
          titulo_reu = reu.get('titulo', f'Reuniao {numero}')
          nome_reu = f"Reuniao do dia {data_reu}" if data_reu else titulo_reu
          texto = (
              f"{nome_reu}. Como quer ouvir? "
              "1 para Resumo em Topicos Frasais. "
              "2 para Resumo Pragmatico. "
              "3 para Audio na Integra. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":      "item",
              "menu_tipo":  "reunioes",
              "item_idx":   str(numero - 1),
              "item_dados": json.dumps(reu),
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Favoritos: amigo escolheu sublista → lista itens ----------
      if menu_tipo == "favoritos":
          sublistas = _obter_json(session, "sublistas") or []
          if not (1 <= numero <= len(sublistas)):
              return _resp(f"Numero invalido. Ha {len(sublistas)} categorias. Qual?",
                            end=False, session=session)
          sublista_nome = sublistas[numero - 1]
          favoritos = _buscar_favoritos()
          itens = favoritos.get(sublista_nome, [])
          if not itens:
              return _resp(
                  f"{sublista_nome}. Nenhum item favoritado nesta categoria. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          partes = [f"{i}: {it.get('titulo', '?')}" for i, it in enumerate(itens, 1)]
          texto = (
              f"{sublista_nome}. {len(itens)} ite{'m' if len(itens) == 1 else 'ns'}. "
              f"{'. '.join(partes)}. "
              f"Diga o numero para ouvir detalhes e remover se quiser. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":           "submenu",
              "menu_tipo":       "favoritos_itens",
              "sublista_nome":   sublista_nome,
              "itens_favoritos": json.dumps(itens),
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Favoritos itens: amigo escolheu item especifico ----------
      if menu_tipo == "favoritos_itens":
          itens = _obter_json(session, "itens_favoritos") or []
          if not (1 <= numero <= len(itens)):
              return _resp(f"Numero invalido. Ha {len(itens)} itens. Qual?",
                            end=False, session=session)
          item = itens[numero - 1]
          sublista_nome = session.get("sublista_nome", "")
          texto = (
              f"Item {numero}: {item.get('titulo', '?')}. "
              f"Favoritado em {item.get('favoritado_em', '?')}. "
              f"1 para remover este item dos favoritos. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":         "item",
              "menu_tipo":     "favoritos_item",
              "item_idx":      str(numero - 1),
              "item_dados":    json.dumps(item),
              "sublista_nome": sublista_nome,
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Listas: amigo escolheu lista → itens ----------
      if menu_tipo == "listas":
          nomes = _obter_json(session, "nomes_listas") or []
          listas = _obter_json(session, "listas") or {}
          if not (1 <= numero <= len(nomes)):
              return _resp(f"Numero invalido. Ha {len(nomes)} listas. Qual?",
                            end=False, session=session)
          nome_lista = nomes[numero - 1]
          itens = listas.get(nome_lista, [])
          if not itens:
              return _resp(f"{nome_lista}. Lista vazia. {NUM_VOLTAR} para voltar.",
                            end=False, session=session)
          partes = [f"{i}: {it.get('conteudo', '?')}" for i, it in enumerate(itens, 1)]
          texto = (
              f"Lista {nome_lista}. {len(itens)} ite{'m' if len(itens) == 1 else 'ns'}. "
              f"{'. '.join(partes)}. "
              f"Diga o numero para ouvir e editar. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":        "submenu",
              "menu_tipo":    "listas_itens",
              "nome_lista":   nome_lista,
              "itens_lista":  json.dumps(itens),
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Listas itens: amigo escolheu item ----------
      if menu_tipo == "listas_itens":
          itens = _obter_json(session, "itens_lista") or []
          if not (1 <= numero <= len(itens)):
              return _resp(f"Numero invalido. Ha {len(itens)} itens. Qual?",
                            end=False, session=session)
          item = itens[numero - 1]
          nome_lista = session.get("nome_lista", "")
          texto = (
              f"Item {numero}: {item.get('conteudo', '?')}. "
              f"Adicionado em {item.get('adicionado_em', '?')}. "
              f"1 para remover este item. "
              f"2 para editar o conteudo. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":       "item",
              "menu_tipo":   "listas_item",
              "item_idx":    str(numero - 1),
              "item_dados":  json.dumps(item),
              "nome_lista":  nome_lista,
          }
          return _resp(texto, end=False, session=new_session)

      # ---------- Documentos (menus filtro): amigo escolheu doc ----------
      if menu_tipo == "documentos":
          docs = _obter_json(session, "docs_filtrados") or []
          if not (1 <= numero <= len(docs)):
              return _resp(f"Numero invalido. Ha {len(docs)} documentos. Qual?",
                            end=False, session=session)
          doc = docs[numero - 1]
          titulo = _titulo_curto(doc.get("titulo", "Sem titulo"))
          url = doc.get("url_audio", "")
          if url:
              _registrar_uso(titulo, "play")
              return _build_audio(titulo, url)
          return _resp(f"{titulo} nao tem audio disponivel.", end=True)

      # ---------- Configuracoes: submenu principal ----------
      if menu_tipo == "configuracoes":
          if numero == NUM_REPETIR:
              return _resp(
                  "Configuracoes. 1 para Velocidade da Fala. 2 para Guia do Usuario. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _voltar_nivel_anterior(session)
          if numero == 1:
              return _menu_config_velocidades(session)
          if numero == 2:
              return _resp(
                  "Guia do Usuario. Voce pode ouvir o menu de ajuda dizendo: Alexa, pede ajuda na super alexa. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          return _resp("Opcao invalida. 1 para Velocidade. 2 para Guia.",
                        end=False, session=session)

      # ---------- Configuracoes: escolher velocidade ----------
      if menu_tipo == "config_velocidades":
          if numero == NUM_REPETIR:
              return _menu_config_velocidades(session)
          if numero == NUM_VOLTAR:
              return _resp(
                  "Configuracoes. 1 para Velocidade da Fala. 2 para Guia do Usuario. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          velocidades_nomes  = ["Muito Devagar", "Devagar", "Normal", "Rapido", "Muito Rapido"]
          velocidades_chaves = ["muito_devagar", "devagar", "normal", "rapido", "muito_rapido"]
          if not (1 <= numero <= len(velocidades_nomes)):
              return _resp(f"Opcao invalida. Escolha entre 1 e {len(velocidades_nomes)}.",
                            end=False, session=session)
          vel_nome  = velocidades_nomes[numero - 1]
          vel_chave = velocidades_chaves[numero - 1]
          # Salva velocidade na sessao: _resp vai usar SSML automaticamente
          new_session = {**session, "nivel": "submenu", "menu_tipo": "configuracoes", "velocidade": vel_chave}
          return _resp(
              f"Velocidade {vel_nome} ativada para esta sessao. "
              "Os menus e textos serao falados nessa velocidade. "
              "Para audiobooks gravados (MP3), a velocidade nao pode ser alterada em tempo real. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session=new_session)

      # ---------- YouTube: submenu principal ----------
      if menu_tipo == "youtube":
          if numero == NUM_REPETIR:
              return _menu_youtube(session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          if numero == 1:
              # Ultimas atualizacoes dos canais salvos
              user_id = session.get("user_id", "")
              canais = _get_canais_youtube(user_id)
              if not canais:
                  return _resp(
                      "Voce ainda nao tem canais salvos. "
                      "Diga 3 para gerenciar seus canais. "
                      f"{NUM_VOLTAR} para voltar.",
                      end=False, session=session)
              todos_videos = []
              for canal in canais:
                  videos = _buscar_videos_canal_rss(canal.get("channel_id", ""), max_videos=3)
                  todos_videos.extend(videos)
              # Ordena por data (mais recente primeiro)
              todos_videos.sort(key=lambda v: v.get("data", ""), reverse=True)
              todos_videos = todos_videos[:10]
              if not todos_videos:
                  return _resp(
                      "Nenhum video recente encontrado nos seus canais. "
                      f"{NUM_VOLTAR} para voltar.",
                      end=False, session=session)
              partes = []
              for i, v in enumerate(todos_videos, 1):
                  partes.append(f"{i}. {v['titulo']}, do canal {v.get('canal', 'desconhecido')}")
              texto = (
                  f"Ultimas atualizacoes. {len(todos_videos)} videos. "
                  f"{'. '.join(partes)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
                  "Diga o numero do video."
              )
              new_session = {
                  **session,
                  "nivel": "submenu",
                  "menu_tipo": "youtube_canal",
                  "youtube_videos": json.dumps(todos_videos),
              }
              return _resp(texto, end=False, reprompt="Diga o numero do video.", session=new_session)

          if numero == 2:
              # Pesquisar no YouTube — pedir o termo de busca
              return _resp(
                  "O que voce quer pesquisar no YouTube? "
                  "Diga por exemplo: ver videos de meditacao, "
                  "canal de culinaria, ou tutorial de violao.",
                  end=False,
                  reprompt="Diga o que quer pesquisar. Por exemplo: ver videos de meditacao.",
                  session={**session, "nivel": "submenu", "menu_tipo": "youtube_busca_aguardando"})

          if numero == 3:
              # Gerenciar canais
              return _menu_youtube_canais(session)

          return _resp(
              f"Opcao invalida. 1 atualizacoes, 2 pesquisar, 3 canais. "
              f"{NUM_REPETIR} repetir. {NUM_VOLTAR} voltar.",
              end=False, session=session)

      # ---------- YouTube: aguardando termo de busca por voz ----------
      if menu_tipo == "youtube_busca_aguardando":
          if numero == NUM_VOLTAR:
              return _menu_youtube(session)
          # Usuário disse um número quando deveria dizer o termo de busca
          return _resp(
              "Nao entendi. Para pesquisar, diga por exemplo: "
              "ver videos de meditacao, ou canal de culinaria, ou tutorial de violao. "
              f"{NUM_VOLTAR} para voltar.",
              end=False,
              reprompt="Diga o que quer pesquisar. Por exemplo: ver videos de meditacao.",
              session=session)

      # ---------- YouTube: lista de videos (de canal ou busca) ----------
      if menu_tipo in ("youtube_canal", "youtube_busca"):
          if numero == NUM_REPETIR:
              videos = _obter_json(session, "youtube_videos") or []
              partes = []
              for i, v in enumerate(videos, 1):
                  partes.append(f"{i}. {v['titulo']}")
              texto = (
                  f"{len(videos)} videos. {'. '.join(partes)}. "
                  f"{NUM_REPETIR} repetir. {NUM_VOLTAR} voltar."
              )
              return _resp(texto, end=False, reprompt="Diga o numero.", session=session)
          if numero == NUM_VOLTAR:
              return _menu_youtube(session)
          videos = _obter_json(session, "youtube_videos") or []
          if not (1 <= numero <= len(videos)):
              return _resp(
                  f"Numero invalido. Escolha entre 1 e {len(videos)}.",
                  end=False, session=session)
          video = videos[numero - 1]
          titulo_v = video.get("titulo", "video")
          canal_v = video.get("canal", "")
          duracao_v = video.get("duracao", "")
          dur_txt = f" Duracao: {duracao_v}." if duracao_v else ""
          canal_txt = f" Canal: {canal_v}." if canal_v else ""
          texto = (
              f"{titulo_v}.{canal_txt}{dur_txt} "
              "1 para ouvir resumo do video. "
              "2 para enviar link no WhatsApp. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel": "submenu",
              "menu_tipo": "youtube_video",
              "youtube_video_atual": json.dumps(video),
              "youtube_parent_tipo": menu_tipo,  # salva de onde veio (canal ou busca)
          }
          return _resp(texto, end=False, reprompt="Diga uma opcao.", session=new_session)

      # ---------- YouTube: opcoes de um video (resumo ou link) ----------
      if menu_tipo == "youtube_video":
          if numero == NUM_REPETIR:
              video = _obter_json(session, "youtube_video_atual") or {}
              return _resp(
                  f"{video.get('titulo', 'video')}. 1 resumo. 2 enviar link. "
                  f"{NUM_REPETIR} repetir. {NUM_VOLTAR} voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              # Volta para lista de videos
              parent = session.get("youtube_parent_tipo", "youtube_canal")
              return _resp(
                  "Voltando para a lista de videos. Diga o numero do video.",
                  end=False,
                  session={**session, "nivel": "submenu", "menu_tipo": parent})
          video = _obter_json(session, "youtube_video_atual") or {}
          if numero == 1:
              # Resumo do video
              video_id = video.get("video_id", "")
              resumo = _resumir_video_youtube(video_id)
              return _resp(
                  f"Resumo de {video.get('titulo', 'video')}. {resumo} "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == 2:
              # Enviar link no WhatsApp
              url_video = video.get("url", "")
              titulo_v = video.get("titulo", "")
              mensagem = f"Video do YouTube: {titulo_v}\n{url_video}"
              sucesso = _enviar_whatsapp(mensagem)
              if sucesso:
                  return _resp(
                      f"Link de {titulo_v} enviado no WhatsApp. "
                      f"{NUM_VOLTAR} para voltar.",
                      end=False, session=session)
              else:
                  return _resp(
                      "Nao foi possivel enviar. Verifique as configuracoes do WhatsApp. "
                      f"{NUM_VOLTAR} para voltar.",
                      end=False, session=session)
          return _resp("1 resumo. 2 enviar link.", end=False, session=session)

      # ---------- YouTube: gerenciar canais ----------
      if menu_tipo == "youtube_canais":
          if numero == NUM_REPETIR:
              return _menu_youtube_canais(session)
          if numero == NUM_VOLTAR:
              return _menu_youtube(session)
          user_id = session.get("user_id", "")

          if numero == 1:
              # Ver meus canais
              canais = _get_canais_youtube(user_id)
              if not canais:
                  return _resp(
                      "Voce nao tem canais salvos. Diga 2 para adicionar um canal. "
                      f"{NUM_VOLTAR} para voltar.",
                      end=False, session=session)
              partes = [f"{i}. {c.get('nome', 'canal')}" for i, c in enumerate(canais, 1)]
              return _resp(
                  f"Seus canais: {'. '.join(partes)}. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)

          if numero == 2:
              # Adicionar canal — pedir nome
              return _resp(
                  "Diga o nome do canal que deseja adicionar.",
                  end=False,
                  session={**session, "nivel": "submenu", "menu_tipo": "youtube_canais_adicionar"})

          if numero == 3:
              # Remover canal — listar e pedir numero
              canais = _get_canais_youtube(user_id)
              if not canais:
                  return _resp("Voce nao tem canais para remover.", end=False, session=session)
              partes = [f"{i}. {c.get('nome', 'canal')}" for i, c in enumerate(canais, 1)]
              return _resp(
                  f"Qual canal remover? {'. '.join(partes)}. Diga o numero.",
                  end=False,
                  session={**session, "nivel": "submenu", "menu_tipo": "youtube_canais_remover",
                           "youtube_canais_lista": json.dumps(canais)})

          return _resp("1 ver canais. 2 adicionar. 3 remover.", end=False, session=session)

      # ---------- YouTube: remover canal por numero ----------
      if menu_tipo == "youtube_canais_remover":
          if numero == NUM_VOLTAR:
              return _menu_youtube_canais(session)
          canais = _obter_json(session, "youtube_canais_lista") or []
          user_id = session.get("user_id", "")
          if not (1 <= numero <= len(canais)):
              return _resp(f"Numero invalido. Escolha entre 1 e {len(canais)}.", end=False, session=session)
          removido = canais.pop(numero - 1)
          _salvar_canais_youtube(user_id, canais)
          return _resp(
              f"Canal {removido.get('nome', '')} removido. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session={**session, "menu_tipo": "youtube_canais"})

      # ---------- Playback pausado: menu de opcoes apos dizer "pare" ----------
      if menu_tipo == "playback_pausado":
          if numero == NUM_REPETIR:
              livro_titulo = session.get("livro_titulo_pausado", "")
              cap_num = int(session.get("capitulo_pausado", "0")) + 1
              texto_livro = f"{livro_titulo}, capitulo {cap_num}. " if livro_titulo else ""
              texto = (
                  f"{texto_livro}"
                  "1 para pular capitulo. "
                  "2 para voltar capitulo. "
                  "3 para velocidade. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para menu principal."
              )
              return _resp(texto, end=False, reprompt="Diga uma opcao.", session=session)

          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)

          if numero == 3:  # Velocidade
              return _menu_config_velocidades(session)

          if numero in (1, 2):  # Pular ou voltar capitulo
              token = session.get("audio_token", "")
              if TOKEN_SEPARADOR in token:
                  partes_token = token.split(TOKEN_SEPARADOR)
                  livro_base_token = partes_token[0]
                  try:
                      cap_idx = int(partes_token[1])
                  except Exception:
                      cap_idx = 0
                  # Busca dados completos do livro no GitHub Pages
                  todos_docs = _obter_json(session, "todos_docs") or []
                  if not todos_docs:
                      docs_completos, _ = _buscar_dados_completos()
                      todos_docs = docs_completos
                      if todos_docs:
                          session = {**session, "todos_docs": json.dumps(todos_docs)}
                  caps = [d for d in todos_docs if _extrair_livro_base(d.get("titulo","")) == livro_base_token]
                  caps.sort(key=lambda d: _extrair_num_capitulo(d.get("titulo","")))

                  session_reconstituida = {
                      **session,
                      "livro_base": livro_base_token,
                      "livro_titulo": livro_base_token,
                      "capitulos_livro": json.dumps(caps),
                      "capitulo_atual": str(cap_idx),
                      "nivel": "item",
                      "menu_tipo": "livros",
                  }
                  direcao = +1 if numero == 1 else -1
                  return _pular_capitulo_sessao(session_reconstituida, direcao=direcao)
              else:
                  return _resp(
                      "Nao foi possivel identificar o livro. Abra o menu principal e escolha o livro novamente.",
                      end=False, session={**session, "nivel": "menu", "menu_tipo": "principal"})

          return _resp(
              f"Opcao invalida. 1 pular, 2 voltar, 3 velocidade, {NUM_REPETIR} repetir, {NUM_VOLTAR} menu principal.",
              end=False, reprompt="Diga uma opcao.", session=session)

      # Fallback
      return _resp("Nao entendi. Diga o numero ou diga voltar.",
                    end=False, session=session)


# ==================== NIVEL: ITEM (ACOES) ====================

def _selecionar_acao_item(numero, session):
      """Amigo esta vendo detalhes de um item e escolheu uma acao."""
      menu_tipo = session.get("menu_tipo", "")

      # ---------- Livros: amigo escolheu acao (comecar, continuar, escolher cap, sinopse) ----------
      if menu_tipo == "livros":
          titulo = session.get("livro_titulo", "?")
          livro_base = session.get("livro_base", "")
          capitulos = _obter_json(session, "capitulos_livro") or []
          user_id = session.get("user_id", "")
          progresso = _obter_json(session, "progresso") or {}
          cap_salvo = progresso.get(livro_base, None)

          if numero == NUM_REPETIR:
              opcao_continuar = f"2 para Continuar do Capitulo {cap_salvo + 1}. " if cap_salvo else ""
              return _resp(
                  f"{titulo}. 1 para Comecar do Inicio. {opcao_continuar}"
                  "3 para Escolher Capitulo. 4 para Sinopse. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)

          if numero == NUM_VOLTAR:
              # Volta para lista de livros da mesma categoria
              categoria_nome = session.get("livros_categoria", "")
              todos_docs = _obter_json(session, "todos_docs") or []
              cat_info = next((c for c in LIVROS_CATEGORIAS if c["nome"] == categoria_nome), None)
              filtro_sub = cat_info["filtro_subcategoria"] if cat_info else "Livros: Geral"
              docs_livros = [d for d in todos_docs if d.get("subcategoria","") == filtro_sub or d.get("categoria","") == filtro_sub]
              return _menu_livros(docs_livros, session, categoria_nome=categoria_nome)

          if numero == 1:
              # Comecar do capitulo 1
              if capitulos:
                  cap = capitulos[0]
                  url = cap.get("url_audio", "")
                  cap_titulo = _titulo_curto(cap.get("titulo", "Capitulo 1"))
                  if url:
                      _registrar_uso(titulo, "play_livro_inicio")
                      token = f"{livro_base}{TOKEN_SEPARADOR}0"
                      new_session = {**session, "capitulo_atual": "0"}
                      return _build_audio(cap_titulo, url, token=token, session_extra=new_session)
              return _resp(f"{titulo} nao tem audio disponivel.", end=False, session=session)

          if numero == 2:
              # Continuar do capitulo salvo
              if cap_salvo is not None and capitulos and cap_salvo < len(capitulos):
                  cap = capitulos[cap_salvo]
                  url = cap.get("url_audio", "")
                  cap_titulo = _titulo_curto(cap.get("titulo", f"Capitulo {cap_salvo + 1}"))
                  if url:
                      _registrar_uso(titulo, "play_livro_continuar")
                      token = f"{livro_base}{TOKEN_SEPARADOR}{cap_salvo}"
                      new_session = {**session, "capitulo_atual": str(cap_salvo)}
                      return _build_audio(cap_titulo, url, token=token, session_extra=new_session)
              return _resp(
                  f"Nenhum progresso salvo para {titulo}. Diga 1 para comecar do inicio. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)

          if numero == 3:
              # Listar capitulos para escolher
              partes = []
              for i, cap in enumerate(capitulos, 1):
                  partes.append(f"{i}. {_titulo_curto(cap.get('titulo', f'Capitulo {i}'))}")
              texto = (
                  f"{titulo}. {len(capitulos)} capitulos. "
                  f"{'. '.join(partes)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
                  "Qual capitulo quer ouvir?"
              )
              return _resp(texto, end=False,
                            session={**session, "nivel": "submenu", "menu_tipo": "livros_capitulos"})

          if numero == 4:
              # Sinopse do livro (campo 'sinopse' ou sinopse automática)
              n_caps = len(capitulos)
              data_raw = capitulos[0].get("data", "") if capitulos else ""
              data_txt = ""
              if data_raw:
                  try:
                      dt = datetime.strptime(data_raw, "%Y-%m-%d")
                      meses = ["janeiro","fevereiro","marco","abril","maio","junho",
                               "julho","agosto","setembro","outubro","novembro","dezembro"]
                      data_txt = f", adicionado em {meses[dt.month-1]} de {dt.year}"
                  except Exception:
                      data_txt = f", adicionado em {data_raw}"
              if capitulos:
                  sinopse = capitulos[0].get(
                      "sinopse",
                      f"{n_caps} capitulo{'s' if n_caps > 1 else ''}{data_txt}."
                  )
              else:
                  sinopse = "Sinopse nao disponivel."
              return _resp(
                  f"Sinopse de {titulo}. {sinopse}. "
                  "1 para Comecar a Ler. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)

          return _resp(
              "Opcao invalida. 1 para inicio. 2 para continuar. 3 para capitulos. 4 para sinopse. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session=session)

      # ---------- Calendario: editar ou remover compromisso ----------
      if menu_tipo == "calendario":
          comp = _obter_json(session, "item_dados") or {}
          if numero == 1:
              # Editar: pergunta qual campo
              texto = (
                  f"Editar compromisso: {comp.get('titulo', '?')}. "
                  f"Qual campo? 1 para titulo. 2 para data. 3 para hora. 4 para descricao. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
              )
              return _resp(texto, end=False,
                            session={**session, "nivel": "editar", "menu_tipo": "calendario_editar"})
          if numero == 2:
              # Remover
              return _resp(
                  f"Compromisso '{comp.get('titulo', '?')}' removido com sucesso. "
                  "Diga outro numero ou diga voltar.",
                  end=False,
                  session={**session, "nivel": "menu", "acao_pendente": "remover_compromisso"})
          return _resp("Opcao invalida. 1 para editar. 2 para remover.",
                        end=False, session=session)

      # ---------- Reunioes: modo de escuta ----------
      if menu_tipo == "reunioes":
          reu = _obter_json(session, "item_dados") or {}
          titulo_reu = reu.get('titulo', '?')
          if numero == NUM_REPETIR:
              return _resp(
                  f"Reuniao: {titulo_reu}. Como quer ouvir? "
                  "1 para Resumo em Topicos Frasais. "
                  "2 para Resumo Pragmatico. "
                  "3 para Audio na Integra. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _menu_reunioes(session)
          if numero == 1:
              resumo = reu.get("resumo", "Sem resumo disponivel.")
              return _resp(
                  f"Resumo em topicos frasais da reuniao {titulo_reu}. {resumo}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "item", "menu_tipo": "reunioes"})
          if numero == 2:
              resumo = reu.get("resumo", "Sem resumo disponivel.")
              return _resp(
                  f"Resumo pragmatico da reuniao {titulo_reu}. {resumo}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "item", "menu_tipo": "reunioes"})
          if numero == 3:
              transcricao = reu.get("transcricao", "")
              if transcricao:
                  return _resp(
                      f"Audio na integra da reuniao {titulo_reu}. {transcricao[:3000]}. "
                      f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                      end=False, session={**session, "nivel": "item", "menu_tipo": "reunioes"})
              return _resp(
                  f"Transcricao nao disponivel para {titulo_reu}. "
                  "1 para topicos frasais. 2 para resumo pragmatico. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          return _resp(
              "Opcao invalida. 1 para topicos frasais. 2 para resumo pragmatico. 3 para audio na integra. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
              end=False, session=session)

      # ---------- Favoritos: remover ----------
      if menu_tipo == "favoritos_item":
          if numero == 1:
              item = _obter_json(session, "item_dados") or {}
              return _resp(
                  f"Item '{item.get('titulo', '?')}' removido dos favoritos. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False,
                  session={**session, "nivel": "menu", "acao_pendente": "remover_favorito"})
          return _resp("1 para remover. " + f"{NUM_VOLTAR} para voltar.",
                        end=False, session=session)

      # ---------- Listas: remover ou editar ----------
      if menu_tipo == "listas_item":
          if numero == 1:
              item = _obter_json(session, "item_dados") or {}
              return _resp(
                  f"Item '{item.get('conteudo', '?')}' removido da lista. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False,
                  session={**session, "nivel": "menu", "acao_pendente": "remover_lista_item"})
          if numero == 2:
              return _resp(
                  "Para editar um item, use o aplicativo no celular por enquanto. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "menu"})
          return _resp("1 para remover. 2 para editar.", end=False, session=session)

      # Fallback
      return _resp("Nao entendi. Diga o numero.", end=False, session=session)


# ==================== NIVEL: EDITAR CAMPO ====================

def _selecionar_campo_editar(numero, session):
      """Amigo esta editando um item e escolheu qual campo mudar."""
      menu_tipo = session.get("menu_tipo", "")

      if menu_tipo == "calendario_editar":
          campos = {1: "titulo", 2: "data", 3: "hora", 4: "descricao"}
          campo = campos.get(numero)
          if not campo:
              return _resp("1 titulo. 2 data. 3 hora. 4 descricao.", end=False, session=session)
          # Alexa nao suporta entrada livre de texto facilmente,
          # entao indicamos para usar o app
          return _resp(
              f"Para alterar o {campo} do compromisso, use o aplicativo no celular. "
              "A edicao por voz para texto livre sera adicionada em breve. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session={**session, "nivel": "menu"})

      return _resp("Nao entendi.", end=False, session={**session, "nivel": "menu"})


# ==================== NAVEGACAO ====================

def _repetir_opcoes(session):
      """Repete a ultima listagem baseada no estado atual."""
      nivel = session.get("nivel", "menu")
      menu_tipo = session.get("menu_tipo", "")

      if nivel == "menu" or not menu_tipo:
          return _voltar_menu_principal(session)

      # Re-executa o menu de origem
      if menu_tipo == "livros_categorias":
          return _menu_livros_categorias(session)
      if menu_tipo == "calendario":
          return _menu_calendario(session)
      if menu_tipo == "reunioes":
          return _menu_reunioes(session)
      if menu_tipo == "favoritos":
          return _menu_favoritos(session)
      if menu_tipo == "listas":
          return _menu_listas(session)
      if menu_tipo == "youtube":
          return _menu_youtube(session)
      if menu_tipo == "youtube_canais":
          return _menu_youtube_canais(session)

      return _voltar_menu_principal(session)


def _voltar_menu_principal(session):
      """Volta ao menu principal (nivel 1)."""
      menu = _obter_json(session, "menu") or list(MENU_DEFAULT)
      todos_docs = _obter_json(session, "todos_docs") or []
      texto = _enumerar_menu_principal(menu, todos_docs)
      new_session = {
          "nivel":     "menu",
          "todos_docs": session.get("todos_docs", json.dumps(todos_docs)),
          "menu":       session.get("menu", json.dumps(menu)),
          "user_id":    session.get("user_id", ""),
          "progresso":  session.get("progresso", "{}"),
      }
      if session.get("velocidade"):
          new_session["velocidade"] = session["velocidade"]
      return _resp(texto, end=False, reprompt="Diga o numero.", session=new_session)


# Tabela de navegacao: cada menu_tipo aponta para sua funcao-pai
# None = voltar ao menu principal
_PARENT_MENU = {
    "musicas":             None,
    "livros_categorias":   None,
    "livros":              "livros_categorias",
    "livros_capitulos":    "livros",
    "configuracoes":       None,
    "config_vozes":        "configuracoes",
    "config_velocidades":  "configuracoes",
    "favoritos":           None,
    "favoritos_itens":     "favoritos",
    "favoritos_item":      "favoritos_itens",
    "calendario":          None,
    "reunioes":            None,
    "listas":              None,
    "listas_itens":        "listas",
    "listas_item":         "listas_itens",
    "documentos":          None,
    "playback_pausado":    None,
    "youtube":             None,
    "youtube_canal":       "youtube",
    "youtube_busca":       "youtube",
    "youtube_busca_aguardando": "youtube",
    "youtube_video":       "youtube_canal",
    "youtube_canais":      "youtube",
    "youtube_canais_adicionar": "youtube_canais",
    "youtube_canais_remover":   "youtube_canais",
}

# Funcoes que reconstroem cada menu (usadas pelo voltar hierarquico)
def _reconstruir_menu(menu_tipo, session):
      """Reconstroi o menu do tipo especificado para voltar um nivel."""
      if menu_tipo == "livros_categorias":
          return _menu_livros_categorias(session)
      if menu_tipo == "livros":
          categoria_nome = session.get("livros_categoria", "")
          todos_docs = _obter_json(session, "todos_docs") or []
          cat_info = next((c for c in LIVROS_CATEGORIAS if c["nome"] == categoria_nome), None)
          filtro_sub = cat_info["filtro_subcategoria"] if cat_info else "Livros: Geral"
          docs_livros = [d for d in todos_docs if d.get("subcategoria","") == filtro_sub or d.get("categoria","") == filtro_sub]
          return _menu_livros(docs_livros, session, categoria_nome=categoria_nome)
      if menu_tipo == "musicas":
          return _menu_musicas(session)
      if menu_tipo == "configuracoes":
          return _resp(
              "Configuracoes. 1 para Velocidade da Fala. 2 para Guia do Usuario. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
              end=False,
              session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
      if menu_tipo == "config_velocidades":
          return _menu_config_velocidades(session)
      if menu_tipo == "favoritos":
          return _menu_favoritos(session)
      if menu_tipo == "favoritos_itens":
          sublistas = _obter_json(session, "sublistas") or []
          return _menu_favoritos(session)
      if menu_tipo == "calendario":
          return _menu_calendario(session)
      if menu_tipo == "reunioes":
          return _menu_reunioes(session)
      if menu_tipo == "listas":
          return _menu_listas(session)
      if menu_tipo == "listas_itens":
          return _menu_listas(session)
      if menu_tipo == "youtube":
          return _menu_youtube(session)
      if menu_tipo == "youtube_canais":
          return _menu_youtube_canais(session)
      # Fallback
      return _voltar_menu_principal(session)


def _voltar_nivel_anterior(session):
      """Volta UM nivel na hierarquia de menus (nao direto ao menu principal)."""
      menu_tipo = session.get("menu_tipo", "")
      nivel = session.get("nivel", "menu")

      # Se ja esta no menu principal, nao tem para onde voltar
      if nivel == "menu" or not menu_tipo:
          return _voltar_menu_principal(session)

      # Busca o pai na tabela
      pai = _PARENT_MENU.get(menu_tipo)

      if pai is None:
          # Pai eh o menu principal
          return _voltar_menu_principal(session)
      else:
          # Reconstroi o menu pai
          return _reconstruir_menu(pai, session)


# ==================== HELPERS: LISTAR DOCS ====================

def _listar_docs_como_submenu(docs, nome_cat, session):
      """Lista documentos de uma categoria como submenu numerado."""
      partes = [f"{i}: {_titulo_curto(d.get('titulo', '?'))}" for i, d in enumerate(docs, 1)]
      texto = (
          f"{nome_cat}. {len(docs)} documento{'s' if len(docs) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual numero?"
      )
      new_session = {
          **session,
          "nivel":          "submenu",
          "menu_tipo":      "documentos",
          "docs_filtrados":  json.dumps(docs),
          "categoria_nome":  nome_cat,
      }
      return _resp(texto, end=False, reprompt="Diga o numero.", session=new_session)


# ==================== HELPERS: ATALHOS DE VOZ ====================

def _handle_filtrar_tipo(slots, session):
      tipo = _extrair_texto(slots, "tipo_documento")
      if not tipo:
          return _resp("Que tipo? Livros, artigos, emails ou documentos?",
                        end=False, session=session)
      todos_docs = _obter_json(session, "todos_docs") or []
      mapa = {
          "livro": "Livros", "livros": "Livros",
          "artigo": "Artigos e Noticias", "artigos": "Artigos e Noticias",
          "email": "Emails", "emails": "Emails",
          "documento": "Documentos", "documentos": "Documentos",
      }
      categoria = mapa.get(tipo.lower().strip())
      if not categoria:
          return _resp("Tipo desconhecido. Diga: livros, artigos, emails ou documentos.",
                        end=False, session=session)
      filtrados = [d for d in todos_docs if d.get("categoria", "") == categoria]
      if not filtrados:
          return _resp(f"Nao ha {tipo} no momento.", end=False, session=session)
      return _listar_docs_como_submenu(filtrados, categoria, session)


def _handle_novidades(session):
      todos_docs = _obter_json(session, "todos_docs") or []
      novos = _docs_recentes(todos_docs)
      if not novos:
          return _resp("Nao ha novidades recentes.", end=False, session=session)
      return _listar_docs_como_submenu(novos, "Ultimas Atualizacoes", session)


def _handle_ler_documento(slots, session):
      numero = _extrair_numero(slots, "numero")
      nome = _extrair_texto(slots, "nome_documento")
      todos_docs = _obter_json(session, "todos_docs") or []
      doc = None
      if numero and 1 <= numero <= len(todos_docs):
          doc = todos_docs[numero - 1]
      elif nome:
          doc = _buscar_por_nome(todos_docs, nome)
      if not doc:
          return _resp("Nao encontrei. Diga o numero.", end=False, session=session)
      titulo = _titulo_curto(doc.get("titulo", "?"))
      url = doc.get("url_audio", "")
      if url:
          return _build_audio(titulo, url)
      return _resp(f"{titulo} sem audio.", end=True)


def _handle_ajuda(session):
      return _resp(
          "Para navegar: diga o numero do menu. "
          "Dentro de cada menu, diga o numero da opcao. "
          f"A qualquer momento, diga {NUM_REPETIR} para repetir ou {NUM_VOLTAR} para voltar. "
          "Diga voltar para ir ao menu principal.",
          end=False, session=session)


# ==================== BUSCA DE DADOS ====================

def _buscar_dados_completos():
      """Busca documentos e menu do GitHub Pages."""
      documentos = []
      menu = list(MENU_DEFAULT)
      try:
          url_index = f"{RSS_BASE_URL}/indice.json"
          with urllib.request.urlopen(url_index, timeout=10) as response:
              dados = json.loads(response.read().decode("utf-8"))
              documentos = dados.get("documentos", [])
              menu = dados.get("menu", {}).get("categorias", list(MENU_DEFAULT))
              return documentos, menu
      except Exception as e:
          logger.warning(f"Erro indice.json: {e}")
      # Fallback RSS
      try:
          url_rss = f"{RSS_BASE_URL}/feed.xml"
          with urllib.request.urlopen(url_rss, timeout=10) as response:
              documentos = _parsear_rss(response.read().decode("utf-8"))
      except Exception as e:
          logger.error(f"Erro RSS: {e}")
      return documentos, menu


def _buscar_compromissos():
      """Busca compromissos do GitHub Pages."""
      try:
          url = f"{RSS_BASE_URL}/compromissos.json"
          with urllib.request.urlopen(url, timeout=8) as response:
              return json.loads(response.read().decode("utf-8"))
      except Exception:
          return []


def _buscar_favoritos():
      """Busca favoritos do GitHub Pages."""
      try:
          url = f"{RSS_BASE_URL}/favoritos.json"
          with urllib.request.urlopen(url, timeout=8) as response:
              return json.loads(response.read().decode("utf-8"))
      except Exception:
          return {}


def _buscar_reunioes():
      """Busca reunioes do GitHub Pages."""
      try:
          url = f"{RSS_BASE_URL}/reunioes.json"
          with urllib.request.urlopen(url, timeout=8) as response:
              return json.loads(response.read().decode("utf-8"))
      except Exception:
          return []


def _buscar_listas():
      """Busca listas mentais do GitHub Pages."""
      try:
          url = f"{RSS_BASE_URL}/listas_mentais.json"
          with urllib.request.urlopen(url, timeout=8) as response:
              return json.loads(response.read().decode("utf-8"))
      except Exception:
          return {}


def _parsear_rss(xml_content):
      documentos = []
      try:
          root = ET.fromstring(xml_content)
          channel = root.find("channel")
          if not channel:
              return []
          categoria = channel.findtext("category", "Documentos")
          for item in channel.findall("item"):
              enc = item.find("enclosure")
              url = enc.get("url", "") if enc is not None else ""
              if url:
                  documentos.append({
                      "titulo": item.findtext("title", "Sem titulo"),
                      "url_audio": url,
                      "categoria": categoria,
                      "data": item.findtext("pubDate", ""),
                  })
      except Exception as e:
          logger.error(f"Erro RSS: {e}")
      return documentos


# ==================== HELPERS DE ORDENACAO ====================

def _ordenar_compromissos(compromissos):
      def chave(c):
          try:
              return datetime.strptime(
                  f"{c.get('data', '01/01/2099')} {c.get('hora', '00:00')}",
                  "%d/%m/%Y %H:%M")
          except Exception:
              return datetime(2099, 1, 1)
      return sorted(compromissos, key=chave)


def _ordenar_reunioes(reunioes):
      def chave(r):
          try:
              return datetime.strptime(r.get("data", "01/01/2000"), "%d/%m/%Y")
          except Exception:
              return datetime(2000, 1, 1)
      return sorted(reunioes, key=chave, reverse=True)


def _docs_recentes(documentos, dias=30):
      cutoff = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
      recentes = [d for d in documentos if d.get("data", "")[:10] >= cutoff]
      return sorted(recentes, key=lambda d: d.get("data", ""), reverse=True)


# ==================== HELPERS GERAIS ====================

def _titulo_curto(titulo):
      if titulo.lower().endswith(".mp3"):
          titulo = titulo[:-4]
      titulo = re.sub(r"^.*?Cap\s*\d+\s*[-–]\s*", "", titulo)
      titulo = re.sub(r"\s*[-–]\s*Parte\s*\d+$", "", titulo)
      titulo = re.sub(r"\s+", " ", titulo).strip()
      if titulo.lower() in ("untitled", "sem titulo", ""):
          titulo = "Documento sem nome"
      return titulo


def _buscar_por_nome(documentos, nome):
      nome_lower = nome.lower().strip()
      for d in documentos:
          if nome_lower in _titulo_curto(d.get("titulo", "")).lower():
              return d
      palavras = nome_lower.split()
      for d in documentos:
          titulo_lower = _titulo_curto(d.get("titulo", "")).lower()
          if any(p in titulo_lower for p in palavras if len(p) > 2):
              return d
      return None


def _enumerar_menu_principal(menu, documentos):
      """Monta o texto do menu principal."""
      partes = []
      for cat in menu:
          num = cat.get("numero")
          nome = cat.get("nome", "")
          tipo = cat.get("tipo", "filtro")
          # Menus permanentes (sempre aparecem)
          if tipo in ("recentes", "gravacao", "configuracoes", "favoritos",
                       "musica", "calendario", "reunioes", "listas_mentais", "youtube"):
              partes.append(f"{num} para {nome}")
          else:
              # tipo filtro: so aparece se tiver documentos
              cat_filtro = cat.get("categoria", nome)
              if any(d.get("categoria", "") == cat_filtro for d in documentos):
                  partes.append(f"{num} para {nome}")
      if not partes:
          return "Sua biblioteca esta vazia."
      return (
          f"Voce tem {len(partes)} opcoes. {', '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para sair. "
          "Qual numero?"
      )


def _obter_json(session, chave):
      try:
          valor = session.get(chave, "")
          if valor:
              return json.loads(valor)
      except Exception:
          pass
      return None


def _registrar_uso(titulo, acao, extra=None):
      dados = {
          "evento": "USO_SKILL",
          "timestamp": datetime.now().isoformat(),
          "acao": acao,
          "titulo": titulo,
      }
      if extra is not None:
          dados["extra"] = extra
      logger.info(f"ANALYTICS|{json.dumps(dados, ensure_ascii=False)}")


def _extrair_numero(slots, nome):
      try:
          slot_data = slots.get(nome, {})
          valor = slot_data.get("value", "")
          logger.info(f"DEBUG _extrair_numero: nome={nome} | slot_data={slot_data} | valor={valor} | tipo={type(valor)}")
          if valor:
              # Tenta converter direto (ex: "7" → 7)
              try:
                  return int(valor)
              except ValueError:
                  # AMAZON.NUMBER pode retornar texto em pt-BR (ex: "sete")
                  num = _PALAVRAS_NUMEROS.get(valor.lower().strip())
                  if num is not None:
                      return num
      except (TypeError) as e:
          logger.error(f"DEBUG _extrair_numero ERROR: {e}")
          pass
      return None


# Mapa de palavras em portugues para numeros
_PALAVRAS_NUMEROS = {
      "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3,
      "quatro": 4, "cinco": 5, "seis": 6, "meia": 6, "sete": 7, "oito": 8,
      "nove": 9, "dez": 10, "onze": 11, "doze": 12,
      "primeiro": 1, "primeira": 1, "segundo": 2, "segunda": 2,
      "terceiro": 3, "terceira": 3, "quarto": 4, "quarta": 4,
      "quinto": 5, "quinta": 5, "sexto": 6, "sexta": 6,
      "sétimo": 7, "setimo": 7, "oitavo": 8, "oitava": 8,
      "nono": 9, "nona": 9, "décimo": 10, "decimo": 10,
      "noventa e oito": 98, "noventa e nove": 99,
}


def _extrair_numero_da_fala(event):
      """Tenta extrair um numero da fala bruta do usuario (fallback)."""
      try:
          # Fonte 1: inputTranscript — texto bruto da fala (campo real da Alexa)
          raw = event.get("request", {}).get("inputTranscript", "") or ""
          # Fonte 2: tenta slot value direto
          if not raw:
              raw = event.get("request", {}).get("intent", {}).get("slots", {}).get("numero", {}).get("value", "") or ""
          # Fonte 3: tenta slots genericos
          if not raw:
              for slot_name, slot_data in event.get("request", {}).get("intent", {}).get("slots", {}).items():
                  if isinstance(slot_data, dict):
                      raw = slot_data.get("value", "") or ""
                      if raw:
                          break
          logger.info(f"Fallback raw input: '{raw}' | inputTranscript: '{event.get('request', {}).get('inputTranscript', 'N/A')}'")

          # Limpa o texto
          texto = raw.lower().strip()
          if not texto:
              return None

          # Tenta converter direto
          try:
              return int(texto)
          except ValueError:
              pass

          # Tenta mapear palavra para numero
          for palavra, num in _PALAVRAS_NUMEROS.items():
              if palavra in texto:
                  return num

          # Tenta extrair qualquer digito do texto
          digitos = re.findall(r'\d+', texto)
          if digitos:
              return int(digitos[0])

      except Exception as e:
          logger.warning(f"Erro extrair numero fallback: {e}")
      return None


def _extrair_texto(slots, nome):
      try:
          return slots.get(nome, {}).get("value", "") or ""
      except Exception:
          return ""


# ==================== RESPOSTAS ====================

def _resp(text, end=True, reprompt=None, session=None):
      """Cria resposta da Alexa. Se session tem 'velocidade', usa SSML para ajustar ritmo."""
      # Mapa de velocidade para SSML prosody rate
      _RATE_MAP = {
          "muito_devagar": "x-slow",
          "devagar":       "slow",
          "normal":        "medium",
          "rapido":        "fast",
          "muito_rapido":  "x-fast",
      }

      vel = (session or {}).get("velocidade", "normal")
      rate = _RATE_MAP.get(vel, "medium")

      if rate != "medium":
          # Escapa caracteres especiais XML no texto
          texto_seguro = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
          ssml = f'<speak><prosody rate="{rate}">{texto_seguro}</prosody></speak>'
          fala = {"type": "SSML", "ssml": ssml}
          reprompt_fala = None
          if reprompt:
              rep_seguro = reprompt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
              reprompt_fala = {"type": "SSML", "ssml": f'<speak><prosody rate="{rate}">{rep_seguro}</prosody></speak>'}
      else:
          fala = {"type": "PlainText", "text": text}
          reprompt_fala = {"type": "PlainText", "text": reprompt} if reprompt else None

      response = {
          "version": "1.0",
          "response": {
              "outputSpeech": fala,
              "shouldEndSession": end,
          }
      }
      if reprompt_fala:
          response["response"]["reprompt"] = {"outputSpeech": reprompt_fala}
      if session:
          response["sessionAttributes"] = session
      return response


def _build_audio(titulo, url_audio, token=None, session_extra=None):
      """Reproduz um MP3 via AudioPlayer.
      token: identificador do audio, usado para pular capitulos (livro_base|||cap_idx)
      session_extra: atributos de sessao a preservar (obs: Alexa encerra sessao durante audio)
      """
      _registrar_uso(titulo, "play")
      audio_token = token or titulo
      resposta = {
          "version": "1.0",
          "response": {
              "outputSpeech": {"type": "PlainText", "text": f"Reproduzindo {titulo}"},
              "directives": [{
                  "type": "AudioPlayer.Play",
                  "playBehavior": "REPLACE_ALL",
                  "audioItem": {
                      "stream": {
                          "url": url_audio,
                          "token": audio_token,
                          "offsetInMilliseconds": 0,
                      },
                      "metadata": {
                          "title": titulo,
                          "subtitle": "Super Alexa — Caxinguele",
                      }
                  }
              }],
              "shouldEndSession": True,
          }
      }
      if session_extra:
          resposta["sessionAttributes"] = session_extra
      return resposta
