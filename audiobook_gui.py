"""
Interface grafica do sistema PDF2Audiobook - Projeto Caxinguele
Converte PDFs em audiobooks e publica automaticamente no Spotify via Alexa
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

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
}

ETAPAS = [
    "Lendo PDF",
    "Processando",
    "Gerando Audio",
    "Google Drive",
    "Publicando",
]


class AudiobookGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Projeto Caxinguele  |  Audiobooks para Alexa")
        self.root.geometry("820x720")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)
        self.root.minsize(700, 600)

        self.fila = queue.Queue()
        self.processando = False
        self.pdf_selecionado = None
        self.inicio_conversao = None
        self.etapa_atual = -1
        self.total_caps = 0
        self.caps_feitos = 0

        self._construir_interface()
        self._verificar_sistema_async()
        self.root.after(100, self._processar_fila)

    # ──────────────────────────── INTERFACE ────────────────────────────

    def _construir_interface(self):
        # ---------- HEADER ----------
        header = tk.Frame(self.root, bg=C["painel"], pady=0)
        header.pack(fill="x")

        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=20, pady=14)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="PROJETO CAXINGUELE",
                 font=("Segoe UI", 16, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner, text="Sistema de Audiobooks para Alexa  •  Powered by Edge-TTS + Amazon Music",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Status dot
        self.dot_status = tk.Label(inner, text="● Pronto",
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

        # Coluna esquerda: formulario
        col_esq = tk.Frame(corpo, bg=C["bg"])
        col_esq.pack(fill="both", expand=True)

        # -- PDF --
        self._secao(col_esq, "1   Selecionar PDF")

        frame_pdf = tk.Frame(col_esq, bg=C["bg"])
        frame_pdf.pack(fill="x", pady=(4, 0))

        self.label_pdf = tk.Label(
            frame_pdf,
            text="Nenhum arquivo selecionado...",
            font=("Segoe UI", 10), anchor="w",
            bg=C["entrada"], fg=C["texto2"],
            padx=12, pady=9, relief="flat"
        )
        self.label_pdf.pack(side="left", fill="x", expand=True)

        tk.Button(frame_pdf, text="  Abrir PDF  ",
                  command=self._selecionar_pdf,
                  bg=C["acento"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=4, pady=5,
                  activebackground="#5a52e0",
                  activeforeground="white"
                  ).pack(side="right", padx=(8, 0))

        # -- NOME --
        self._secao(col_esq, "2   Nome do livro  (aparece na Alexa)")

        self.entry_nome = tk.Entry(
            col_esq,
            font=("Segoe UI", 11),
            bg=C["entrada"], fg=C["texto"],
            insertbackground=C["texto"],
            relief="flat", bd=0
        )
        self.entry_nome.pack(fill="x", ipady=8, pady=(4, 0))

        # -- OPCOES --
        self._secao(col_esq, "3   Opcoes")

        frame_ops = tk.Frame(col_esq, bg=C["bg"])
        frame_ops.pack(fill="x", pady=(4, 0))

        self.var_drive = tk.BooleanVar(value=True)
        self.var_github = tk.BooleanVar(value=True)

        self._checkbox(frame_ops, "Subir para Google Drive", self.var_drive)
        self._checkbox(frame_ops, "Publicar RSS no GitHub", self.var_github)

        # -- BOTAO --
        tk.Frame(col_esq, bg=C["bg"], height=14).pack()

        self.btn_converter = tk.Button(
            col_esq,
            text="▶   CONVERTER E PUBLICAR",
            command=self._iniciar_conversao,
            bg=C["acento"], fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            pady=13,
            activebackground="#5a52e0",
            activeforeground="white"
        )
        self.btn_converter.pack(fill="x")

        # -- PROGRESSO --
        frame_prog = tk.Frame(col_esq, bg=C["bg"])
        frame_prog.pack(fill="x", pady=(8, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("cax.Horizontal.TProgressbar",
                        troughcolor=C["borda"],
                        background=C["acento"],
                        thickness=6)

        self.barra_var = tk.IntVar(value=0)
        self.barra = ttk.Progressbar(frame_prog,
                                     mode="determinate",
                                     variable=self.barra_var,
                                     maximum=100,
                                     style="cax.Horizontal.TProgressbar")
        self.barra.pack(fill="x")

        frame_info = tk.Frame(col_esq, bg=C["bg"])
        frame_info.pack(fill="x", pady=(5, 0))

        self.label_status = tk.Label(frame_info, text="Aguardando...",
                                     font=("Segoe UI", 9),
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

        # -- RSS URL -- (aparece após conversão)
        self.frame_rss = tk.Frame(col_esq, bg=C["entrada"],
                                  highlightbackground=C["ok"],
                                  highlightthickness=1)

        frame_rss_inner = tk.Frame(self.frame_rss, bg=C["entrada"])
        frame_rss_inner.pack(fill="x", padx=10, pady=8)

        tk.Label(frame_rss_inner, text="RSS gerado — siga os passos abaixo:",
                 font=("Segoe UI", 8, "bold"),
                 bg=C["entrada"], fg=C["ok"]).pack(anchor="w")

        # Linha 1: Amazon Music
        tk.Label(frame_rss_inner, text="1. Abra o site do Amazon Music:",
                 font=("Segoe UI", 8),
                 bg=C["entrada"], fg=C["texto2"]).pack(anchor="w", pady=(6, 0))

        frame_amazon_url = tk.Frame(frame_rss_inner, bg=C["entrada"])
        frame_amazon_url.pack(fill="x", pady=(2, 0))

        entry_amazon = tk.Entry(
            frame_amazon_url,
            font=("Consolas", 8),
            bg=C["log_bg"], fg=C["ok"],
            relief="flat", bd=0
        )
        entry_amazon.insert(0, "podcasters.amazon.com")
        entry_amazon.bind("<Key>", lambda e: "break")
        entry_amazon.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))

        tk.Button(frame_amazon_url, text="Copiar",
                  command=lambda: (self.root.clipboard_clear(), self.root.clipboard_append("https://podcasters.amazon.com")),
                  bg=C["aviso"], fg=C["bg"],
                  font=("Segoe UI", 8, "bold"),
                  relief="flat", cursor="hand2",
                  padx=8, pady=3,
                  activebackground="#e6b800"
                  ).pack(side="right")

        # Linha 2: URL do RSS
        tk.Label(frame_rss_inner, text="2. Cole o RSS do livro convertido:",
                 font=("Segoe UI", 8),
                 bg=C["entrada"], fg=C["texto2"]).pack(anchor="w", pady=(8, 0))

        frame_rss_url = tk.Frame(frame_rss_inner, bg=C["entrada"])
        frame_rss_url.pack(fill="x", pady=(2, 0))

        self.entry_rss = tk.Entry(
            frame_rss_url,
            font=("Consolas", 8),
            bg=C["log_bg"], fg=C["ok"],
            insertbackground=C["ok"],
            relief="flat", bd=0
        )
        self.entry_rss.bind("<Key>", lambda e: "break")
        self.entry_rss.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))

        tk.Button(frame_rss_url, text="Copiar",
                  command=self._copiar_rss,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 8, "bold"),
                  relief="flat", cursor="hand2",
                  padx=8, pady=3,
                  activebackground="#35c07a"
                  ).pack(side="right")

        # Esconde o frame RSS inicialmente
        self.frame_rss.pack(fill="x", pady=(8, 0))
        self.frame_rss.pack_forget()

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
                 text="Projeto Caxinguele  •  Voz: Thalita (pt-BR)  •  Drive + Amazon Music + Alexa",
                 font=("Segoe UI", 8), bg=C["painel"], fg=C["texto2"]).pack()

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

            num = "✓" if i < ativa else str(i + 1)
            tk.Label(f, text=num,
                     font=("Segoe UI", 8, "bold"),
                     bg=cor_circ, fg="white",
                     width=2, pady=2).pack(side="left")

            tk.Label(f, text=f" {nome} ",
                     font=("Segoe UI", 9),
                     bg=C["bg"], fg=cor_txt).pack(side="left")

            if i < len(ETAPAS) - 1:
                tk.Label(self.frame_etapas, text="→",
                         font=("Segoe UI", 9),
                         bg=C["bg"], fg=C["borda"]).pack(side="left", padx=2)

    # ──────────────────────────── ACOES ────────────────────────────

    def _selecionar_pdf(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione o PDF",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if arquivo:
            self.pdf_selecionado = Path(arquivo)
            self.label_pdf.config(
                text=f"  {self.pdf_selecionado.name}",
                fg=C["texto"]
            )
            nome = self.pdf_selecionado.stem.replace("_", " ").replace("-", " ")
            self.entry_nome.delete(0, "end")
            self.entry_nome.insert(0, nome)

    def _iniciar_conversao(self):
        if self.processando:
            return

        if not self.pdf_selecionado:
            messagebox.showwarning("Aviso", "Selecione um arquivo PDF primeiro.")
            return

        nome = self.entry_nome.get().strip()
        if not nome:
            messagebox.showwarning("Aviso", "Digite o nome do livro.")
            return

        self.processando = True
        self.inicio_conversao = time.time()
        self.total_caps = 0
        self.caps_feitos = 0
        self.barra_var.set(0)
        self.btn_converter.config(state="disabled", text="⏳  Processando...")
        self.dot_status.config(text="● Convertendo", fg=C["acento"])
        self._desenhar_etapas(0)
        self._escrever_log("━" * 55, "dim")
        self._escrever_log(f"NOVO LIVRO: {nome}", "bold")
        self._escrever_log(f"Arquivo : {self.pdf_selecionado.name}", "dim")
        self._escrever_log(f"Opcoes  : Drive={self.var_drive.get()}  GitHub={self.var_github.get()}", "dim")
        self._atualizar_tempo()

        threading.Thread(
            target=self._executar_pipeline,
            args=(self.pdf_selecionado, nome),
            daemon=True
        ).start()

    def _executar_pipeline(self, pdf_path, nome_livro):
        def on_progresso(msg):
            # Detecta total de capitulos
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
                caminho_pdf=str(pdf_path),
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

    def _copiar_rss(self):
        url = self.entry_rss.get()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("Copiado", "URL do RSS copiada!\n\nCole em podcasters.amazon.com")

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
                    # Atualiza status com mensagem curta
                    if len(msg) > 4 and not msg.startswith("─") and not msg.startswith("━"):
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
                        # 0-100% = fase TTS ocupa 70% da barra (10% PDF, 70% TTS, 10% Drive, 10% RSS)
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
        # Não chamar barra.stop() — está em modo determinate, não tem efeito

        if sucesso:
            self.barra_var.set(100)
            self.label_pct.config(text="100%")
            self._desenhar_etapas(len(ETAPAS))
            self.dot_status.config(text="● Concluido", fg=C["ok"])
            self.btn_converter.config(
                state="normal",
                text="▶   CONVERTER E PUBLICAR",
                bg=C["ok"]
            )
            self.root.after(4000, lambda: self.btn_converter.config(bg=C["acento"]))
            nome = self.entry_nome.get().strip()
            tempo = int(time.time() - self.inicio_conversao) if self.inicio_conversao else 0
            mins = tempo // 60
            segs = tempo % 60
            tempo_str = f"{mins} min {segs}s" if mins > 0 else f"{segs} segundos"

            # Monta e exibe a URL do RSS
            from config import GITHUB_CONFIG
            nome_arquivo = nome.lower().replace(" ", "-")
            for char in '!@#$%^&*()+=[]{}|;:,.<>?/\\\'\"':
                nome_arquivo = nome_arquivo.replace(char, "")
            url_rss = f"{GITHUB_CONFIG['pages_url']}/{nome_arquivo}.xml"
            self.entry_rss.delete(0, "end")
            self.entry_rss.insert(0, url_rss)
            self.frame_rss.pack(fill="x", pady=(8, 0), before=self.frame_log_header)

            messagebox.showinfo("Publicado!",
                f"Livro disponivel na Alexa!\n\n"
                f"Diga: 'Alexa, toca {nome} no Amazon Music'\n\n"
                f"Tempo total: {tempo_str}")
        else:
            self._desenhar_etapas(-1)
            self.dot_status.config(text="● Erro - verifique o log", fg=C["erro"])
            self.btn_converter.config(state="normal", text="▶   CONVERTER E PUBLICAR")

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
