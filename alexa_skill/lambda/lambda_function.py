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
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ==================== CONFIGURACOES ====================

RSS_BASE_URL = "https://andrezoepaiva-commits.github.io/caxinguele-audiobooks"

# F4: Sino curto enfileirado entre capitulos (UPLOAD MANUAL DE sino.mp3 NO REPO PAGES)
SINO_URL = f"{RSS_BASE_URL}/sino.mp3"

# Menu padrao sincronizado com o Labirinto de Numeros
# Numeracao sequencial: 0-8 sao opcoes, 9 = voltar ao menu principal
MENU_DEFAULT = [
      {"numero": 0, "nome": "Organizacoes Mentais",           "tipo": "gravacao"},
      {"numero": 1, "nome": "Ultimas Atualizacoes",           "tipo": "recentes"},
      {"numero": 2, "nome": "Livros",                          "tipo": "filtro",  "categoria": "Livros"},
      {"numero": 3, "nome": "Favoritos Importantes",           "tipo": "favoritos"},
      {"numero": 4, "nome": "Musica",                          "tipo": "musica"},
      {"numero": 5, "nome": "Calendario e Compromissos",       "tipo": "calendario"},
      {"numero": 6, "nome": "Reunioes Caxinguele",             "tipo": "reunioes"},
      {"numero": 7, "nome": "Organizacoes da Mente em Listas", "tipo": "listas_mentais"},
      {"numero": 8, "nome": "Configuracoes",                   "tipo": "configuracoes"},
      {"numero": 9, "nome": "Voltar ao Menu Principal",        "tipo": "voltar_menu"},
]

# Numeros especiais reservados para navegacao
NUM_REPETIR = 98
NUM_VOLTAR  = 99

# DynamoDB para persistencia de capitulo entre sessoes
DYNAMODB_TABLE           = "caxinguele_progresso"
DYNAMODB_LISTENING_TABLE = "caxinguele_listening_history"  # tempo de leitura por sessao
TOKEN_SEPARADOR = "|||"  # usado no token do AudioPlayer: "livro_base|||capitulo_idx"
REWIND_MS = 10000  # rebobinar 10s no resume (TTS sem pausa natural entre frases)


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
          elif request_type == "AudioPlayer.PlaybackNearlyFinished":
              return handle_playback_nearly_finished(event)
          elif request_type in ("AudioPlayer.PlaybackFinished", "AudioPlayer.PlaybackFailed"):
              return {"version": "1.0", "response": {}}
          else:
              return _resp("Nao entendi. Tente dizer o numero do menu, ou diga ajuda.", end=False)

      except Exception as e:
          logger.error(f"ERRO CRITICO: {str(e)}", exc_info=True)
          return _resp("Houve um erro. Tente novamente.", end=True)


# ==================== LAUNCH ====================

def handle_launch(event):
      """Abertura: mostra menu principal (nivel 1). Se tem livro em andamento, oferece retomar."""
      documentos, menu = _buscar_dados_completos()
      user_id = _get_user_id(event)
      progresso = _carregar_progresso(user_id)
      flags = _carregar_flags(user_id)

      session = {
          "nivel":      "menu",
          "todos_docs": json.dumps(documentos),
          "menu":       json.dumps(menu),
          "user_id":    user_id,
          "progresso":  json.dumps(progresso),
          # Flags persistentes injetadas na session (sobrevivem entre sessoes via DynamoDB)
          "avisado_ja_lidos": "true" if flags.get("avisado_ja_lidos") else "false",
          "onboarding_feito": "true" if flags.get("onboarding_feito") else "false",
      }

      # F3: Onboarding na 1a vez — explica navegacao basica antes do menu
      prefixo_onboarding = ""
      if not flags.get("onboarding_feito"):
          # Extrai o numero real do menu "Livros" (pode mudar entre deploys via indice.json)
          livros_num = next((m["numero"] for m in menu if m.get("nome", "").lower() == "livros"), 2)
          prefixo_onboarding = (
              "Bem vindo aos seus Audiobooks. "
              "Diga ajuda a qualquer hora. "
          )
          _salvar_flag(user_id, "onboarding_feito", True)
          session["onboarding_feito"] = "true"

      prefixo_retomar = ""
      if progresso:
          try:
              # Pega o livro mais RECENTE pelo timestamp (nao o de maior cap_idx)
              ultimo_livro = max(progresso, key=lambda k: progresso[k].get("ts", ""))
              cap_idx = int(progresso[ultimo_livro].get("cap_idx", 0))
              livros = _agrupar_livros(documentos)
              livro = next((l for l in livros if l["livro_base"] == ultimo_livro), None)
              if livro and livro.get("capitulos"):
                  total_caps = len(livro["capitulos"])
                  nome_livro = livro["titulo"]
                  prefixo_retomar = (
                      f"Bem vindo de volta. Voce estava ouvindo {nome_livro}, "
                      f"capitulo {cap_idx + 1} de {total_caps}. "
                      "Diga continuar para retomar. Ou escolha um menu. "
                  )
          except Exception as e:
              logger.info(f"Sem progresso para retomar: {e}")

      texto_menu = _enumerar_menu_principal(menu, documentos)
      texto = prefixo_onboarding + prefixo_retomar + texto_menu

      _registrar_uso("_abertura", "launch", len(documentos))
      # Reprompt = menu inteiro: se silencio (~8s), Alexa repete todas opcoes automaticamente
      reprompt = ("Diga continuar para retomar, ou escolha. " + texto_menu) if progresso else texto_menu
      return _resp(texto, end=False, reprompt=reprompt, session=session)


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
          # Para o audio e encerra a sessao
          return {
              "version": "1.0",
              "response": {
                  "directives": [{"type": "AudioPlayer.Stop"}],
                  "shouldEndSession": True,
              }
          }
      if intent_name == "AMAZON.ResumeIntent":
          # Retoma o ultimo livro do DynamoDB no offset salvo (com rebobinada)
          try:
              user_id = _get_user_id(event)
              progresso = _carregar_progresso(user_id)
              if progresso:
                  # Pega o livro mais RECENTE pelo timestamp
                  ultimo_livro = max(progresso, key=lambda k: progresso[k].get("ts", ""))
                  prog = progresso[ultimo_livro]
                  cap_idx = int(prog.get("cap_idx", 0))
                  offset_salvo = int(prog.get("offset_ms", 0))
                  # Rebobina REWIND_MS para dar contexto (TTS sem pausa natural)
                  offset_resume = max(0, offset_salvo - REWIND_MS)
                  documentos, _ = _buscar_dados_completos()
                  livros = _agrupar_livros(documentos)
                  livro = next((l for l in livros if l["livro_base"] == ultimo_livro), None)
                  if livro and livro.get("capitulos"):
                      caps = livro["capitulos"]
                      if cap_idx < len(caps):
                          cap = caps[cap_idx]
                          url = cap.get("url_audio", "")
                          if url:
                              token = f"{ultimo_livro}{TOKEN_SEPARADOR}{cap_idx}"
                              cap_titulo = _titulo_curto(cap.get("titulo", f"Capitulo {cap_idx + 1}"))
                              return _build_audio(
                                  f"Continuando: {cap_titulo}",
                                  url,
                                  token=token,
                                  total_capitulos=len(caps),
                                  offset_ms=offset_resume,
                              )
              documentos, menu = _buscar_dados_completos()
              user_id = _get_user_id(event)
              full_session = {
                  "nivel": "menu",
                  "todos_docs": json.dumps(documentos),
                  "menu": json.dumps(menu),
                  "user_id": user_id,
              }
              texto_menu = _enumerar_menu_principal(menu, documentos)
              return _resp(
                  "Nenhum livro em andamento ainda. " + texto_menu,
                  end=False, session=full_session)
          except Exception as e:
              logger.warning(f"ResumeIntent erro: {e}")
              return _resp(
                  "Nao consegui retomar. Diga o numero do menu ou diga ajuda.",
                  end=False, session=session)
      if intent_name in ("AMAZON.HelpIntent", "OpcoesIntent"):
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

      # Paginacao da lista de livros
      if intent_name == "PaginaProximaIntent":
          if session.get("menu_tipo") == "livros":
              pagina = int(session.get("pagina_livros", "1"))
              # F4 fix: detectar fim da lista antes de tentar avancar
              livros_dados = _obter_json(session, "livros_dados") or []
              progresso = _obter_json(session, "progresso") or {}
              cats = _categorizar_livros(livros_dados, progresso)
              mostrar = session.get("mostrar_ja_lidos") == "true"
              visiveis = cats["em_progresso"] + cats["nunca_lidos"] + cats["em_progresso_abandonados"]
              if mostrar:
                  visiveis = visiveis + cats["ja_lidos"]
              total_paginas = max(1, (len(visiveis) + PAGINA_TAM_LIVROS - 1) // PAGINA_TAM_LIVROS)
              if pagina >= total_paginas:
                  return _resp(
                      "Esses sao todos os seus livros. Diga o numero que quer ouvir, ou voltar.",
                      end=False, session=session)
              new_session = {**session, "pagina_livros": str(pagina + 1)}
              return _render_pagina_livros(new_session, mostrar_ja_lidos=mostrar)
          return _resp("Diga proximos so na lista de livros.", end=False, session=session)
      if intent_name == "PaginaAnteriorIntent":
          if session.get("menu_tipo") == "livros":
              pagina = int(session.get("pagina_livros", "1"))
              new_session = {**session, "pagina_livros": str(max(1, pagina - 1))}
              mostrar = session.get("mostrar_ja_lidos") == "true"
              return _render_pagina_livros(new_session, mostrar_ja_lidos=mostrar)
          return _resp("Diga anterior so na lista de livros.", end=False, session=session)
      if intent_name == "MostrarOuvidosIntent":
          if session.get("menu_tipo") == "livros":
              # P2e (S246): checar se ha ja_lidos antes de listar
              livros_dados = _obter_json(session, "livros_dados") or []
              progresso = _obter_json(session, "progresso") or {}
              cats = _categorizar_livros(livros_dados, progresso)
              if not cats["ja_lidos"]:
                  return _resp(
                      "Voce ainda nao terminou nenhum livro completo. Diga voltar pra lista.",
                      end=False, session=session)
              # Persiste flag no DynamoDB pra nao avisar mais em sessoes futuras (fix F3)
              user_id = _get_user_id(event)
              _salvar_flag(user_id, "avisado_ja_lidos", True)
              new_session = {
                  **session,
                  "pagina_livros":      "1",
                  "mostrar_ja_lidos":   "true",
                  "avisado_ja_lidos":   "true",
              }
              return _render_pagina_livros(new_session, mostrar_ja_lidos=True)
          return _resp("Diga ouvidos so na lista de livros.", end=False, session=session)

      # F5: esquecer livro abandonado (remove do progresso)
      if intent_name == "EsquecerLivroIntent":
          if session.get("menu_tipo") != "livros":
              return _resp(
                  "Diga esquecer so quando estiver na lista de Livros.",
                  end=False, session=session)
          numero = _extrair_numero(slots, "numero")
          if numero is None:
              numero = _extrair_numero_da_fala(event)
          if numero is None:
              # P2b: usuario falou so "esquecer" sem numero
              return _resp("Esquecer qual numero? Diga por exemplo: esquecer 3.",
                            end=False, session=session)
          visiveis = _livros_visiveis(session)
          if not (1 <= numero <= len(visiveis)):
              return _resp(f"Numero {numero} nao existe. Diga repetir.",
                            end=False, session=session)
          livro = visiveis[numero - 1]
          livro_base = livro.get("livro_base", "")
          titulo_curto = livro.get("titulo", "?")
          # P2c: verificar se o livro tem progresso ANTES de tentar esquecer
          progresso = _obter_json(session, "progresso") or {}
          if livro_base not in progresso:
              return _resp(
                  f"{titulo_curto} nao tem progresso pra esquecer. Voce ainda nao comecou a ouvir esse livro.",
                  end=False, session=session)
          user_id = _get_user_id(event)
          ok = _esquecer_livro(user_id, livro_base)
          # Atualiza progresso na session pra refletir mudanca imediatamente
          progresso.pop(livro_base, None)
          new_session = {
              **session,
              "progresso":      json.dumps(progresso),
              "pagina_livros":  "1",
          }
          if ok:
              # Render com aviso de confirmacao prepended (suporta PlainText E SSML)
              resp = _render_pagina_livros(new_session, mostrar_ja_lidos=session.get("mostrar_ja_lidos") == "true")
              try:
                  out = resp["response"]["outputSpeech"]
                  if out.get("type") == "SSML" and out.get("ssml"):
                      # Insere confirmacao logo apos <speak> (preserva tags prosody)
                      ssml = out["ssml"]
                      texto_seguro = titulo_curto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                      out["ssml"] = ssml.replace("<speak>", f"<speak>{texto_seguro} foi esquecido. ", 1)
                  else:
                      out["text"] = f"{titulo_curto} foi esquecido. {out.get('text', '')}"
              except Exception as e:
                  logger.warning(f"Erro ao prepend confirmacao esquecer: {e}")
              return resp
          return _resp(f"Nao consegui esquecer {titulo_curto}. Erro tecnico, tente de novo.",
                        end=False, session=session)

      # Fallback: tenta extrair numero da fala bruta
      if intent_name == "AMAZON.FallbackIntent":
          fala_bruta = event.get("request", {}).get("intent", {}).get("slots", {})
          # Tenta extrair numero de qualquer texto
          numero = _extrair_numero_da_fala(event)
          if numero is not None:
              return _roteador_numero(numero, session)
          return _resp("Nao entendi. Tente dizer o numero, por exemplo: numero dois.",
                        end=False, session=session)

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
          return _resp(f"Nao encontrei o menu {numero}. " + _enumerar_menu_principal(menu, todos_docs),
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

      # ---------- Menu 7: YouTube e Videos ----------
      if tipo == "youtube":
          opcoes = cat.get("opcoes", [])
          partes = [f"{o['numero']} para {o['nome']}" for o in opcoes]
          return _resp(
              f"{nome}. {', '.join(partes)}. "
              "Diga repetir ou voltar.",
              end=False,
              session={**session, "nivel": "submenu", "menu_tipo": "youtube"})

      # ---------- Menu 9: Configuracoes ----------
      if tipo == "configuracoes":
          return _resp(
              f"{nome}. 1 para Velocidade da Fala. "
              "2 para Guia do Usuario. "
              "Diga repetir ou voltar.",
              end=False,
              session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})

      # ---------- Menu 10: Listas Mentais ----------
      if tipo == "listas_mentais":
          return _menu_listas(session)

      # ---------- Voltar ao Menu Principal ----------
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
      """Carrega progresso salvo. Migra entradas legado (int) pro schema novo (dict).

      Schema novo: {livro_base: {"cap_idx": int, "offset_ms": int, "ts": str}}
      Schema legado: {livro_base: int}  (so cap_idx)
      """
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          resp = table.get_item(Key={"user_id": user_id})
          bruto = resp.get("Item", {}).get("progresso", {})
          progresso = {}
          for livro, valor in bruto.items():
              if isinstance(valor, dict):
                  progresso[livro] = valor
              else:
                  # Migracao on-read: legado (int) -> dict
                  progresso[livro] = {"cap_idx": int(valor), "offset_ms": 0, "ts": ""}
          return progresso
      except Exception as e:
          logger.info(f"Progresso nao encontrado (normal na 1a vez): {e}")
          return {}


def _salvar_progresso(user_id, livro_base, capitulo_idx, offset_ms=0):
      """Salva capitulo, offset de audio e timestamp.

      offset_ms=0 quando muda de capitulo. Valor real vem de PlaybackStopped.
      timestamp atualizado a cada save permite rastrear "ultimo livro ouvido".

      Faz 2 update_items sequenciais: primeiro garante que o mapa "progresso"
      exista (cria item ou atributo se for 1a vez do usuario), depois faz o
      SET aninhado. Sem isso, primeiro save de usuario novo da
      ValidationException silenciosa (item ou atributo nao existe).
      """
      try:
          timestamp = datetime.utcnow().isoformat() + "Z"
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          # Passo 1: garante mapa "progresso" no item (idempotente)
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="SET progresso = if_not_exists(progresso, :empty)",
              ExpressionAttributeValues={":empty": {}},
          )
          # Passo 2: SET aninhado da entrada do livro
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="SET progresso.#livro = :p",
              ExpressionAttributeNames={"#livro": livro_base},
              ExpressionAttributeValues={":p": {
                  "cap_idx": int(capitulo_idx),
                  "offset_ms": int(offset_ms),
                  "ts": timestamp,
              }},
          )
          logger.info(f"Progresso salvo: {livro_base} cap {capitulo_idx} offset {offset_ms}ms")
      except Exception as e:
          logger.warning(f"Erro ao salvar progresso: {e}")


def _esquecer_livro(user_id, livro_base):
      """F5: Remove entrada do livro do mapa progresso. Livro vira 'nunca lido' visualmente."""
      if not user_id or not livro_base:
          return False
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="REMOVE progresso.#l",
              ExpressionAttributeNames={"#l": livro_base},
          )
          logger.info(f"Livro esquecido: {livro_base}")
          return True
      except Exception as e:
          logger.warning(f"Erro ao esquecer livro {livro_base}: {e}")
          return False


# ==================== DYNAMODB: FLAGS PERSISTENTES (avisado_ja_lidos, etc) ====================

def _carregar_flags(user_id):
      """Carrega flags persistentes do usuario do DynamoDB. Retorna dict (vazio se nao existe)."""
      if not user_id:
          return {}
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          resp = table.get_item(Key={"user_id": user_id})
          return resp.get("Item", {}).get("flags", {}) or {}
      except Exception as e:
          logger.info(f"Sem flags ainda (normal na 1a vez): {e}")
          return {}


def _salvar_flag(user_id, nome, valor):
      """Salva uma flag boolean no DynamoDB. Garante mapa flags via if_not_exists (mesmo padrao do progresso)."""
      if not user_id:
          return
      try:
          table = _get_dynamo().Table(DYNAMODB_TABLE)
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="SET flags = if_not_exists(flags, :empty)",
              ExpressionAttributeValues={":empty": {}},
          )
          table.update_item(
              Key={"user_id": user_id},
              UpdateExpression="SET flags.#f = :v",
              ExpressionAttributeNames={"#f": nome},
              ExpressionAttributeValues={":v": bool(valor)},
          )
          logger.info(f"Flag salva: {nome}={valor}")
      except Exception as e:
          logger.warning(f"Erro ao salvar flag {nome}: {e}")


# ==================== DYNAMODB: TEMPO DE LEITURA ====================

def _registrar_sessao_inicio(user_id, token, timestamp):
      """Cria entrada de sessao de escuta com tempo_inicio (sem tempo_fim ainda)."""
      try:
          partes = token.split(TOKEN_SEPARADOR) if TOKEN_SEPARADOR in token else [token, "0"]
          documento = partes[0].replace("_", " ")

          table = _get_dynamo().Table(DYNAMODB_LISTENING_TABLE)
          table.put_item(Item={
              "user_id":         user_id,
              "data_sessao":     timestamp,
              "documento":       documento,
              "token":           token,
              "tempo_inicio":    timestamp,
              "tempo_fim":       None,
              "minutos_ouvidos": 0,
              "status":          "em_andamento",
          })
          logger.info(f"Sessao inicio registrada: {documento} @ {timestamp}")
      except Exception as e:
          logger.warning(f"Erro ao registrar inicio de sessao: {e}")


def _registrar_sessao_fim(user_id, token, timestamp_fim):
      """Busca a sessao aberta e calcula minutos_ouvidos."""
      try:
          from boto3.dynamodb.conditions import Key as DynKey
          table = _get_dynamo().Table(DYNAMODB_LISTENING_TABLE)

          resp = table.query(
              KeyConditionExpression=DynKey("user_id").eq(user_id),
              FilterExpression="token = :t AND #s = :s",
              ExpressionAttributeNames={"#s": "status"},
              ExpressionAttributeValues={":t": token, ":s": "em_andamento"},
              ScanIndexForward=False,
              Limit=1,
          )
          itens = resp.get("Items", [])
          if not itens:
              return

          sessao = itens[0]
          data_sessao = sessao["data_sessao"]
          tempo_inicio_str = sessao.get("tempo_inicio", data_sessao)

          try:
              t_inicio = datetime.fromisoformat(tempo_inicio_str.replace("Z", "+00:00"))
              t_fim    = datetime.fromisoformat(timestamp_fim.replace("Z", "+00:00"))
              minutos  = max(0, int((t_fim - t_inicio).total_seconds() / 60))
          except Exception:
              minutos = 0

          table.update_item(
              Key={"user_id": user_id, "data_sessao": data_sessao},
              UpdateExpression="SET tempo_fim = :tf, minutos_ouvidos = :m, #s = :s",
              ExpressionAttributeNames={"#s": "status"},
              ExpressionAttributeValues={":tf": timestamp_fim, ":m": minutos, ":s": "concluida"}
          )
          logger.info(f"Sessao fim: {sessao['documento']} — {minutos} min")
      except Exception as e:
          logger.warning(f"Erro ao registrar fim de sessao: {e}")


def _calcular_tempo_leitura(user_id, periodo="mes"):
      """Retorna estatisticas de tempo de leitura para o periodo."""
      try:
          from boto3.dynamodb.conditions import Key as DynKey
          table = _get_dynamo().Table(DYNAMODB_LISTENING_TABLE)

          agora = datetime.utcnow()
          if periodo == "mes":
              corte = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
          elif periodo == "semana":
              corte = agora - timedelta(days=agora.weekday())
              corte = corte.replace(hour=0, minute=0, second=0, microsecond=0)
          else:
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
          horas = total // 60
          horas_str = f"{horas}h {total % 60}min" if horas > 0 else f"{total % 60}min"
          dias = max(1, (agora - corte).days + 1)

          contagem = {}
          for s in sessoes:
              doc = s.get("documento", "Desconhecido")
              contagem[doc] = contagem.get(doc, 0) + int(s.get("minutos_ouvidos", 0))

          top = sorted(
              [{"documento": d, "minutos": m, "percentual": int(m / max(total, 1) * 100)}
               for d, m in contagem.items()],
              key=lambda x: -x["minutos"]
          )[:5]

          return {"total_minutos": total, "horas_minutos": horas_str,
                  "media_por_dia": round(total / dias), "top_documentos": top}
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


DIAS_PARA_ABANDONO = 14  # F5: livro parado >N dias vira "abandonado" (perde destaque)


def _dias_parado(ts_str):
      """Calcula dias desde o ultimo timestamp do progresso. Retorna 999 se ts invalido."""
      if not ts_str:
          return 999
      try:
          ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
          agora = datetime.utcnow().replace(tzinfo=ts.tzinfo)
          return (agora - ts).days
      except Exception:
          return 999


def _categorizar_livros(livros, progresso):
      """Separa livros em 4 grupos: em_progresso (ativos), em_progresso_abandonados, nunca_lidos, ja_lidos.
      Ativo = cap_idx > 0, parado <=14 dias.
      Abandonado (F5) = cap_idx > 0, parado >14 dias — perde destaque.
      Ja lido = ultimo cap E offset_ms > MIN_OFFSET_OUVIDO (>=60s ouvido do ultimo cap).
        P2e: criterio fortalecido em S246 — sem offset min, livros pulados via "escolher capitulo"
        sem ouvir contavam como ja_lidos por engano.
      Nunca lido = sem entrada de progresso ou cap_idx == 0 (e sem offset).
      """
      MIN_OFFSET_OUVIDO_MS = 60_000  # 60s do ultimo cap = qualifica como ouvido
      em_progresso = []
      em_progresso_abandonados = []
      nunca_lidos = []
      ja_lidos = []
      for livro in livros:
          livro_base = livro.get("livro_base", "")
          prog = progresso.get(livro_base) if isinstance(progresso, dict) else None
          if not prog:
              nunca_lidos.append(livro)
              continue
          if isinstance(prog, dict):
              cap_idx = int(prog.get("cap_idx", 0))
              offset_ms = int(prog.get("offset_ms", 0))
              ts = prog.get("ts", "")
          else:
              cap_idx = int(prog)
              offset_ms = 0
              ts = ""
          livro_meta = {**livro, "_ts": ts, "_cap_idx": cap_idx}
          total = livro.get("total_capitulos", 0)
          # P2e (S246): livro 1 cap unico vira ja_lido SO se offset_ms >= 60s
          if total == 1 and offset_ms >= MIN_OFFSET_OUVIDO_MS:
              ja_lidos.append(livro_meta)
          # P2e (S246): multicap vira ja_lido SO se ultimo cap E ouviu >= 60s dele
          elif total > 0 and cap_idx >= total - 1 and cap_idx > 0 and offset_ms >= MIN_OFFSET_OUVIDO_MS:
              ja_lidos.append(livro_meta)
          elif cap_idx > 0:
              # F5: separar ativo de abandonado pelo numero de dias parado
              dias = _dias_parado(ts)
              livro_meta["_dias_parado"] = dias
              if dias > DIAS_PARA_ABANDONO:
                  em_progresso_abandonados.append(livro_meta)
              else:
                  em_progresso.append(livro_meta)
          else:
              nunca_lidos.append(livro)
      em_progresso.sort(key=lambda l: l.get("_ts", ""), reverse=True)
      em_progresso_abandonados.sort(key=lambda l: l.get("_ts", ""), reverse=True)
      ja_lidos.sort(key=lambda l: l.get("_ts", ""), reverse=True)
      nunca_lidos.sort(key=lambda l: l.get("titulo", "").lower())
      return {
          "em_progresso":              em_progresso,
          "em_progresso_abandonados":  em_progresso_abandonados,
          "nunca_lidos":               nunca_lidos,
          "ja_lidos":                  ja_lidos,
      }


def _livros_visiveis(session):
      """Lista visivel de livros na ordem mostrada.
      Ordem (F5): ativos -> nunca_lidos -> abandonados -> (opcional) ja_lidos.
      Abandonados perdem destaque mas continuam acessiveis.
      Mesma ordem usada por _render_pagina_livros, pra _selecionar_submenu indexar correto.
      """
      livros_dados = _obter_json(session, "livros_dados") or []
      progresso = _obter_json(session, "progresso") or {}
      mostrar_ja_lidos = session.get("mostrar_ja_lidos") == "true"
      cats = _categorizar_livros(livros_dados, progresso)
      visiveis = cats["em_progresso"] + cats["nunca_lidos"] + cats["em_progresso_abandonados"]
      if mostrar_ja_lidos:
          visiveis = visiveis + cats["ja_lidos"]
      return visiveis


PAGINA_TAM_LIVROS = 5


def _render_pagina_livros(session, mostrar_ja_lidos=False):
      """Renderiza pagina atual de livros com paginacao 5 + categorizacao."""
      livros_dados = _obter_json(session, "livros_dados") or []
      progresso = _obter_json(session, "progresso") or {}
      pagina = int(session.get("pagina_livros", "1"))
      categoria_nome = session.get("livros_categoria", "")

      cats = _categorizar_livros(livros_dados, progresso)
      # F5: ordem ativos -> nunca -> abandonados -> opcional ja_lidos
      visiveis = cats["em_progresso"] + cats["nunca_lidos"] + cats["em_progresso_abandonados"]
      if mostrar_ja_lidos:
          visiveis = visiveis + cats["ja_lidos"]

      if not visiveis:
          texto = f"Nenhum livro disponivel{' em ' + categoria_nome if categoria_nome else ''}. Diga voltar."
          return _resp(texto, end=False, session={**session, "nivel": "submenu", "menu_tipo": "livros_categorias"})

      total_paginas = max(1, (len(visiveis) + PAGINA_TAM_LIVROS - 1) // PAGINA_TAM_LIVROS)
      pagina = max(1, min(pagina, total_paginas))
      inicio = (pagina - 1) * PAGINA_TAM_LIVROS
      fim = inicio + PAGINA_TAM_LIVROS
      pagina_livros = visiveis[inicio:fim]

      # Numeracao GLOBAL (nao reseta por pagina)
      partes = []
      for i, livro in enumerate(pagina_livros, start=inicio + 1):
          n_caps = livro["total_capitulos"]
          cap_idx = livro.get("_cap_idx")
          dias = livro.get("_dias_parado")
          if cap_idx is not None and cap_idx > 0:
              # F5: anuncio diferente pra abandonado
              if dias is not None and dias > DIAS_PARA_ABANDONO:
                  partes.append(f"{i}. {livro['titulo']}, abandonado ha {dias} dias no capitulo {cap_idx + 1} de {n_caps}")
              else:
                  partes.append(f"{i}. {livro['titulo']}, pausado no capitulo {cap_idx + 1} de {n_caps}")
          else:
              caps_txt = f"{n_caps} capitulos" if n_caps > 1 else "1 capitulo"
              partes.append(f"{i}. {livro['titulo']}, {caps_txt}")

      # Comandos de paginacao
      cmds = []
      if pagina < total_paginas:
          prox_n = min(PAGINA_TAM_LIVROS, len(visiveis) - pagina * PAGINA_TAM_LIVROS)
          cmds.append(f"diga proximos para mais {prox_n}")
      if pagina > 1:
          cmds.append("diga anterior")
      # F5: dica do comando esquecer quando ha abandonados na pagina atual
      tem_abandonado_na_pagina = any(
          (l.get("_dias_parado") is not None and l.get("_dias_parado", 0) > DIAS_PARA_ABANDONO)
          for l in pagina_livros
      )
      if tem_abandonado_na_pagina:
          cmds.append("diga esquecer e o numero para remover um livro abandonado")

      # Aviso 1a vez sobre ja_lidos (fix F4: redacao mais curta, sem duplicar "Voce tem")
      avisado = session.get("avisado_ja_lidos") == "true"
      aviso = ""
      if cats["ja_lidos"] and not avisado and not mostrar_ja_lidos:
          n = len(cats["ja_lidos"])
          plural = "s" if n > 1 else ""
          aviso = f"Mais {n} livro{plural} ja ouvido{plural} estao escondidos. Diga ouvidos para escutar a lista. "

      # Cabecalho
      cabecalho = ""
      if pagina == 1:
          tot = len(visiveis)
          plural = "s" if tot > 1 else ""
          rotulo = "ja ouvidos" if mostrar_ja_lidos else "para ouvir"
          cabecalho = f"Voce tem {tot} livro{plural} {rotulo}. "
      if total_paginas > 1:
          cabecalho += f"Pagina {pagina} de {total_paginas}. "

      cmds_txt = ". ".join(cmds) + ". " if cmds else ""
      texto = (
          f"{cabecalho}{'. '.join(partes)}. "
          f"{aviso}"
          f"Para ouvir um livro, diga o numero. {cmds_txt}"
          "Diga repetir ou voltar."
      )

      new_session = {
          **session,
          "nivel":             "submenu",
          "menu_tipo":         "livros",
          "pagina_livros":     str(pagina),
          "mostrar_ja_lidos":  "true" if mostrar_ja_lidos else "false",
      }
      reprompt = "Diga o numero do livro, proximos, anterior, ou voltar."
      return _resp(texto, end=False, reprompt=reprompt, session=new_session)


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
              "Diga voltar para o menu.",
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
          return _build_audio(titulo, url, token=token, session_extra=new_session, total_capitulos=len(capitulos))

      return _resp(
          f"Capitulo {novo_cap + 1} sem audio disponivel. "
          "Tente outro ou diga voltar.",
          end=False, session=session)


def handle_playback_started(event):
      """Quando AudioPlayer comeca a tocar, salva progresso (preservando offset inicial) e registra inicio."""
      try:
          request = event.get("request", {})
          token = request.get("token", "")
          # offsetInMilliseconds do Started = posicao inicial do play (preserva resume)
          offset_ms = int(request.get("offsetInMilliseconds", 0))
          user_id = _get_user_id(event)
          timestamp = request.get("timestamp", datetime.utcnow().isoformat() + "Z")
          if TOKEN_SEPARADOR in token and user_id:
              partes = token.split(TOKEN_SEPARADOR)
              # Nao salva progresso de musica nem de SINO (sino e auxiliar entre capitulos, F4)
              if partes[0] not in ("MUSICA", "SINO"):
                  livro_base = partes[0]
                  capitulo_idx = int(partes[1])
                  _salvar_progresso(user_id, livro_base, capitulo_idx, offset_ms)
                  # Registra inicio da sessao de escuta para calcular tempo depois
                  _registrar_sessao_inicio(user_id, token, timestamp)
      except Exception as e:
          logger.warning(f"Erro ao salvar progresso no playback: {e}")
      return {"version": "1.0", "response": {}}


def handle_playback_stopped(event):
      """Quando usuario para o audio: salva offset (pra retomar do mesmo ponto) + minutos ouvidos."""
      try:
          request = event.get("request", {})
          token = request.get("token", "")
          offset_ms = int(request.get("offsetInMilliseconds", 0))
          user_id = _get_user_id(event)
          timestamp = request.get("timestamp", datetime.utcnow().isoformat() + "Z")
          # Nao rastreia paradas de musica nem de SINO (auxiliar F4)
          if TOKEN_SEPARADOR in token and token.split(TOKEN_SEPARADOR)[0] not in ("MUSICA", "SINO"):
              partes = token.split(TOKEN_SEPARADOR)
              livro_base = partes[0]
              cap_idx = int(partes[1])
              if user_id and livro_base:
                  _salvar_progresso(user_id, livro_base, cap_idx, offset_ms)
              _registrar_sessao_fim(user_id, token, timestamp)
      except Exception as e:
          logger.warning(f"Erro ao registrar parada de audio: {e}")
      return {"version": "1.0", "response": {}}


def handle_playback_nearly_finished(event):
      """Auto-avanco: enfileira proximo audio. Para LIVROS, intercala SINO entre capitulos (F4 Opcao B).
      Fluxo: cap_atual → sino → cap_proximo → sino → ...
      Token SINO: SINO|||{livro_base}|||{prox_cap_idx} (3 partes, vs 2 do livro normal).
      """
      try:
          token = event.get("request", {}).get("token", "")
          if TOKEN_SEPARADOR not in token:
              return {"version": "1.0", "response": {}}

          partes = token.split(TOKEN_SEPARADOR)
          tipo_audio = partes[0]

          # ===== Caso 1: MUSICA terminando — enfileira proxima musica (sem sino) =====
          if tipo_audio == "MUSICA":
              idx_atual = int(partes[1])
              musicas = _buscar_musicas_json()
              musicas_com_url = [m for m in musicas if m.get("url")]
              novo_idx = idx_atual + 1
              if novo_idx < len(musicas_com_url):
                  m = musicas_com_url[novo_idx]
                  novo_token = f"MUSICA{TOKEN_SEPARADOR}{novo_idx}"
                  return {
                      "version": "1.0",
                      "response": {
                          "directives": [{
                              "type": "AudioPlayer.Play",
                              "playBehavior": "ENQUEUE",
                              "audioItem": {
                                  "stream": {
                                      "url": m["url"],
                                      "token": novo_token,
                                      "expectedPreviousToken": token,
                                      "offsetInMilliseconds": 0,
                                  },
                                  "metadata": {
                                      "title": m.get("titulo", f"Musica {novo_idx + 1}"),
                                      "subtitle": "Super Alexa — Caxinguele",
                                  }
                              }
                          }]
                      }
                  }
              return {"version": "1.0", "response": {}}

          # ===== Caso 2: SINO terminando — enfileira proximo capitulo real =====
          if tipo_audio == "SINO" and len(partes) >= 3:
              livro_base = partes[1]
              prox_cap_idx = int(partes[2])
              documentos, _ = _buscar_dados_completos()
              docs_livro = [d for d in documentos if _extrair_livro_base(d.get("titulo", "")) == livro_base]
              docs_livro.sort(key=lambda d: _extrair_num_capitulo(d.get("titulo", "")))
              if prox_cap_idx < len(docs_livro):
                  cap = docs_livro[prox_cap_idx]
                  url = cap.get("url_audio", "")
                  if url:
                      novo_token = f"{livro_base}{TOKEN_SEPARADOR}{prox_cap_idx}"
                      user_id = _get_user_id(event)
                      if user_id:
                          _salvar_progresso(user_id, livro_base, prox_cap_idx)
                      return {
                          "version": "1.0",
                          "response": {
                              "directives": [{
                                  "type": "AudioPlayer.Play",
                                  "playBehavior": "ENQUEUE",
                                  "audioItem": {
                                      "stream": {
                                          "url": url,
                                          "token": novo_token,
                                          "expectedPreviousToken": token,
                                          "offsetInMilliseconds": 0,
                                      },
                                      "metadata": {
                                          "title": _titulo_curto(cap.get("titulo", f"Capitulo {prox_cap_idx + 1}")),
                                          "subtitle": f"{livro_base} — Super Alexa",
                                      }
                                  }
                              }]
                          }
                      }
              return {"version": "1.0", "response": {}}

          # ===== Caso 3: LIVRO terminando — enfileira SINO antes do proximo cap =====
          livro_base = tipo_audio
          idx_atual = int(partes[1])
          documentos, _ = _buscar_dados_completos()
          docs_livro = [d for d in documentos if _extrair_livro_base(d.get("titulo", "")) == livro_base]
          docs_livro.sort(key=lambda d: _extrair_num_capitulo(d.get("titulo", "")))
          novo_cap = idx_atual + 1
          if novo_cap < len(docs_livro):
              # Enfileira SINO; quando sino acabar, NearlyFinished do sino enfileira o cap real
              sino_token = f"SINO{TOKEN_SEPARADOR}{livro_base}{TOKEN_SEPARADOR}{novo_cap}"
              return {
                  "version": "1.0",
                  "response": {
                      "directives": [{
                          "type": "AudioPlayer.Play",
                          "playBehavior": "ENQUEUE",
                          "audioItem": {
                              "stream": {
                                  "url": SINO_URL,
                                  "token": sino_token,
                                  "expectedPreviousToken": token,
                                  "offsetInMilliseconds": 0,
                              },
                              "metadata": {
                                  "title": "Capitulo terminado",
                                  "subtitle": f"{livro_base} — Super Alexa",
                              }
                          }
                      }]
                  }
              }
          # Fim do livro — nao enfileira nada (fica em silencio, usuario decide voltar)
      except Exception as e:
          logger.warning(f"Erro ao enfileirar proximo: {e}")
      return {"version": "1.0", "response": {}}


def handle_playback_next(event):
      """Botão 'próxima faixa' no app durante reprodução de MP3."""
      try:
          token = event.get("request", {}).get("token", "")
          user_id = _get_user_id(event)
          if TOKEN_SEPARADOR in token:
              partes = token.split(TOKEN_SEPARADOR)
              tipo_audio = partes[0]
              # F4: SINO e transicao curta entre caps — ignora Next (deixa sino terminar normalmente)
              if tipo_audio == "SINO":
                  return {"version": "1.0", "response": {}}
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
                          return _build_audio(titulo, url, token=novo_token, total_capitulos=len(docs_livro))
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
              # F4: SINO e transicao curta — ignora Prev (deixa sino terminar)
              if tipo_audio == "SINO":
                  return {"version": "1.0", "response": {}}
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
                          return _build_audio(titulo, url, token=novo_token, total_capitulos=len(docs_livro))
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
              "Diga voltar para o menu.",
              end=False, session=session)
      partes = [f"{m['numero']}. {m['titulo']}" for m in musicas]
      texto = (
          f"Musicas Caxinguele. {len(musicas)} musica{'s' if len(musicas) > 1 else ''} disponivel{'is' if len(musicas) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          "Diga repetir ou voltar. "
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
      {"numero": 1, "nome": "Geral", "filtro": "Livros"},
]


def _menu_livros_categorias(session):
      """Submenu de categorias de livros. Se só 1 categoria, pula direto para lista."""
      if len(LIVROS_CATEGORIAS) == 1:
          cat = LIVROS_CATEGORIAS[0]
          todos_docs = _obter_json(session, "todos_docs") or []
          docs_livros = [d for d in todos_docs if d.get("categoria", "") == cat["filtro"]]
          return _menu_livros(docs_livros, session, categoria_nome=cat["nome"])
      partes = [f"{cat['numero']} para Livros {cat['nome']}" for cat in LIVROS_CATEGORIAS]
      texto = (
          "Livros. Escolha a categoria. "
          f"{'. '.join(partes)}. "
          "Diga repetir ou voltar ao menu."
      )
      new_session = {
          **session,
          "nivel":     "submenu",
          "menu_tipo": "livros_categorias",
      }
      return _resp(texto, end=False, reprompt="Diga o numero da categoria.", session=new_session)


def _menu_livros(docs_brutos, session, categoria_nome=""):
      """Lista livros agrupados, paginados 5 por vez, ordenados por status (em progresso → nunca → ja lidos escondidos)."""
      livros = _agrupar_livros(docs_brutos)
      if not livros:
          return _resp(
              f"Nenhum livro catalogado em {categoria_nome}. "
              "Diga voltar para o menu.",
              end=False, session={**session, "nivel": "submenu", "menu_tipo": "livros_categorias"})
      new_session = {
          **session,
          "livros_dados":      json.dumps(livros),
          "livros_categoria":  categoria_nome,
          "pagina_livros":     "1",
          "mostrar_ja_lidos":  "false",
      }
      return _render_pagina_livros(new_session, mostrar_ja_lidos=False)


# ==================== MENU [9]: CONFIGURACOES — VOZES E VELOCIDADES ====================

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
          "Diga repetir ou voltar."
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
          "Diga repetir ou voltar."
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
          "Diga repetir ou voltar. Qual numero?"
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
          "Diga repetir ou voltar. "
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
          "Diga repetir ou voltar. "
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
          "Diga repetir ou voltar. "
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
                  f"Esse numero nao existe. Temos {len(musicas)} musicas. Diga um numero entre 1 e {len(musicas)}. "
                  "Diga repetir ou voltar.",
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
                  f"Esse numero nao existe. Escolha entre 1 e {len(LIVROS_CATEGORIAS)}. "
                  "Diga repetir ou voltar.",
                  end=False, session=session)
          cat_nome = cat["nome"]
          cat_filtro = cat.get("filtro", cat_nome)
          todos_docs = _obter_json(session, "todos_docs") or []
          docs_livros = [d for d in todos_docs if d.get("categoria", "") == cat_filtro]
          return _menu_livros(docs_livros, session, categoria_nome=cat_nome)

      # ---------- Livros: amigo escolheu qual livro → mostra opcoes ----------
      if menu_tipo == "livros":
          # Lista NA ORDEM mostrada (em_progresso + nunca + opcionalmente ja_lidos)
          visiveis = _livros_visiveis(session)
          if numero == NUM_REPETIR:
              # Re-renderiza a pagina atual (preserva paginacao + filtros)
              mostrar = session.get("mostrar_ja_lidos") == "true"
              return _render_pagina_livros(session, mostrar_ja_lidos=mostrar)
          if numero == NUM_VOLTAR:
              if len(LIVROS_CATEGORIAS) <= 1:
                  return _voltar_menu_principal(session)
              return _menu_livros_categorias(session)
          if not (1 <= numero <= len(visiveis)):
              return _resp(
                  f"Esse numero nao existe. Temos {len(visiveis)} livros visiveis. "
                  f"Diga um numero entre 1 e {len(visiveis)}. Diga repetir ou voltar.",
                  end=False, session=session)

          livro = visiveis[numero - 1]
          titulo_livro = livro["titulo"]
          capitulos = livro.get("capitulos", [])
          livro_base = livro.get("livro_base", titulo_livro)
          n_caps = livro["total_capitulos"]

          # Verifica progresso salvo no DynamoDB (session ja tem schema dict)
          progresso = _obter_json(session, "progresso") or {}
          cap_data = progresso.get(livro_base, None)
          cap_salvo = cap_data.get("cap_idx") if isinstance(cap_data, dict) else cap_data
          opcao_continuar = ""
          if cap_salvo is not None and cap_salvo > 0:
              opcao_continuar = f"2 para Continuar do Capitulo {cap_salvo + 1}. "

          # Eco reforcado do numero + nome (confirmacao implicita pra cego validar acerto)
          texto = (
              f"Numero {numero}. {titulo_livro}. {n_caps} capitulo{'s' if n_caps > 1 else ''}. "
              "Diga 1 para Comecar do Inicio. "
              f"{('Diga ' + opcao_continuar) if opcao_continuar else ''}"
              "Diga 3 para Escolher Capitulo. "
              "Diga 4 para Sinopse. "
              "Ou diga outro numero para outro livro. "
              "Diga repetir ou voltar."
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
                  "Diga repetir ou voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _resp(
                  f"{titulo_livro}. 1 para Comecar do Inicio. 3 para Escolher Capitulo. 4 para Sinopse. "
                  "Diga repetir ou voltar.",
                  end=False, session={**session, "nivel": "item", "menu_tipo": "livros"})
          if not (1 <= numero <= len(capitulos)):
              return _resp(
                  f"Esse numero nao existe. Temos {len(capitulos)} capitulos. Diga um numero entre 1 e {len(capitulos)}.",
                  end=False, session=session)
          cap_idx = numero - 1
          cap = capitulos[cap_idx]
          url = cap.get("url_audio", "")
          cap_titulo = _titulo_curto(cap.get("titulo", f"Capitulo {numero}"))
          if url:
              token = f"{livro_base}{TOKEN_SEPARADOR}{cap_idx}"
              new_session = {**session, "capitulo_atual": str(cap_idx)}
              _registrar_uso(cap_titulo, "play_livro_capitulo")
              return _build_audio(cap_titulo, url, token=token, session_extra=new_session, total_capitulos=len(capitulos))
          return _resp(f"Capitulo {numero} sem audio disponivel.", end=False, session=session)

      # ---------- Calendario: amigo escolheu compromisso ----------
      if menu_tipo == "calendario":
          compromissos = _obter_json(session, "compromissos") or []
          if not (1 <= numero <= len(compromissos)):
              return _resp(
                  f"Esse numero nao existe. Ha {len(compromissos)} compromissos. Qual?",
                  end=False, session=session)
          comp = compromissos[numero - 1]
          texto = (
              f"Compromisso {numero}: {comp.get('titulo', '?')}. "
              f"Data: {comp.get('data', '?')}. Hora: {comp.get('hora', '?')}. "
              f"Descricao: {comp.get('descricao', 'sem descricao')}. "
              f"O que quer fazer? "
              f"1 para editar este compromisso. "
              f"2 para remover este compromisso. "
              "Diga repetir ou voltar."
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
                  f"Esse numero nao existe. Ha {len(reunioes)} reunioes. Diga um numero entre 1 e {len(reunioes)}. "
                  "Diga repetir ou voltar.",
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
              "Diga repetir ou voltar."
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
              return _resp(f"Esse numero nao existe. Ha {len(sublistas)} categorias. Qual?",
                            end=False, session=session)
          sublista_nome = sublistas[numero - 1]
          favoritos = _buscar_favoritos()
          itens = favoritos.get(sublista_nome, [])
          if not itens:
              return _resp(
                  f"{sublista_nome}. Nenhum item favoritado nesta categoria. "
                  "Diga voltar.",
                  end=False, session=session)
          partes = [f"{i}: {it.get('titulo', '?')}" for i, it in enumerate(itens, 1)]
          texto = (
              f"{sublista_nome}. {len(itens)} ite{'m' if len(itens) == 1 else 'ns'}. "
              f"{'. '.join(partes)}. "
              f"Diga o numero para ouvir detalhes e remover se quiser. "
              "Diga repetir ou voltar."
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
              return _resp(f"Esse numero nao existe. Ha {len(itens)} itens. Qual?",
                            end=False, session=session)
          item = itens[numero - 1]
          sublista_nome = session.get("sublista_nome", "")
          texto = (
              f"Item {numero}: {item.get('titulo', '?')}. "
              f"Favoritado em {item.get('favoritado_em', '?')}. "
              f"1 para remover este item dos favoritos. "
              "Diga repetir ou voltar."
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
              return _resp(f"Esse numero nao existe. Ha {len(nomes)} listas. Qual?",
                            end=False, session=session)
          nome_lista = nomes[numero - 1]
          itens = listas.get(nome_lista, [])
          if not itens:
              return _resp(f"{nome_lista}. Lista vazia. Diga voltar.",
                            end=False, session=session)
          partes = [f"{i}: {it.get('conteudo', '?')}" for i, it in enumerate(itens, 1)]
          texto = (
              f"Lista {nome_lista}. {len(itens)} ite{'m' if len(itens) == 1 else 'ns'}. "
              f"{'. '.join(partes)}. "
              f"Diga o numero para ouvir e editar. "
              "Diga repetir ou voltar."
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
              return _resp(f"Esse numero nao existe. Ha {len(itens)} itens. Qual?",
                            end=False, session=session)
          item = itens[numero - 1]
          nome_lista = session.get("nome_lista", "")
          texto = (
              f"Item {numero}: {item.get('conteudo', '?')}. "
              f"Adicionado em {item.get('adicionado_em', '?')}. "
              f"1 para remover este item. "
              f"2 para editar o conteudo. "
              "Diga repetir ou voltar."
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
              return _resp(f"Esse numero nao existe. Ha {len(docs)} documentos. Qual?",
                            end=False, session=session)
          doc = docs[numero - 1]
          titulo = _titulo_curto(doc.get("titulo", "Sem titulo"))
          url = doc.get("url_audio", "")
          if url:
              _registrar_uso(titulo, "play")
              return _build_audio(titulo, url)
          return _resp(f"{titulo} nao tem audio disponivel. Escolha outro ou diga voltar.",
                        end=False, session=session)

      # ---------- YouTube: submenu ----------
      if menu_tipo == "youtube":
          if numero == NUM_REPETIR:
              return _resp(
                  "YouTube e Videos. 1 para Ultimas Atualizacoes YT. "
                  "2 para Pesquisar no YouTube. 3 para Meus Canais. "
                  "Diga repetir ou voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          if numero == 1:
              return _resp(
                  "Ultimas Atualizacoes de YouTube ainda nao disponivel. "
                  "Diga outro numero ou diga voltar.",
                  end=False, session=session)
          if numero == 2:
              return _resp(
                  "Pesquisa no YouTube ainda nao disponivel. "
                  "Diga outro numero ou diga voltar.",
                  end=False, session=session)
          if numero == 3:
              return _resp(
                  "Meus Canais ainda nao disponivel. "
                  "Diga outro numero ou diga voltar.",
                  end=False, session=session)
          return _resp("Essa opcao nao existe. 1 para Atualizacoes. 2 para Pesquisar. 3 para Canais.",
                        end=False, session=session)

      # ---------- Configuracoes: submenu principal ----------
      if menu_tipo == "configuracoes":
          if numero == NUM_REPETIR:
              return _resp(
                  "Configuracoes. 1 para Velocidade da Fala. 2 para Guia do Usuario. "
                  "Diga repetir ou voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _voltar_nivel_anterior(session)
          if numero == 1:
              return _menu_config_velocidades(session)
          if numero == 2:
              return _resp(
                  "Guia do Usuario. Voce pode ouvir o menu de ajuda dizendo: Alexa, ajuda. "
                  "Diga repetir ou voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          return _resp("Essa opcao nao existe. 1 para Velocidade. 2 para Guia.",
                        end=False, session=session)

      # ---------- Configuracoes: escolher velocidade ----------
      if menu_tipo == "config_velocidades":
          if numero == NUM_REPETIR:
              return _menu_config_velocidades(session)
          if numero == NUM_VOLTAR:
              return _resp(
                  "Configuracoes. 1 para Velocidade da Fala. 2 para Guia do Usuario. "
                  "Diga repetir ou voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          velocidades_nomes  = ["Muito Devagar", "Devagar", "Normal", "Rapido", "Muito Rapido"]
          velocidades_chaves = ["muito_devagar", "devagar", "normal", "rapido", "muito_rapido"]
          if not (1 <= numero <= len(velocidades_nomes)):
              return _resp(f"Essa opcao nao existe. Escolha entre 1 e {len(velocidades_nomes)}.",
                            end=False, session=session)
          vel_nome  = velocidades_nomes[numero - 1]
          vel_chave = velocidades_chaves[numero - 1]
          # Salva velocidade na sessao: _resp vai usar SSML automaticamente
          new_session = {**session, "nivel": "submenu", "menu_tipo": "configuracoes", "velocidade": vel_chave}
          return _resp(
              f"Velocidade {vel_nome} ativada para esta sessao. "
              "Os menus e textos serao falados nessa velocidade. "
              "Para audiobooks gravados (MP3), a velocidade nao pode ser alterada em tempo real. "
              "Diga voltar.",
              end=False, session=new_session)

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
          cap_data = progresso.get(livro_base, None)
          cap_salvo = cap_data.get("cap_idx") if isinstance(cap_data, dict) else cap_data
          offset_salvo = cap_data.get("offset_ms", 0) if isinstance(cap_data, dict) else 0

          if numero == NUM_REPETIR:
              opcao_continuar = f"2 para Continuar do Capitulo {cap_salvo + 1}. " if (cap_salvo is not None and cap_salvo > 0) else ""
              return _resp(
                  f"{titulo}. 1 para Comecar do Inicio. {opcao_continuar}"
                  "3 para Escolher Capitulo. 4 para Sinopse. "
                  "Diga repetir ou voltar.",
                  end=False, session=session)

          if numero == NUM_VOLTAR:
              # Volta para lista de livros PRESERVANDO pagina atual (fix F1)
              if _obter_json(session, "livros_dados"):
                  mostrar = session.get("mostrar_ja_lidos") == "true"
                  return _render_pagina_livros(session, mostrar_ja_lidos=mostrar)
              # Fallback: remonta do zero se livros_dados perdido
              categoria_nome = session.get("livros_categoria", "")
              todos_docs = _obter_json(session, "todos_docs") or []
              cat_info = next((c for c in LIVROS_CATEGORIAS if c["nome"] == categoria_nome), None)
              cat_filtro = cat_info["filtro"] if cat_info else "Livros"
              docs_livros = [d for d in todos_docs if d.get("categoria","") == cat_filtro]
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
                      return _build_audio(cap_titulo, url, token=token, session_extra=new_session, total_capitulos=len(capitulos))
              return _resp(f"{titulo} nao tem audio disponivel.", end=False, session=session)

          if numero == 2:
              # Continuar do capitulo salvo, no offset salvo (rebobinado REWIND_MS)
              if cap_salvo is not None and capitulos and cap_salvo < len(capitulos):
                  cap = capitulos[cap_salvo]
                  url = cap.get("url_audio", "")
                  cap_titulo = _titulo_curto(cap.get("titulo", f"Capitulo {cap_salvo + 1}"))
                  if url:
                      _registrar_uso(titulo, "play_livro_continuar")
                      token = f"{livro_base}{TOKEN_SEPARADOR}{cap_salvo}"
                      new_session = {**session, "capitulo_atual": str(cap_salvo)}
                      offset_resume = max(0, int(offset_salvo) - REWIND_MS)
                      return _build_audio(
                          cap_titulo, url,
                          token=token, session_extra=new_session,
                          total_capitulos=len(capitulos),
                          offset_ms=offset_resume,
                      )
              return _resp(
                  f"Nenhum progresso salvo para {titulo}. Diga 1 para comecar do inicio. "
                  "Diga voltar.",
                  end=False, session=session)

          if numero == 3:
              # Listar capitulos para escolher
              partes = []
              for i, cap in enumerate(capitulos, 1):
                  partes.append(f"{i}. {_titulo_curto(cap.get('titulo', f'Capitulo {i}'))}")
              texto = (
                  f"{titulo}. {len(capitulos)} capitulos. "
                  f"{'. '.join(partes)}. "
                  "Diga repetir ou voltar. "
                  "Qual capitulo quer ouvir?"
              )
              return _resp(texto, end=False,
                            session={**session, "nivel": "submenu", "menu_tipo": "livros_capitulos"})

          if numero == 4:
              # Sinopse do livro (campo 'sinopse' ou mensagem padrao)
              if capitulos:
                  sinopse = capitulos[0].get("sinopse", "Sinopse nao disponivel para este livro.")
              else:
                  sinopse = "Sinopse nao disponivel."
              return _resp(
                  f"Sinopse de {titulo}. {sinopse}. "
                  "1 para Comecar a Ler. "
                  "Diga repetir ou voltar.",
                  end=False, session=session)

          # Numero >= 5 dentro do submenu Livros = troca de livro (eco prometeu essa opcao)
          if numero >= 5:
              new_session = {**session, "nivel": "submenu"}
              return _selecionar_submenu(numero, new_session)

          return _resp(
              "Essa opcao nao existe. 1 para inicio. 2 para continuar. 3 para capitulos. 4 para sinopse. "
              "Ou diga outro numero a partir de 5 para escolher outro livro. "
              "Diga voltar.",
              end=False, session=session)

      # ---------- Calendario: editar ou remover compromisso ----------
      if menu_tipo == "calendario":
          comp = _obter_json(session, "item_dados") or {}
          if numero == 1:
              # Editar: pergunta qual campo
              texto = (
                  f"Editar compromisso: {comp.get('titulo', '?')}. "
                  f"Qual campo? 1 para titulo. 2 para data. 3 para hora. 4 para descricao. "
                  "Diga repetir ou voltar."
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
          return _resp("Essa opcao nao existe. 1 para editar. 2 para remover.",
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
                  "Diga repetir ou voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _menu_reunioes(session)
          if numero == 1:
              resumo = reu.get("resumo", "Sem resumo disponivel.")
              return _resp(
                  f"Resumo em topicos frasais da reuniao {titulo_reu}. {resumo}. "
                  "Diga repetir ou voltar.",
                  end=False, session={**session, "nivel": "item", "menu_tipo": "reunioes"})
          if numero == 2:
              resumo = reu.get("resumo", "Sem resumo disponivel.")
              return _resp(
                  f"Resumo pragmatico da reuniao {titulo_reu}. {resumo}. "
                  "Diga repetir ou voltar.",
                  end=False, session={**session, "nivel": "item", "menu_tipo": "reunioes"})
          if numero == 3:
              transcricao = reu.get("transcricao", "")
              if transcricao:
                  return _resp(
                      f"Audio na integra da reuniao {titulo_reu}. {transcricao[:3000]}. "
                      "Diga repetir ou voltar.",
                      end=False, session={**session, "nivel": "item", "menu_tipo": "reunioes"})
              return _resp(
                  f"Transcricao nao disponivel para {titulo_reu}. "
                  "1 para topicos frasais. 2 para resumo pragmatico. "
                  "Diga repetir ou voltar.",
                  end=False, session=session)
          return _resp(
              "Essa opcao nao existe. 1 para topicos frasais. 2 para resumo pragmatico. 3 para audio na integra. "
              "Diga repetir ou voltar.",
              end=False, session=session)

      # ---------- Favoritos: remover ----------
      if menu_tipo == "favoritos_item":
          if numero == 1:
              item = _obter_json(session, "item_dados") or {}
              return _resp(
                  f"Item '{item.get('titulo', '?')}' removido dos favoritos. "
                  "Diga voltar.",
                  end=False,
                  session={**session, "nivel": "menu", "acao_pendente": "remover_favorito"})
          return _resp("1 para remover. Ou diga voltar.",
                        end=False, session=session)

      # ---------- Listas: remover ou editar ----------
      if menu_tipo == "listas_item":
          if numero == 1:
              item = _obter_json(session, "item_dados") or {}
              return _resp(
                  f"Item '{item.get('conteudo', '?')}' removido da lista. "
                  "Diga voltar.",
                  end=False,
                  session={**session, "nivel": "menu", "acao_pendente": "remover_lista_item"})
          if numero == 2:
              return _resp(
                  "Para editar um item, use o aplicativo no celular por enquanto. "
                  "Diga voltar.",
                  end=False, session={**session, "nivel": "menu"})
          return _resp("1 para remover. 2 para editar.", end=False, session=session)

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
              "Diga voltar.",
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
    "livros":              None if len(LIVROS_CATEGORIAS) <= 1 else "livros_categorias",
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
          cat_filtro = cat_info["filtro"] if cat_info else "Livros"
          docs_livros = [d for d in todos_docs if d.get("categoria","") == cat_filtro]
          return _menu_livros(docs_livros, session, categoria_nome=categoria_nome)
      if menu_tipo == "musicas":
          return _menu_musicas(session)
      if menu_tipo == "configuracoes":
          return _resp(
              "Configuracoes. 1 para Velocidade da Fala. 2 para Guia do Usuario. "
              "Diga repetir ou voltar.",
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
          "Diga repetir ou voltar. "
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
      return _resp(f"{titulo} sem audio. Escolha outro ou diga voltar.", end=False, session=session)


def _handle_ajuda(session):
      """P2f (S246): ajuda contextual — re-apresenta o menu/lista do estado atual.
      Cobre 11 estados via _reconstruir_menu. Buracos conhecidos (arestas futuras):
      nivel=item livros (livro selecionado), livros_capitulos, nivel=item reunioes.
      """
      menu_tipo = session.get("menu_tipo", "")
      nivel = session.get("nivel", "menu")
      # Estado raiz: menu principal
      if nivel == "menu" or not menu_tipo:
          return _voltar_menu_principal(session)
      # Demais estados: re-renderiza o menu/lista atual
      return _reconstruir_menu(menu_tipo, session)


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
                       "musica", "calendario", "reunioes", "listas_mentais",
                       "youtube"):
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
          "Diga repetir ou voltar. Qual numero?"
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
              return int(valor)
      except (ValueError, TypeError) as e:
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
          # Fonte 1: inputTranscript contem o texto bruto da fala do usuario
          raw = event.get("request", {}).get("intent", {}).get("slots", {}).get("numero", {}).get("value", "") or ""
          # Fonte 2: tenta slots genericos
          if not raw:
              for slot_name, slot_data in event.get("request", {}).get("intent", {}).get("slots", {}).items():
                  if isinstance(slot_data, dict):
                      raw = slot_data.get("value", "") or ""
                      if raw:
                          break
          logger.info(f"Fallback raw input: {raw}")

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


def _build_audio(titulo, url_audio, token=None, session_extra=None, total_capitulos=None, offset_ms=0):
      """Reproduz um MP3 via AudioPlayer.
      token: identificador do audio, usado para pular capitulos (livro_base|||cap_idx)
      session_extra: atributos de sessao a preservar (obs: Alexa encerra sessao durante audio)
      total_capitulos: se informado, anuncia "Capitulo X de Y" (evita HTTP extra)
      offset_ms: posicao em ms onde comecar (default 0). Usado pelo ResumeIntent.
      """
      _registrar_uso(titulo, "play")
      audio_token = token or titulo
      fala = f"Reproduzindo {titulo}"
      if total_capitulos and token and TOKEN_SEPARADOR in token:
          try:
              cap_idx = int(token.split(TOKEN_SEPARADOR)[1])
              fala = f"Capitulo {cap_idx + 1} de {total_capitulos}. {titulo}"
          except Exception:
              pass
      # Resposta completa: metadata (display Echo Show) + sessionAttributes (Resume entre capitulos)
      resposta = {
          "version": "1.0",
          "response": {
              "outputSpeech": {"type": "PlainText", "text": fala},
              "directives": [{
                  "type": "AudioPlayer.Play",
                  "playBehavior": "REPLACE_ALL",
                  "audioItem": {
                      "stream": {
                          "url": url_audio,
                          "token": audio_token,
                          "offsetInMilliseconds": int(offset_ms),
                      },
                      "metadata": {
                          "title": titulo,
                          "subtitle": "Caxinguele Audiobooks",
                      }
                  }
              }],
              "shouldEndSession": True,
          }
      }
      if session_extra:
          resposta["sessionAttributes"] = session_extra
      return resposta
