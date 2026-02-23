"""
Monitor de Gmail — Projeto Caxinguele v2

Verifica emails nao lidos em tororocaxinguele@gmail.com e permite
converter o conteudo em audiobook via pipeline existente.

Fluxo:
  1. Usuario clica "Verificar Emails" na GUI
  2. Busca emails nao lidos (Gmail API via OAuth2)
  3. Mostra lista para selecao
  4. Usuario escolhe -> baixa como .eml -> passa ao pipeline
  5. Marca email como lido apos processar

Autenticacao: usa o mesmo credentials.json do Google Drive,
mas com escopo de Gmail (token salvo em token_gmail.json).
Na primeira vez, abre o navegador para autorizar acesso ao Gmail.

REQUISITO: Gmail API deve estar habilitada no Google Cloud Console
(mesma conta/projeto do Drive).
"""

import base64
import logging
import re
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
from datetime import datetime

from config import BASE_DIR

logger = logging.getLogger(__name__)

# Credenciais e token separado do Drive
CREDENTIALS_FILE = BASE_DIR / "client_secrets.json"
GMAIL_TOKEN_FILE = BASE_DIR / "token_gmail.json"

# Email do projeto
EMAIL_PROJETO = "tororocaxinguele@gmail.com"

# Cores (mesmas do app)
C = {
    "bg":      "#0f1117",
    "painel":  "#1a1d27",
    "borda":   "#2a2d3e",
    "acento":  "#6c63ff",
    "ok":      "#43d98c",
    "erro":    "#ff5370",
    "aviso":   "#ffcb6b",
    "texto":   "#e8eaf6",
    "texto2":  "#8b8fa8",
    "entrada": "#252836",
}


# ==================== AUTENTICACAO ====================

def obter_servico_gmail():
    """
    Autentica no Gmail via OAuth2.
    Usa credentials.json (mesmo do Drive) mas token separado.
    Na primeira vez abre navegador para autorizar.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Pacote google-api-python-client nao encontrado.\n"
            "Execute: pip install google-api-python-client google-auth-oauthlib"
        )

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"client_secrets.json nao encontrado em: {CREDENTIALS_FILE}\n"
            "Baixe o arquivo do Google Cloud Console e salve em: {CREDENTIALS_FILE}"
        )

    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    creds = None

    if GMAIL_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(GMAIL_TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        logger.info("Token Gmail salvo.")

    from googleapiclient.discovery import build
    return build('gmail', 'v1', credentials=creds)


# ==================== OPERACOES GMAIL ====================

def listar_emails_novos(max_emails=20):
    """
    Lista emails nao lidos.
    Retorna lista de dicts com id, de, assunto, data, snippet.
    """
    service = obter_servico_gmail()

    result = service.users().messages().list(
        userId='me',
        q='is:unread',
        maxResults=max_emails
    ).execute()

    mensagens = result.get('messages', [])
    emails = []

    for msg in mensagens:
        try:
            detalhe = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = {
                h['name']: h['value']
                for h in detalhe.get('payload', {}).get('headers', [])
            }

            emails.append({
                'id': msg['id'],
                'de': _limpar_remetente(headers.get('From', '?')),
                'assunto': headers.get('Subject', '(sem assunto)'),
                'data': _formatar_data(headers.get('Date', '')),
                'snippet': detalhe.get('snippet', ''),
            })
        except Exception as e:
            logger.warning(f"Erro ao ler email {msg['id']}: {e}")

    return emails


def baixar_email_como_eml(msg_id):
    """
    Baixa email completo no formato RFC2822 (.eml).
    Salva na pasta temp/ e retorna o caminho.
    """
    service = obter_servico_gmail()

    msg = service.users().messages().get(
        userId='me',
        id=msg_id,
        format='raw'
    ).execute()

    raw = base64.urlsafe_b64decode(msg['raw'])

    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eml_path = temp_dir / f"email_{timestamp}.eml"
    eml_path.write_bytes(raw)

    logger.info(f"Email baixado: {eml_path}")
    return eml_path


def marcar_como_lido(msg_id):
    """Marca email como lido (remove label UNREAD)"""
    try:
        service = obter_servico_gmail()
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        logger.info(f"Email {msg_id} marcado como lido.")
    except Exception as e:
        logger.warning(f"Nao foi possivel marcar email como lido: {e}")


def _limpar_remetente(de):
    """Extrai apenas o nome/email do campo From"""
    # Remove aspas e pega nome antes do email
    m = re.match(r'^"?([^"<]+)"?\s*<?', de)
    if m:
        nome = m.group(1).strip()
        if nome:
            return nome[:40]
    return de[:40]


def _formatar_data(data_str):
    """Formata data do email para exibicao"""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(data_str)
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return data_str[:10] if data_str else "?"


def assunto_como_nome(assunto):
    """Converte assunto do email em nome para o audiobook"""
    # Remove prefixos Re:, Fwd:, etc.
    assunto = re.sub(r'^(Re|Fwd?|FW|RES|ENC):\s*', '', assunto, flags=re.IGNORECASE)
    assunto = re.sub(r'\s+', ' ', assunto).strip()
    return assunto or "Email sem assunto"


# ==================== DIALOG DE SELECAO ====================

class DialogVerificarEmails:
    """Janela para listar e selecionar emails para converter"""

    def __init__(self, parent, callback_selecao):
        """
        parent: janela pai
        callback_selecao(eml_path, nome_sugerido): chamado ao selecionar email
        """
        self.parent = parent
        self.callback = callback_selecao
        self.emails = []

        self.win = tk.Toplevel(parent)
        self.win.title("Emails Recebidos — tororocaxinguele@gmail.com")
        self.win.geometry("720x460")
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.minsize(560, 360)

        self._construir_interface()
        # Carrega emails em thread para nao travar a UI
        threading.Thread(target=self._carregar_emails, daemon=True).start()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["ok"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="EMAILS NAO LIDOS",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")

        self.label_status = tk.Label(inner,
                 text="Conectando ao Gmail...",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"])
        self.label_status.pack(anchor="w")

        # Tabela de emails
        frame_tree = tk.Frame(self.win, bg=C["bg"])
        frame_tree.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        style = ttk.Style()
        style.configure("Gmail.Treeview",
                        background=C["entrada"],
                        foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10),
                        rowheight=28)
        style.configure("Gmail.Treeview.Heading",
                        background=C["painel"],
                        foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Gmail.Treeview",
                  background=[("selected", C["acento"])])

        colunas = ("data", "de", "assunto")
        self.tree = ttk.Treeview(frame_tree, columns=colunas,
                                  show="headings", height=10,
                                  style="Gmail.Treeview",
                                  selectmode="browse")

        self.tree.heading("data", text="Data")
        self.tree.heading("de", text="De")
        self.tree.heading("assunto", text="Assunto")

        self.tree.column("data", width=85, minwidth=70, anchor="center")
        self.tree.column("de", width=180, minwidth=100)
        self.tree.column("assunto", width=360, minwidth=200)

        scroll = ttk.Scrollbar(frame_tree, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self._converter_selecionado())

        # Preview do assunto/snippet
        frame_prev = tk.Frame(self.win, bg=C["entrada"], padx=12, pady=6)
        frame_prev.pack(fill="x", padx=16, pady=(8, 0))

        self.label_snippet = tk.Label(frame_prev, text="Selecione um email para ver o preview",
                 font=("Segoe UI", 9),
                 bg=C["entrada"], fg=C["texto2"],
                 wraplength=660, justify="left", anchor="w")
        self.label_snippet.pack(anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self._on_selecao)

        # Botoes
        frame_btn = tk.Frame(self.win, bg=C["bg"])
        frame_btn.pack(fill="x", padx=16, pady=(10, 12))

        tk.Button(frame_btn, text="Converter para Audiobook",
                  command=self._converter_selecionado,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=16, pady=6,
                  activebackground="#35c07a"
                  ).pack(side="right")

        tk.Button(frame_btn, text="Atualizar Lista",
                  command=lambda: threading.Thread(
                      target=self._carregar_emails, daemon=True).start(),
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  activebackground=C["entrada"]
                  ).pack(side="right", padx=(0, 8))

        tk.Button(frame_btn, text="Fechar",
                  command=self.win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6
                  ).pack(side="left")

    def _carregar_emails(self):
        """Carrega emails em thread separada"""
        self.win.after(0, lambda: self.label_status.config(
            text="Buscando emails...", fg=C["aviso"]))

        try:
            self.emails = listar_emails_novos()

            def atualizar_tree():
                self.tree.delete(*self.tree.get_children())
                if not self.emails:
                    self.label_status.config(
                        text="Nenhum email nao lido.", fg=C["texto2"])
                    return

                for i, em in enumerate(self.emails):
                    self.tree.insert("", "end", iid=str(i),
                                   values=(em['data'], em['de'], em['assunto']))

                self.label_status.config(
                    text=f"{len(self.emails)} email(s) nao lido(s). Duplo-clique para converter.",
                    fg=C["ok"])

            self.win.after(0, atualizar_tree)

        except Exception as e:
            msg = str(e)
            if "gmail" in msg.lower() or "api" in msg.lower():
                msg = ("Gmail API nao habilitada no Google Cloud Console.\n"
                       "Habilite em: console.cloud.google.com -> APIs -> Gmail API -> Ativar")
            self.win.after(0, lambda: self.label_status.config(
                text=f"Erro: {msg[:80]}", fg=C["erro"]))

    def _on_selecao(self, event):
        """Mostra preview do email selecionado"""
        sel = self.tree.selection()
        if sel:
            idx = int(sel[0])
            em = self.emails[idx]
            snippet = em.get('snippet', '')
            self.label_snippet.config(
                text=f"Assunto: {em['assunto']}\nPreview: {snippet[:120]}...")

    def _converter_selecionado(self):
        """Baixa email selecionado e passa ao pipeline"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um email.", parent=self.win)
            return

        idx = int(sel[0])
        em = self.emails[idx]
        nome_sugerido = assunto_como_nome(em['assunto'])

        self.label_status.config(text="Baixando email...", fg=C["aviso"])

        def baixar_e_processar():
            try:
                eml_path = baixar_email_como_eml(em['id'])
                marcar_como_lido(em['id'])

                # Chama callback na thread principal
                self.win.after(0, lambda: self._concluir(eml_path, nome_sugerido))

            except Exception as e:
                self.win.after(0, lambda: self.label_status.config(
                    text=f"Erro ao baixar: {e}", fg=C["erro"]))

        threading.Thread(target=baixar_e_processar, daemon=True).start()

    def _concluir(self, eml_path, nome_sugerido):
        """Fecha dialog e chama callback com o arquivo baixado"""
        self.win.destroy()
        self.callback(eml_path, nome_sugerido)


def abrir_verificar_emails(parent, callback_selecao):
    """Abre a janela de verificacao de emails"""
    DialogVerificarEmails(parent, callback_selecao)
