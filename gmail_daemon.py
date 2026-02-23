"""
Gmail Daemon — Projeto Caxinguele v2
Monitora emails e converte automaticamente em audiobooks.

Funcionalidades:
- Roda em background
- Detecta novos emails de membros autorizados
- Converte para áudio (Edge-TTS)
- Publica no Labirinto automaticamente
- Aplica filtros inteligentes (sem spam, notificações, etc)
"""

import time
import threading
import json
import logging
from pathlib import Path
from datetime import datetime
from config import BASE_DIR
from gerenciar_equipe import carregar_equipe

# Setup logging
LOG_FILE = BASE_DIR / "logs" / "gmail_daemon.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

INDICE_PROCESSADO = BASE_DIR / "emails_processados.json"


def carregar_emails_processados():
    """Carrega lista de emails já processados"""
    if INDICE_PROCESSADO.exists():
        try:
            return json.loads(INDICE_PROCESSADO.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def salvar_emails_processados(emails: list):
    """Salva lista de emails processados"""
    INDICE_PROCESSADO.write_text(
        json.dumps(emails, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def eh_email_valido(email_obj, remetente_autorizado) -> bool:
    """
    Verifica se o email deve ser convertido.
    Filtra spam, notificações automáticas, etc.
    """
    assunto = email_obj.get("subject", "").lower()
    corpo = email_obj.get("body", "").lower()[:200]

    # Lista de palavras-chave de spam/notificação
    palavras_bloqueadas = [
        "unsubscribe", "not-reply", "noreply", "do not reply",
        "confirmação de entrega", "notificação", "atualização automática",
        "alerta", "aviso", "erro", "recibido", "bounce", "delivery status"
    ]

    for palavra in palavras_bloqueadas:
        if palavra in assunto or palavra in corpo:
            return False

    # Verifica se é de remetente autorizado
    if remetente_autorizado and email_obj.get("from") != remetente_autorizado:
        return False

    return True


def processar_email(email_id: str, remetente, assunto, corpo):
    """
    Processa um email: converte em áudio e publica.

    Returns: True se bem-sucedido
    """
    try:
        logging.info(f"Processando email: {assunto[:50]}")

        # TODO: Implementar conversão real
        # 1. Remover formatação HTML
        # 2. Chamar Edge-TTS para converter
        # 3. Adicionar ao indice.json com categoria "Emails"
        # 4. Publicar na skill Alexa

        logging.info(f"Email processado: {email_id}")
        return True

    except Exception as e:
        logging.error(f"Erro ao processar email: {e}")
        return False


class GmailDaemon:
    """Daemon que monitora Gmail e converte emails"""

    def __init__(self):
        self.ativo = False
        self.thread = None
        self.intervalo = 300  # Verifica a cada 5 minutos
        logging.info("Gmail Daemon inicializado")

    def iniciar(self):
        """Inicia o daemon em background"""
        if self.ativo:
            return

        self.ativo = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logging.info("Gmail Daemon iniciado")

    def parar(self):
        """Para o daemon"""
        self.ativo = False
        logging.info("Gmail Daemon parado")

    def _loop(self):
        """Loop principal do daemon"""
        emails_processados = carregar_emails_processados()

        while self.ativo:
            try:
                # TODO: Conectar ao Gmail usando OAuth2
                # emails_novos = self._buscar_emails_novos(emails_processados)

                # for email in emails_novos:
                #     if self._validar_email(email):
                #         if processar_email(email):
                #             emails_processados.append(email['id'])

                # salvar_emails_processados(emails_processados)

                time.sleep(self.intervalo)

            except Exception as e:
                logging.error(f"Erro no loop do daemon: {e}")
                time.sleep(60)

    def _buscar_emails_novos(self, ids_processados: list):
        """Busca novos emails não processados"""
        # TODO: Implementar busca real no Gmail
        return []

    def _validar_email(self, email_obj) -> bool:
        """Valida se o email deve ser processado"""
        equipe = carregar_equipe()
        emails_autorizados = {m.get("email") for m in equipe}

        return eh_email_valido(email_obj, emails_autorizados)


# Instância global
daemon = GmailDaemon()


def ativar_daemon():
    """Ativa o daemon globalmente"""
    daemon.iniciar()


def desativar_daemon():
    """Desativa o daemon globalmente"""
    daemon.parar()
