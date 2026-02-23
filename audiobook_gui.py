"""
Interface grafica do sistema Caxinguele v2
Converte documentos multi-formato em audiobooks para Alexa

Novidades v2:
  - Suporte multi-formato (PDF, DOCX, EPUB, TXT, Email, Imagem, etc.)
  - Drag-and-drop de arquivos na janela
  - Seletor de destinatario (Eu / Meu Amigo)
  - Icone visual por tipo detectado
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import sys
import time
import os
from pathlib import Path
from datetime import datetime

# Esconder janela preta do console no Windows
if sys.platform == "win32":
    try:
        import ctypes
        console_window = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window:
            ctypes.windll.user32.ShowWindow(console_window, 0)
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))

from doc_processor import FILTRO_EXTENSOES, formato_suportado
from doc_classifier import classificar_documento, ICONES_TIPO, NOMES_TIPO, obter_opcoes_tipo_gui
from config import PERFIS_USUARIOS, DESTINATARIO_PADRAO
from labirinto_ui import abrir_labirinto
from analytics_manager import abrir_analytics, registrar_envio
from gmail_monitor import abrir_verificar_emails

# ==================== CORES ====================

C = {
    "bg":         "#0f1117",
    "painel":     "#1a1d27",
    "borda":      "#2a2d3e",
    "acento":     "#6c63ff",
    "acento2":    "#ff6584",
    "ok":         "#43d98c",
    "erro":       "#ff5370",
    "aviso":      "#ffcb6b",
    "texto":      "#e8eaf6",
    "texto2":     "#8b8fa8",
    "entrada":    "#252836",
    "log_bg":     "#0a0c12",
    "log_info":   "#82aaff",
    "log_ok":     "#43d98c",
    "log_erro":   "#ff5370",
    "log_aviso":  "#ffcb6b",
    "log_dim":    "#4a4f6a",
    "etapa_ok":   "#43d98c",
    "etapa_ativa":"#6c63ff",
    "etapa_esp":  "#2a2d3e",
    "drop_ativo": "#1e2233",  # Cor quando arrasta arquivo sobre a janela
}

ETAPAS = [
    "Lendo Doc",
    "Processando",
    "Gerando Audio",
    "Enviando p/ Google Drive",
    "Publicando",
]


class AudiobookGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Projeto Caxinguele v2  |  Audiobooks para Alexa")
        self.root.geometry("820x780")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)
        self.root.minsize(700, 650)

        self.fila = queue.Queue()
        self.processando = False
        self.arquivo_selecionado = None  # Renomeado de pdf_selecionado
        self.tipo_detectado = None       # ClassificacaoDocumento
        self.inicio_conversao = None
        self.etapa_atual = -1
        self.total_caps = 0
        self.caps_feitos = 0

        self._construir_interface()
        self._configurar_drag_drop()
        self._verificar_sistema_async()
        self._iniciar_daemon_gmail()
        self.root.after(100, self._processar_fila)

    # ──────────────────────────── INTERFACE ────────────────────────────

    def _construir_interface(self):
        # ---------- HEADER ----------
        header = tk.Frame(self.root, bg=C["painel"], pady=0)
        header.pack(fill="x")

        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=20, pady=14)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="PROJETO CAXINGUELE v2",
                 font=("Segoe UI", 16, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner, text="Audiobooks para Alexa  |  PDF, Word, EPUB, Email, Imagem e mais",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Status dot
        self.dot_status = tk.Label(inner, text="Pronto",
                                   font=("Segoe UI", 9, "bold"),
                                   bg=C["painel"], fg=C["ok"])
        self.dot_status.pack(anchor="w", pady=(4, 0))

        # ---------- BARRA DE ETAPAS ----------
        self.frame_etapas = tk.Frame(self.root, bg=C["bg"], pady=12)
        self.frame_etapas.pack(fill="x", padx=20)
        self.labels_etapas = []
        self._desenhar_etapas(-1)

        # ---------- CORPO ----------
        corpo = tk.Frame(self.root, bg=C["bg"])
        corpo.pack(fill="both", expand=True, padx=20)

        col_esq = tk.Frame(corpo, bg=C["bg"])
        col_esq.pack(fill="both", expand=True)

        # -- SELECIONAR DOCUMENTO (com area de drag-drop) --
        self._secao(col_esq, "1   Selecionar Documento  (arraste ou clique)")

        # Area de drag-and-drop
        self.frame_drop = tk.Frame(col_esq, bg=C["entrada"],
                                   highlightbackground=C["borda"],
                                   highlightthickness=2,
                                   cursor="hand2")
        self.frame_drop.pack(fill="x", pady=(4, 0), ipady=12)

        self.label_drop_icone = tk.Label(
            self.frame_drop, text="",
            font=("Segoe UI", 18),
            bg=C["entrada"], fg=C["texto2"]
        )
        self.label_drop_icone.pack()

        self.label_arquivo = tk.Label(
            self.frame_drop,
            text="Arraste um arquivo aqui ou clique para selecionar",
            font=("Segoe UI", 10), anchor="center",
            bg=C["entrada"], fg=C["texto2"],
        )
        self.label_arquivo.pack()

        self.label_tipo = tk.Label(
            self.frame_drop,
            text="",
            font=("Segoe UI", 9),
            bg=C["entrada"], fg=C["acento"],
        )
        self.label_tipo.pack()

        # Clique na area de drop abre o seletor
        for widget in [self.frame_drop, self.label_drop_icone, self.label_arquivo, self.label_tipo]:
            widget.bind("<Button-1>", lambda e: self._selecionar_arquivo())

        # Botão principal: Enviar Documento
        frame_btn_abrir = tk.Frame(col_esq, bg=C["bg"])
        frame_btn_abrir.pack(fill="x", pady=(4, 0))

        tk.Button(frame_btn_abrir, text="  Enviar Documento  ",
                  command=self._selecionar_arquivo,
                  bg=C["acento"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=4, pady=5,
                  activebackground="#5a52e0",
                  activeforeground="white"
                  ).pack(side="right")

        # -- NOME --
        self._secao(col_esq, "2   Nome  (aparece na Alexa)")

        self.entry_nome = tk.Entry(
            col_esq,
            font=("Segoe UI", 11),
            bg=C["entrada"], fg=C["texto"],
            insertbackground=C["texto"],
            relief="flat", bd=0
        )
        self.entry_nome.pack(fill="x", ipady=8, pady=(4, 0))

        # -- OPCOES (sempre ativas, sem jargao tecnico) --
        self.var_drive = tk.BooleanVar(value=True)
        self.var_github = tk.BooleanVar(value=True)
        self.var_destinatario = tk.StringVar(value="amigo")

        # -- BOTAO --
        tk.Frame(col_esq, bg=C["bg"], height=10).pack()

        self.btn_converter = tk.Button(
            col_esq,
            text="CONVERTER E PUBLICAR",
            command=self._iniciar_conversao,
            bg=C["acento"], fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            pady=13,
            activebackground="#5a52e0",
            activeforeground="white"
        )
        self.btn_converter.pack(fill="x")

        # Botões secundários — linha 1
        frame_secundario1 = tk.Frame(col_esq, bg=C["bg"])
        frame_secundario1.pack(fill="x", pady=(6, 0))

        tk.Button(frame_secundario1, text="Labirinto de Números",
                  command=self._abrir_labirinto,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  activebackground=C["entrada"],
                  activeforeground=C["texto"]
                  ).pack(side="left")

        tk.Button(frame_secundario1, text="Analytics",
                  command=self._abrir_analytics,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  activebackground=C["entrada"],
                  activeforeground=C["texto"]
                  ).pack(side="left", padx=(6, 0))

        tk.Button(frame_secundario1, text="Histórico",
                  command=self._abrir_historico,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  activebackground=C["entrada"],
                  activeforeground=C["texto"]
                  ).pack(side="left", padx=(6, 0))

        # Botões secundários — linha 2
        frame_secundario2 = tk.Frame(col_esq, bg=C["bg"])
        frame_secundario2.pack(fill="x", pady=(6, 0))

        tk.Button(frame_secundario2, text="Gerenciar Equipe",
                  command=self._abrir_gerenciar_equipe,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  activebackground=C["entrada"],
                  activeforeground=C["texto"]
                  ).pack(side="left", padx=(6, 0))


        # -- PROGRESSO --
        frame_prog = tk.Frame(col_esq, bg=C["bg"])
        frame_prog.pack(fill="x", pady=(8, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("cax.Horizontal.TProgressbar",
                        troughcolor=C["borda"],
                        background=C["acento"],
                        thickness=14)

        self.barra_var = tk.IntVar(value=0)
        self.barra = ttk.Progressbar(frame_prog,
                                     mode="determinate",
                                     variable=self.barra_var,
                                     maximum=100,
                                     style="cax.Horizontal.TProgressbar")
        self.barra.pack(fill="x")

        frame_info = tk.Frame(col_esq, bg=C["bg"])
        frame_info.pack(fill="x", pady=(5, 0))

        self.label_status = tk.Label(frame_info, text="Pronto para converter",
                                     font=("Segoe UI", 10, "bold"),
                                     bg=C["bg"], fg=C["texto2"], anchor="w")
        self.label_status.pack(side="left")

        self.label_pct = tk.Label(frame_info, text="",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=C["bg"], fg=C["acento"])
        self.label_pct.pack(side="right", padx=(0, 8))

        self.label_tempo = tk.Label(frame_info, text="",
                                    font=("Segoe UI", 9),
                                    bg=C["bg"], fg=C["texto2"], anchor="e")
        self.label_tempo.pack(side="right")

        # Placeholder para referencia (removido: antigo RSS/Amazon Music section)

        # -- LOG --
        self.frame_log_header = tk.Frame(col_esq, bg=C["bg"])
        self.frame_log_header.pack(fill="x", pady=(14, 3))

        tk.Label(self.frame_log_header, text="LOG DO SISTEMA",
                 font=("Segoe UI", 8, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(side="left")

        tk.Button(self.frame_log_header, text="Copiar Log",
                  command=self._copiar_log,
                  bg=C["borda"], fg=C["texto2"],
                  font=("Segoe UI", 8),
                  relief="flat", cursor="hand2",
                  padx=8, pady=2,
                  activebackground=C["entrada"]
                  ).pack(side="right")

        tk.Button(self.frame_log_header, text="Limpar",
                  command=self._limpar_log,
                  bg=C["borda"], fg=C["texto2"],
                  font=("Segoe UI", 8),
                  relief="flat", cursor="hand2",
                  padx=8, pady=2,
                  activebackground=C["entrada"]
                  ).pack(side="right", padx=(0, 6))

        frame_log = tk.Frame(col_esq, bg=C["log_bg"],
                             highlightbackground=C["borda"],
                             highlightthickness=1)
        frame_log.pack(fill="both", expand=True, pady=(0, 16))

        self.log_text = tk.Text(
            frame_log,
            bg=C["log_bg"], fg=C["log_info"],
            font=("Consolas", 9),
            relief="flat", state="disabled",
            wrap="word", padx=10, pady=8,
            selectbackground=C["acento"]
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(frame_log, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroll.set)

        self.log_text.tag_config("ok",    foreground=C["log_ok"])
        self.log_text.tag_config("erro",  foreground=C["log_erro"])
        self.log_text.tag_config("aviso", foreground=C["log_aviso"])
        self.log_text.tag_config("info",  foreground=C["log_info"])
        self.log_text.tag_config("dim",   foreground=C["log_dim"])
        self.log_text.tag_config("bold",  font=("Consolas", 9, "bold"))

        # ---------- FOOTER ----------
        footer = tk.Frame(self.root, bg=C["painel"], pady=7)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer,
                 text="Projeto Caxinguele v2  |  Voz: Thalita (pt-BR)  |  Skill Alexa: Meus Audiobooks",
                 font=("Segoe UI", 8), bg=C["painel"], fg=C["texto2"]).pack()

    # ──────────────────────────── DRAG AND DROP ────────────────────────────

    def _configurar_drag_drop(self):
        """Configura drag-and-drop usando tkinterdnd2 (se disponivel)"""
        try:
            # Tenta importar tkinterdnd2 para drag-and-drop nativo
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
            self.root.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.root.dnd_bind('<<DragLeave>>', self._on_drag_leave)
            self._escrever_log("Drag-and-drop ativado", "dim")
        except (ImportError, Exception):
            # tkinterdnd2 nao disponivel - funciona sem drag-drop
            # Nao precisa mostrar erro, o botao "Abrir" funciona normalmente
            pass

    def _on_drag_enter(self, event):
        """Visual feedback quando arquivo entra na janela"""
        self.frame_drop.config(highlightbackground=C["acento"], highlightthickness=3)
        self.label_arquivo.config(text="Solte o arquivo aqui!", fg=C["acento"])

    def _on_drag_leave(self, event):
        """Volta ao visual normal"""
        self.frame_drop.config(highlightbackground=C["borda"], highlightthickness=2)
        if not self.arquivo_selecionado:
            self.label_arquivo.config(
                text="Arraste um arquivo aqui ou clique para selecionar",
                fg=C["texto2"]
            )

    def _on_drop(self, event):
        """Processa arquivo solto na janela"""
        # tkinterdnd2 retorna o caminho entre chaves no Windows
        caminho = event.data.strip()
        if caminho.startswith('{') and caminho.endswith('}'):
            caminho = caminho[1:-1]

        # Se soltou multiplos arquivos, pega o primeiro
        if '\n' in caminho:
            caminho = caminho.split('\n')[0].strip()

        caminho = Path(caminho)

        # Volta visual normal
        self.frame_drop.config(highlightbackground=C["borda"], highlightthickness=2)

        if caminho.exists() and formato_suportado(caminho):
            self._definir_arquivo(caminho)
        else:
            self.label_arquivo.config(
                text=f"Formato nao suportado: {caminho.suffix}",
                fg=C["erro"]
            )
            self.root.after(3000, lambda: self.label_arquivo.config(
                text="Arraste um arquivo aqui ou clique para selecionar",
                fg=C["texto2"]
            ))

    # ──────────────────────────── HELPERS DE UI ────────────────────────────

    def _secao(self, parent, texto):
        tk.Label(parent, text=texto,
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(14, 0))

    def _checkbox(self, parent, texto, var):
        tk.Checkbutton(parent, text=texto, variable=var,
                       bg=C["bg"], fg=C["texto"],
                       selectcolor=C["entrada"],
                       activebackground=C["bg"],
                       font=("Segoe UI", 10),
                       cursor="hand2"
                       ).pack(side="left", padx=(0, 20))

    def _desenhar_etapas(self, ativa):
        for w in self.frame_etapas.winfo_children():
            w.destroy()
        self.labels_etapas = []

        for i, nome in enumerate(ETAPAS):
            cor_circ = C["etapa_ok"] if i < ativa else (C["etapa_ativa"] if i == ativa else C["etapa_esp"])
            cor_txt  = C["texto"] if i <= ativa else C["texto2"]

            f = tk.Frame(self.frame_etapas, bg=C["bg"])
            f.pack(side="left")

            num = "V" if i < ativa else str(i + 1)
            tk.Label(f, text=num,
                     font=("Segoe UI", 8, "bold"),
                     bg=cor_circ, fg="white",
                     width=2, pady=2).pack(side="left")

            tk.Label(f, text=f" {nome} ",
                     font=("Segoe UI", 9),
                     bg=C["bg"], fg=cor_txt).pack(side="left")

            if i < len(ETAPAS) - 1:
                tk.Label(self.frame_etapas, text="->",
                         font=("Segoe UI", 9),
                         bg=C["bg"], fg=C["borda"]).pack(side="left", padx=2)

    # ──────────────────────────── ACOES ────────────────────────────

    def _selecionar_arquivo(self):
        """Abre seletor de arquivo multi-formato"""
        arquivo = filedialog.askopenfilename(
            title="Selecione o documento",
            filetypes=FILTRO_EXTENSOES
        )
        if arquivo:
            self._definir_arquivo(Path(arquivo))

    def _definir_arquivo(self, caminho: Path):
        """Define o arquivo selecionado e detecta tipo"""
        self.arquivo_selecionado = caminho

        # Atualiza visual da area de drop
        self.label_arquivo.config(
            text=f"  {caminho.name}",
            fg=C["texto"]
        )

        # Detecta tipo
        self.tipo_detectado = classificar_documento(caminho)
        self.label_drop_icone.config(text=self.tipo_detectado.icone)
        self.label_tipo.config(
            text=f"Tipo: {self.tipo_detectado.nome}  ({self.tipo_detectado.confianca:.0%} confianca)",
            fg=C["acento"]
        )

        # Auto-preenche nome
        nome = caminho.stem.replace("_", " ").replace("-", " ")
        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, nome)

        self._escrever_log(
            f"Arquivo: {caminho.name}  |  Tipo: {self.tipo_detectado.icone} {self.tipo_detectado.nome}",
            "info"
        )

    def _iniciar_conversao(self):
        if self.processando:
            return

        if not self.arquivo_selecionado:
            messagebox.showwarning("Aviso", "Selecione um documento primeiro.")
            return

        nome = self.entry_nome.get().strip()
        if not nome:
            messagebox.showwarning("Aviso", "Digite o nome do documento.")
            return

        self.processando = True
        self.inicio_conversao = time.time()
        self.total_caps = 0
        self.caps_feitos = 0
        self.barra_var.set(0)
        self.btn_converter.config(state="disabled", text="Processando...")
        self.dot_status.config(text="Convertendo", fg=C["acento"])
        self._desenhar_etapas(0)
        self._escrever_log("-" * 55, "dim")
        self._escrever_log(f"NOVO: {nome}", "bold")
        self._escrever_log(f"Arquivo : {self.arquivo_selecionado.name}", "dim")
        if self.tipo_detectado:
            self._escrever_log(f"Tipo    : {self.tipo_detectado.icone} {self.tipo_detectado.nome}", "dim")
        self._escrever_log("Destino : Alexa do Amigo", "dim")
        self._atualizar_tempo()

        threading.Thread(
            target=self._executar_pipeline,
            args=(self.arquivo_selecionado, nome),
            daemon=True
        ).start()

    def _executar_pipeline(self, doc_path, nome_livro):
        def on_progresso(msg):
            import re
            m = re.search(r"Total de arquivos.*?(\d+)", str(msg))
            if m:
                self.fila.put(("total_caps", int(m.group(1))))
            self.fila.put(("log", msg))

        def on_percentual(feitos, total):
            self.fila.put(("percentual", (feitos, total)))

        try:
            from pipeline_mvp import executar_pipeline_completo
            resultado = executar_pipeline_completo(
                caminho_pdf=str(doc_path),  # Nome mantido por compatibilidade
                nome_livro=nome_livro,
                fazer_upload=self.var_drive.get(),
                publicar_rss=self.var_github.get(),
                callback_progresso=on_progresso,
                callback_percentual=on_percentual
            )
            self.fila.put(("concluido", resultado))
        except Exception as e:
            import traceback
            self.fila.put(("log_erro", f"[ERRO] {e}"))
            self.fila.put(("log_erro", traceback.format_exc()))
            self.fila.put(("concluido", False))

    def _copiar_log(self):
        conteudo = self.log_text.get("1.0", "end")
        self.root.clipboard_clear()
        self.root.clipboard_append(conteudo)
        messagebox.showinfo("Copiado", "Log copiado para a area de transferencia!")

    def _limpar_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _atualizar_tempo(self):
        if self.processando and self.inicio_conversao:
            decorrido = int(time.time() - self.inicio_conversao)
            mins = decorrido // 60
            segs = decorrido % 60

            pct = self.barra_var.get()
            if pct > 5:
                total_est = decorrido * 100 / pct
                resta = int(total_est - decorrido)
                rm = resta // 60
                rs = resta % 60
                self.label_tempo.config(text=f"Decorrido: {mins:02d}:{segs:02d}  |  Faltam ~{rm:02d}:{rs:02d}")
            else:
                self.label_tempo.config(text=f"Decorrido: {mins:02d}:{segs:02d}")

            self.root.after(1000, self._atualizar_tempo)
        else:
            self.label_tempo.config(text="")

    # ──────────────────────────── LOG ────────────────────────────

    def _escrever_log(self, msg, tag="info"):
        self.log_text.config(state="normal")
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{hora}] ", "dim")
        self.log_text.insert("end", f"{msg}\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _processar_fila(self):
        try:
            while True:
                tipo, dado = self.fila.get_nowait()

                if tipo == "log":
                    msg = str(dado)
                    if "[OK]" in msg or "concluido" in msg.lower() or "sucesso" in msg.lower():
                        tag = "ok"
                    elif "[ERRO]" in msg or "erro" in msg.lower() or "falha" in msg.lower():
                        tag = "erro"
                    elif "[AVISO]" in msg or "aviso" in msg.lower():
                        tag = "aviso"
                    elif msg.startswith("=") or msg.startswith("ETAPA"):
                        tag = "bold"
                    else:
                        tag = "info"
                    self._escrever_log(msg, tag)
                    if len(msg) > 4 and not msg.startswith("-") and not msg.startswith("="):
                        self.label_status.config(text=msg[:70])

                elif tipo == "log_ok":
                    self._escrever_log(dado, "ok")
                elif tipo == "log_erro":
                    self._escrever_log(dado, "erro")
                elif tipo == "log_aviso":
                    self._escrever_log(dado, "aviso")
                elif tipo == "status":
                    self.label_status.config(text=dado)
                elif tipo == "etapa":
                    self._desenhar_etapas(dado)
                elif tipo == "total_caps":
                    self.total_caps = dado
                    self._escrever_log(f"Total de capitulos: {dado}", "info")
                elif tipo == "percentual":
                    feitos, total = dado
                    self.caps_feitos = feitos
                    self.total_caps = total
                    if total > 0:
                        pct = int(feitos / total * 100)
                        pct_barra = 10 + int(feitos / total * 70)
                        self.barra_var.set(pct_barra)
                        self.label_pct.config(text=f"{pct}%  ({feitos}/{total} caps)")
                        self._desenhar_etapas(2)
                elif tipo == "concluido":
                    self._finalizar(dado)
        except queue.Empty:
            pass
        self.root.after(100, self._processar_fila)

    def _finalizar(self, sucesso):
        self.processando = False

        if sucesso:
            self.barra_var.set(100)
            self.label_pct.config(text="100%")
            self._desenhar_etapas(len(ETAPAS))
            self.dot_status.config(text="Concluido", fg=C["ok"])
            self.btn_converter.config(
                state="normal",
                text="CONVERTER E PUBLICAR",
                bg=C["ok"]
            )
            self.root.after(4000, lambda: self.btn_converter.config(bg=C["acento"]))
            nome = self.entry_nome.get().strip()
            tempo = int(time.time() - self.inicio_conversao) if self.inicio_conversao else 0
            mins = tempo // 60
            segs = tempo % 60
            tempo_str = f"{mins} min {segs}s" if mins > 0 else f"{segs} segundos"

            # Registra no analytics
            cat = self.tipo_detectado.nome if self.tipo_detectado else "Documentos"
            arq = str(self.arquivo_selecionado) if self.arquivo_selecionado else ""
            registrar_envio(nome, cat, arq, tempo)

            messagebox.showinfo("Publicado!",
                f"Documento disponivel na Alexa!\n\n"
                f"Diga: 'Alexa, abre meus audiobooks'\n"
                f"Depois escolha pelo numero.\n\n"
                f"Documento: {nome}\n"
                f"Tempo total: {tempo_str}")
        else:
            self._desenhar_etapas(-1)
            self.dot_status.config(text="Erro - verifique o log", fg=C["erro"])
            self.btn_converter.config(state="normal", text="CONVERTER E PUBLICAR")

    def _verificar_emails(self):
        """Abre dialog de emails recebidos em tororocaxinguele@gmail.com"""
        def on_email_selecionado(eml_path, nome_sugerido):
            self._definir_arquivo(eml_path)
            self.entry_nome.delete(0, "end")
            self.entry_nome.insert(0, nome_sugerido)
            self._escrever_log(f"Email carregado: {nome_sugerido}", "ok")

        abrir_verificar_emails(self.root, on_email_selecionado)

    def _abrir_labirinto(self):
        """Abre o Labirinto de Numeros da Alexa"""
        abrir_labirinto(self.root)

    def _abrir_analytics(self):
        """Abre o dashboard de analytics"""
        abrir_analytics(self.root)

    def _abrir_historico(self):
        """Abre o painel de histórico de documentos enviados"""
        from analytics_manager import abrir_historico
        abrir_historico(self.root)

    def _abrir_configuracoes_voz(self):
        """Abre o painel de configurações de voz"""
        from configuracoes_voz import abrir_configuracoes_voz
        abrir_configuracoes_voz(self.root)

    def _abrir_gerenciar_equipe(self):
        """Abre o painel de gerenciamento da equipe"""
        from gerenciar_equipe import abrir_gerenciar_equipe
        abrir_gerenciar_equipe(self.root)

    def _iniciar_daemon_gmail(self):
        """Inicia o daemon de automação de emails em background"""
        try:
            from gmail_daemon import ativar_daemon
            ativar_daemon()
        except Exception as e:
            pass  # Daemon é opcional, não bloqueia a app

    def _verificar_sistema_async(self):
        def verificar():
            try:
                from updater import executar_verificacao_completa
                executar_verificacao_completa(lambda m: self.fila.put(("log", m)))
            except Exception as e:
                self.fila.put(("log_aviso", f"Verificacao: {e}"))
        threading.Thread(target=verificar, daemon=True).start()


# ──────────────────────────── MAIN ────────────────────────────

def main():
    # Tenta usar tkinterdnd2.TkinterDnD para suporte drag-and-drop
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        # Sem drag-and-drop, funciona normalmente com botao "Abrir"
        root = tk.Tk()

    try:
        icon = Path(__file__).parent / "icon.ico"
        if icon.exists():
            root.iconbitmap(str(icon))
    except Exception:
        pass
    app = AudiobookGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
