"""
Interface grafica do sistema Caxinguele v2
Converte documentos multi-formato em audiobooks para Alexa

Novidades v2:
  - Suporte multi-formato (PDF, DOCX, EPUB, TXT, Email, Imagem, etc.)
  - Drag-and-drop de arquivos na janela
  - Seletor de destinatario (Eu / Meu Amigo)
  - Icone visual por tipo detectado
"""

import json
import shutil
import subprocess
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
from enviar_musica_ui import abrir_enviar_musica

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


def _ler_todas_categorias():
    """Retorna as 7 categorias disponíveis na Alexa Skill.
    Tenta ler subcategorias de Livros do menus_config.json;
    as demais categorias são fixas (estrutura da skill)."""
    # Categorias fixas (refletem a estrutura dos menus da Alexa)
    categorias_fixas = [
        "Livros: Inteligência Sensorial",
        "Livros: Geral",
        "Salvos para Escutar Mais Tarde",
        "Notícias e Artigos Favoritados",
        "Emails Favoritados",
        "Documentos Importantes",
        "Últimas Atualizações",
    ]
    try:
        menus_path = Path(__file__).parent / "menus_config.json"
        with open(menus_path, encoding="utf-8") as f:
            menus = json.load(f)
        # Tenta pegar subcategorias de Livros dinamicamente
        for menu in menus:
            if menu.get("numero") == 2 and menu.get("tipo") == "filtro":
                cats_livros = [op["nome"] for op in menu.get("opcoes", [])]
                if cats_livros:
                    # Reconstrói a lista: cats de Livros + demais fixas
                    return cats_livros + [c for c in categorias_fixas
                                         if not c.startswith("Livros:")]
    except Exception:
        pass
    return categorias_fixas


class AudiobookGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Projeto Caxinguele v2  |  Audiobooks para Alexa")
        self.root.geometry("820x920")  # Aumentado para acomodar categoria + log visível
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)
        self.root.minsize(700, 700)

        self.fila = queue.Queue()
        self.processando = False
        self.arquivo_selecionado = None  # Renomeado de pdf_selecionado
        self.tipo_detectado = None       # ClassificacaoDocumento
        self.inicio_conversao = None
        self.etapa_atual = -1
        self.total_caps = 0
        self.caps_feitos = 0
        self.modo_livro = False    # True quando selecionada pasta com MP3s
        self.pasta_livro = None    # Path da pasta quando modo_livro=True

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

        tk.Label(inner, text="SUPER ALEXA",
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

        # Botões principais: Enviar Documento + Enviar Música (lado a lado)
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

        tk.Button(frame_btn_abrir, text="🎵 Enviar Música",
                  command=self._enviar_musica,
                  bg="#2a4a2a", fg=C["ok"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=4, pady=5,
                  activebackground="#1e3a1e",
                  activeforeground=C["ok"]
                  ).pack(side="right", padx=(0, 6))


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

        # -- CATEGORIA (sempre visível — sugestão automática pelo tipo detectado) --
        self.frame_categoria = tk.Frame(col_esq, bg=C["bg"])
        self.frame_categoria.pack(fill="x")

        self._lbl_cat = tk.Label(
            self.frame_categoria,
            text="3   Categoria  (onde aparece na Alexa)",
            font=("Segoe UI", 10, "bold"),
            bg=C["bg"], fg=C["texto2"]
        )
        self._lbl_cat.pack(anchor="w", pady=(10, 0))

        categorias = _ler_todas_categorias()
        self.var_categoria = tk.StringVar(value=categorias[0] if categorias else "")
        self._combo_categoria = ttk.Combobox(
            self.frame_categoria,
            textvariable=self.var_categoria,
            values=categorias,
            state="readonly",
            font=("Segoe UI", 10),
        )
        self._combo_categoria.pack(fill="x", ipady=4, pady=(4, 0))

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

        if caminho.is_dir():
            # Pasta arrastada → tenta modo livro (MP3s)
            self._definir_pasta(caminho)
        elif caminho.exists() and formato_suportado(caminho):
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
        # Reseta modo livro se estava ativo
        self.modo_livro = False
        self.pasta_livro = None

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

        # Sugere categoria automaticamente com base no tipo detectado
        self._sugerir_categoria(self.tipo_detectado.tipo)

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

        # Modo livro: pasta de MP3s → publicação direta (sem TTS)
        if self.modo_livro:
            self._iniciar_publicar_livro(nome)
            return

        # Modo normal: pipeline TTS completo
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

        # Para barra (seja determinada ou indeterminada)
        try:
            self.barra.stop()
        except Exception:
            pass
        self.barra.config(mode="determinate")

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

            if self.modo_livro:
                # Mensagem específica para livro com MP3s
                cat = self.var_categoria.get() if hasattr(self, "var_categoria") else "Livros"
                arq = str(self.pasta_livro) if self.pasta_livro else ""
                registrar_envio(nome, cat, arq, tempo)
                messagebox.showinfo("Livro Publicado! 📚",
                    f"'{nome}' está disponível na Alexa!\n\n"
                    f"Categoria: {cat}\n"
                    f"Diga: 'Alexa, abre meus audiobooks'\n"
                    f"Vá em Livros para encontrar.")
                self.modo_livro = False
                self.pasta_livro = None
            else:
                # Mensagem padrão para documentos
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

    def _selecionar_pasta(self):
        """Abre seletor de pasta para livros com MP3s."""
        pasta = filedialog.askdirectory(
            title="Selecionar Pasta com MP3s do Livro"
        )
        if pasta:
            self._definir_pasta(Path(pasta))

    def _definir_pasta(self, pasta: Path):
        """Define uma pasta de MP3s como fonte (modo livro)."""
        mp3s = sorted(pasta.glob("*.mp3"))
        if not mp3s:
            messagebox.showwarning("Aviso", f"Nenhum arquivo .mp3 encontrado em:\n{pasta.name}")
            return

        self.pasta_livro = pasta
        self.arquivo_selecionado = pasta  # para validação em _iniciar_conversao
        self.modo_livro = True

        # Atualiza área de drop visual
        self.label_drop_icone.config(text="📚")
        self.label_arquivo.config(
            text=f"  {pasta.name}  ({len(mp3s)} capítulos MP3)",
            fg=C["texto"]
        )
        self.label_tipo.config(
            text=f"Tipo: Livro — {len(mp3s)} capítulos prontos (sem conversão TTS)",
            fg=C["acento"]
        )

        # Auto-preenche nome a partir do nome da pasta
        nome = pasta.name.replace("_", " ").replace("-", " ")
        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, nome)

        # Sugere categoria Livros para pasta de MP3s
        self._sugerir_categoria("LIVRO")

        self._escrever_log(
            f"Pasta: {pasta.name}  |  {len(mp3s)} MP3s  |  Modo livro ativado",
            "info"
        )

    def _sugerir_categoria(self, tipo_documento: str):
        """Sugere categoria no dropdown com base no tipo de documento detectado.
        O usuário pode aceitar ou mudar manualmente."""
        # Mapa: TipoDocumento → categoria na Alexa
        mapa = {
            "LIVRO":             "Livros: Geral",
            "ARTIGO_CIENTIFICO": "Salvos para Escutar Mais Tarde",
            "EMAIL":             "Emails Favoritados",
            "DOCUMENTO_LEGAL":   "Documentos Importantes",
            "MATERIA_JORNAL":    "Notícias e Artigos Favoritados",
            "ARTIGO_NOTICIA":    "Notícias e Artigos Favoritados",
            "RELATORIO":         "Documentos Importantes",
            "OUTRO":             "Últimas Atualizações",
        }
        sugestao = mapa.get(tipo_documento, "Últimas Atualizações")

        # Só aplica se a categoria sugerida existir nas opções disponíveis
        opcoes = list(self._combo_categoria["values"])
        if sugestao in opcoes:
            self.var_categoria.set(sugestao)
        elif opcoes:
            self.var_categoria.set(opcoes[0])  # fallback para primeira opção

    def _iniciar_publicar_livro(self, nome: str):
        """Inicia publicação de livro (pasta MP3) sem pipeline TTS."""
        mp3s = sorted(self.pasta_livro.glob("*.mp3"))
        if not mp3s:
            messagebox.showwarning("Aviso", "Nenhum MP3 na pasta selecionada.")
            return

        categoria = self.var_categoria.get().strip()
        if not categoria:
            messagebox.showwarning("Aviso", "Selecione uma categoria para o livro.")
            return

        self.processando = True
        self.inicio_conversao = time.time()
        self.barra.config(mode="indeterminate")
        self.barra.start(12)
        self.barra_var.set(0)
        self.label_pct.config(text="")
        self.btn_converter.config(state="disabled", text="Publicando livro...")
        self.dot_status.config(text="Publicando", fg=C["acento"])
        self._desenhar_etapas(0)
        self._escrever_log("-" * 55, "dim")
        self._escrever_log(f"LIVRO: {nome}", "bold")
        self._escrever_log(f"Pasta   : {self.pasta_livro.name}", "dim")
        self._escrever_log(f"Categ.  : {categoria}", "dim")
        self._escrever_log(f"Caps.   : {len(mp3s)} MP3s", "dim")

        threading.Thread(
            target=self._publicar_livro_thread,
            args=(categoria, nome, mp3s),
            daemon=True
        ).start()

    def _sanitizar_categoria(self, categoria: str) -> str:
        """Remove caracteres inválidos de categoria para nomes de pasta.
        Ex: 'Livros: Geral' → 'Livros-Geral'"""
        # Windows não permite ':' em nomes de pasta
        return categoria.replace(": ", "-").replace(":", "-")

    def _publicar_livro_thread(self, categoria: str, nome_livro: str, mp3s: list):
        """Thread de publicação de livro (pasta MP3) — sem TTS."""
        from config import BASE_DIR, GDRIVE_CONFIG
        INDICE_JSON = BASE_DIR / "audiobooks" / "indice.json"

        def log(msg, tag="log"):
            self.fila.put((tag, msg))

        try:
            total = len(mp3s)

            # Passo 1: Copiar MP3s para pasta local
            log(f"[1/4] Copiando {total} MP3(s) para audiobooks/{nome_livro}/...")
            categoria_pasta = self._sanitizar_categoria(categoria)
            pasta_dest = BASE_DIR / "audiobooks" / categoria_pasta / nome_livro
            pasta_dest.mkdir(parents=True, exist_ok=True)
            for mp3 in mp3s:
                shutil.copy2(mp3, pasta_dest / mp3.name)

            # Passo 2: Upload para Google Drive
            log("[2/4] Conectando ao Google Drive...")
            from cloud_uploader import obter_servico_drive, obter_ou_criar_pasta, upload_arquivo
            service = obter_servico_drive()
            pasta_raiz_id = GDRIVE_CONFIG.get("pasta_raiz_id") or None

            pasta_livros_id = obter_ou_criar_pasta(service, "Audiobooks Caxinguele", pasta_raiz_id)
            pasta_cat_id = obter_ou_criar_pasta(service, categoria_pasta, pasta_livros_id)
            pasta_livro_id = obter_ou_criar_pasta(service, nome_livro, pasta_cat_id)

            urls_capitulos = []
            for i, mp3 in enumerate(mp3s, 1):
                log(f"[2/4] Upload capítulo {i}/{total}: {mp3.name}...")
                destino = pasta_dest / mp3.name
                resultado = upload_arquivo(service, destino, pasta_livro_id)
                if not resultado:
                    raise RuntimeError(f"Upload falhou para: {mp3.name}")
                urls_capitulos.append({"arquivo": mp3.name, "url": resultado["direct_url"]})

            # Passo 3: Atualizar indice.json
            log("[3/4] Atualizando indice.json...")
            dados = {"documentos": [], "total": 0, "versao": "2.0"}
            if INDICE_JSON.exists():
                with open(INDICE_JSON, encoding="utf-8") as f:
                    dados = json.load(f)

            hoje = datetime.now().strftime("%Y-%m-%d")
            # Extrai categoria base para Lambda (ex: "Livros: Geral" → "Livros")
            # Lambda LIVROS_CATEGORIAS filtra por "Livros", não por "Livros: Geral"
            categoria_base = categoria.split(":")[0].strip() if ":" in categoria else categoria

            # Remove entradas antigas do mesmo livro (evita duplicatas)
            dados["documentos"] = [
                d for d in dados.get("documentos", [])
                if not (d.get("titulo", "").startswith(nome_livro) and d.get("categoria") == categoria_base)
            ]
            for cap in urls_capitulos:
                dados["documentos"].append({
                    "titulo": f"{nome_livro} - {cap['arquivo'].replace('.mp3', '')}",
                    "url_audio": cap["url"],
                    "categoria": categoria_base,
                    "subcategoria": categoria,
                    "data": hoje,
                })
            dados["total"] = len(dados["documentos"])
            dados["atualizado_em"] = datetime.now().isoformat()

            INDICE_JSON.parent.mkdir(parents=True, exist_ok=True)
            with open(INDICE_JSON, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)

            # Passo 4: Git push
            log("[4/4] Publicando no GitHub Pages...")
            cwd = str(BASE_DIR)
            subprocess.run(["git", "add", "audiobooks/indice.json"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Livro: {nome_livro} — {hoje}"],
                cwd=cwd, check=True, capture_output=True
            )
            subprocess.run(["git", "push"], cwd=cwd, check=True, capture_output=True)

            log(f"✅ '{nome_livro}' ({total} caps) publicado na Alexa!", "log_ok")
            self.fila.put(("concluido", True))

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            if "nothing to commit" in stderr or "up to date" in stderr:
                log(f"✅ '{nome_livro}' publicado! (sem mudanças no git)", "log_ok")
                self.fila.put(("concluido", True))
            else:
                log(f"Erro no git push: {stderr}", "log_erro")
                self.fila.put(("concluido", False))
        except Exception as e:
            import traceback
            log(f"[ERRO] {e}", "log_erro")
            log(traceback.format_exc(), "log_erro")
            self.fila.put(("concluido", False))

    def _enviar_musica(self):
        """Abre o dialog para enviar uma música para a Alexa."""
        abrir_enviar_musica(self.root)

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
