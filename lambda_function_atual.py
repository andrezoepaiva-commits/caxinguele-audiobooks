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
      {"numero": 6, "nome": "Reunioes Caxinguele",             "tipo": "reunioes"},
      {"numero": 7, "nome": "Organizacoes da Mente em Listas", "tipo": "listas_mentais"},
      {"numero": 8, "nome": "Configuracoes",                   "tipo": "configuracoes"},
      {"numero": 9, "nome": "Voltar ao Menu Principal",        "tipo": "voltar_menu"},
]

# Numeros especiais reservados para navegacao
NUM_REPETIR = 98
NUM_VOLTAR  = 99


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
          else:
              return _resp("Desculpe, nao entendi.")

      except Exception as e:
          logger.error(f"ERRO CRITICO: {str(e)}", exc_info=True)
          return _resp("Houve um erro. Tente novamente.", end=True)


# ==================== LAUNCH ====================

def handle_launch(event):
      """Abertura: mostra menu principal (nivel 1)"""
      documentos, menu = _buscar_dados_completos()

      texto = _enumerar_menu_principal(menu, documentos)
      session = {
          "nivel":     "menu",
          "todos_docs": json.dumps(documentos),
          "menu":       json.dumps(menu),
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
      if intent_name == "AMAZON.HelpIntent":
          return _handle_ajuda(session)
      if intent_name in ("ListarDocumentosIntent", "AMAZON.NavigateHomeIntent"):
          return _voltar_menu_principal(session)

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
          return _voltar_menu_principal(session)

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

      # ---------- Menu 2: Livros ----------
      if tipo == "filtro":
          cat_filtro = cat.get("categoria", nome)
          livros = [d for d in todos_docs if d.get("categoria", "") == cat_filtro]
          if not livros:
              return _resp(f"Nao ha livros catalogados no momento. Diga outro numero.",
                            end=False, session=session)
          return _menu_livros(livros, session)

      # ---------- Menu 3: Favoritos ----------
      if tipo == "favoritos":
          return _menu_favoritos(session)

      # ---------- Menu 4: Musica ----------
      if tipo == "musica":
          return _menu_musicas(session)

      # ---------- Menu 5: Calendario e Compromissos ----------
      if tipo == "calendario":
          return _menu_calendario(session)

      # ---------- Menu 8: Reunioes Caxinguele ----------
      if tipo == "reunioes":
          return _menu_reunioes(session)

      # ---------- Menu 9: Configuracoes ----------
      if tipo == "configuracoes":
          return _resp(
              f"{nome}. 1 para Escolher Voz. 2 para Velocidade da Fala. "
              "3 para Guia do Usuario. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
              end=False,
              session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})

      # ---------- Menu 7: Listas Mentais ----------
      if tipo == "listas_mentais":
          return _menu_listas(session)

      # ---------- Menu 8: Configuracoes ----------
      # (handler ja existente, mantido abaixo)

      # ---------- Menu 9: Voltar ao Menu Principal ----------
      if tipo == "voltar_menu":
          return _voltar_menu_principal(session)

      # Fallback: tipo desconhecido
      return _resp(f"{nome}. Este menu ainda nao esta disponivel por voz. Diga outro numero.",
                    end=False, session=session)


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


def _menu_musicas(session):
      """Lista musicas Caxinguele numeradas."""
      musicas = [m for m in MUSICAS_CAXINGUELE if m.get("url")]
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

def _menu_livros(livros, session):
      """Lista livros catalogados numerados. Amigo escolhe → opcoes de leitura."""
      partes = []
      for i, livro in enumerate(livros, 1):
          titulo = _titulo_curto(livro.get("titulo", "Sem titulo"))
          partes.append(f"{i}. {titulo}")

      texto = (
          f"Livros. Voce tem {len(livros)} livro{'s' if len(livros) > 1 else ''} catalogado{'s' if len(livros) > 1 else ''}. "
          f"{'. '.join(partes)}. "
          f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar. "
          "Qual livro quer ouvir?"
      )
      new_session = {
          **session,
          "nivel":     "submenu",
          "menu_tipo": "livros",
          "livros":    json.dumps(livros),
      }
      return _resp(texto, end=False, reprompt="Diga o numero do livro.", session=new_session)


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
              return _build_audio(titulo, url)
          return _resp(f"{titulo} ainda nao disponivel. Diga outro numero.", end=False, session=session)

      # ---------- Livros: amigo escolheu livro → opcoes de leitura ----------
      if menu_tipo == "livros":
          livros = _obter_json(session, "livros") or []
          if numero == NUM_REPETIR:
              return _menu_livros(livros, session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          if not (1 <= numero <= len(livros)):
              return _resp(
                  f"Numero invalido. Ha {len(livros)} livros. Diga um numero entre 1 e {len(livros)}. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          livro = livros[numero - 1]
          titulo = _titulo_curto(livro.get("titulo", "Sem titulo"))
          # Verifica se tem capitulo salvo para continuar
          capitulo_salvo = session.get("capitulo_salvo_" + str(numero - 1), "")
          opcao_continuar = f"2 para Continuar do Capitulo {capitulo_salvo}. " if capitulo_salvo else ""
          texto = (
              f"{titulo}. O que quer fazer? "
              "1 para Comecar a Ler do Inicio. "
              f"{opcao_continuar}"
              "3 para Sinopse do Livro. "
              "4 para Adicionar aos Favoritos. "
              "5 para Compartilhar. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar."
          )
          new_session = {
              **session,
              "nivel":        "item",
              "menu_tipo":    "livros",
              "item_idx":     str(numero - 1),
              "item_dados":   json.dumps(livro),
              "livro_titulo": titulo,
          }
          return _resp(texto, end=False, session=new_session)

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
                  "Configuracoes. 1 para Escolher Voz. 2 para Velocidade da Fala. 3 para Guia do Usuario. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              return _voltar_menu_principal(session)
          if numero == 1:
              return _menu_config_vozes(session)
          if numero == 2:
              return _menu_config_velocidades(session)
          if numero == 3:
              return _resp(
                  "Guia do Usuario. Voce pode ouvir o menu de ajuda dizendo: Alexa, pede ajuda na super alexa. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          return _resp("Opcao invalida. 1 para Voz. 2 para Velocidade. 3 para Guia.",
                        end=False, session=session)

      # ---------- Configuracoes: escolher voz ----------
      if menu_tipo == "config_vozes":
          if numero == NUM_REPETIR:
              return _menu_config_vozes(session)
          if numero == NUM_VOLTAR:
              return _resp(
                  "Configuracoes. 1 para Escolher Voz. 2 para Velocidade da Fala. 3 para Guia do Usuario. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          nomes_vozes = ["Camila", "Vitoria", "Thiago", "Francisca", "Thalita", "Antonio"]
          if not (1 <= numero <= len(nomes_vozes)):
              return _resp(f"Opcao invalida. Escolha entre 1 e {len(nomes_vozes)}.",
                            end=False, session=session)
          voz_escolhida = nomes_vozes[numero - 1]
          return _resp(
              f"Voz {voz_escolhida} selecionada. "
              "Para ativar, acesse Configuracoes da Alexa no aplicativo, va em Voz da Alexa e escolha {voz_escolhida}. "
              f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
              end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})

      # ---------- Configuracoes: escolher velocidade ----------
      if menu_tipo == "config_velocidades":
          if numero == NUM_REPETIR:
              return _menu_config_velocidades(session)
          if numero == NUM_VOLTAR:
              return _resp(
                  "Configuracoes. 1 para Escolher Voz. 2 para Velocidade da Fala. 3 para Guia do Usuario. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
          velocidades = ["Muito Devagar", "Devagar", "Normal", "Rapido", "Muito Rapido"]
          if not (1 <= numero <= len(velocidades)):
              return _resp(f"Opcao invalida. Escolha entre 1 e {len(velocidades)}.",
                            end=False, session=session)
          vel_escolhida = velocidades[numero - 1]
          return _resp(
              f"Velocidade {vel_escolhida} selecionada. "
              "Para aplicar, acesse as Configuracoes da Alexa no aplicativo e ajuste a velocidade da voz. "
              f"{NUM_VOLTAR} para voltar.",
              end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})

      # Fallback
      return _resp("Nao entendi. Diga o numero ou diga voltar.",
                    end=False, session=session)


# ==================== NIVEL: ITEM (ACOES) ====================

def _selecionar_acao_item(numero, session):
      """Amigo esta vendo detalhes de um item e escolheu uma acao."""
      menu_tipo = session.get("menu_tipo", "")

      # ---------- Livros: amigo escolheu acao ----------
      if menu_tipo == "livros":
          livro = _obter_json(session, "item_dados") or {}
          titulo = session.get("livro_titulo", livro.get("titulo", "?"))
          url = livro.get("url_audio", "")
          item_idx = session.get("item_idx", "0")
          if numero == NUM_REPETIR:
              capitulo_salvo = session.get("capitulo_salvo_" + item_idx, "")
              opcao_continuar = f"2 para Continuar do Capitulo {capitulo_salvo}. " if capitulo_salvo else ""
              return _resp(
                  f"{titulo}. 1 para Comecar do Inicio. {opcao_continuar}"
                  "3 para Sinopse. 4 para Favoritos. 5 para Compartilhar. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == NUM_VOLTAR:
              livros = _obter_json(session, "livros") or []
              return _menu_livros(livros, session)
          if numero == 1:
              # Comecar do inicio
              if url:
                  _registrar_uso(titulo, "play_livro_inicio")
                  new_session = {**session, "capitulo_atual": "1"}
                  return _build_audio(titulo, url)
              return _resp(f"{titulo} nao tem audio disponivel.", end=False, session=session)
          if numero == 2:
              # Continuar do capitulo salvo
              capitulo_salvo = session.get("capitulo_salvo_" + item_idx, "")
              if capitulo_salvo and url:
                  _registrar_uso(titulo, "play_livro_continuar")
                  return _build_audio(f"{titulo} — Capitulo {capitulo_salvo}", url)
              return _resp(
                  f"Nenhum progresso salvo para {titulo}. Diga 1 para comecar do inicio. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == 3:
              sinopse = livro.get("sinopse", "Sinopse nao disponivel para este livro.")
              return _resp(
                  f"Sinopse de {titulo}. {sinopse}. "
                  "1 para Comecar a Ler. "
                  f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          if numero == 4:
              return _resp(
                  f"{titulo} adicionado aos Favoritos. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session={**session, "acao_pendente": "favoritar_livro"})
          if numero == 5:
              return _resp(
                  f"Para compartilhar {titulo}, acesse o aplicativo Caxinguele no celular. "
                  f"{NUM_VOLTAR} para voltar.",
                  end=False, session=session)
          return _resp(
              "Opcao invalida. 1 para ler. 3 para sinopse. 4 para favoritos. "
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
      }
      return _resp(texto, end=False, reprompt="Diga o numero.", session=new_session)


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
                       "musica", "calendario", "reunioes", "listas_mentais"):
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
      response = {
          "version": "1.0",
          "response": {
              "outputSpeech": {"type": "PlainText", "text": text},
              "shouldEndSession": end,
          }
      }
      if reprompt:
          response["response"]["reprompt"] = {
              "outputSpeech": {"type": "PlainText", "text": reprompt}
          }
      if session:
          response["sessionAttributes"] = session
      return response


def _build_audio(titulo, url_audio):
      _registrar_uso(titulo, "play")
      return {
          "version": "1.0",
          "response": {
              "outputSpeech": {"type": "PlainText", "text": f"Reproduzindo {titulo}"},
              "directives": [{
                  "type": "AudioPlayer.Play",
                  "playBehavior": "REPLACE_ALL",
                  "audioItem": {
                      "stream": {
                          "url": url_audio,
                          "token": titulo,
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
