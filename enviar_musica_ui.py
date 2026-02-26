"""
Janela de Upload de Música para a Alexa — Projeto Caxinguele v2

Fluxo:
  1. Usuário escolhe ONDE colocar (playlist existente ou nova)
  2. Usuário seleciona o ARQUIVO de música no PC (.mp3 / .wav)
  3. Clicar em Publicar:
     → Copia para musicas/<playlist>/
     → Upload para Google Drive
     → Atualiza musicas.json
     → Publica no GitHub Pages
     → Alexa já tem a música disponível
"""

import json
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

from config import BASE_DIR
from musica_ui import listar_playlists, criar_pasta_musicas, PASTA_MUSICAS

ARQUIVO_MUSICAS_JSON = BASE_DIR / "musicas.json"

# Playlists padrão (sempre disponíveis, mesmo se pasta vazia)
PLAYLISTS_PADRAO = [
    "Músicas Caxinguele",
    "Capoeira Regional",
    "Capoeira Angola",
    "Playlists Personalizadas",
]

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


class EnviarMusicaDialog:
    """Dialog de envio de música para a Alexa."""

    def __init__(self, parent):
        self.parent = parent
        self.arquivo_selecionado = None   # Path do arquivo no PC

        self.win = tk.Toplevel(parent)
        self.win.title("Enviar Música para a Alexa")
        self.win.geometry("650x700")
        self.win.configure(bg=C["bg"])
        self.win.resizable(False, False)
        self.win.transient(parent)  # Janela filha, mas permite diálogos de seleção
        self.win.focus_set()

        self._construir()

    # ─────────────────────── INTERFACE ───────────────────────

    def _construir(self):
        # ── Header ──
        header = tk.Frame(self.win, bg=C["painel"], pady=12)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left")
        tk.Label(inner, text="ENVIAR MÚSICA PARA A ALEXA",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner,
                 text="Selecione a playlist e o arquivo. A música ficará disponível na Alexa automaticamente.",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        corpo = tk.Frame(self.win, bg=C["bg"], padx=20, pady=16)
        corpo.pack(fill="both", expand=True)

        # ── Seção 1: Onde colocar ──
        tk.Label(corpo, text="1   Onde colocar no Labirinto?",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(anchor="w")

        tk.Label(corpo, text="Escolha a playlist ou crie uma nova:",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(2, 6))

        # Lista de playlists com radiobuttons
        frame_playlists = tk.Frame(corpo, bg=C["painel"], padx=12, pady=10)
        frame_playlists.pack(fill="x")

        self.var_playlist = tk.StringVar()

        # Playlists do disco que NÃO estão no padrão (playlists criadas pelo usuário)
        playlists_existentes = [p["nome"] for p in listar_playlists()]
        extras = [p for p in playlists_existentes if p not in PLAYLISTS_PADRAO]
        todas = PLAYLISTS_PADRAO + extras

        for pl in todas:
            rb = tk.Radiobutton(
                frame_playlists,
                text=f"  🎵  {pl}",
                variable=self.var_playlist,
                value=pl,
                bg=C["painel"], fg=C["texto"],
                activebackground=C["painel"],
                selectcolor=C["entrada"],
                font=("Segoe UI", 10),
                cursor="hand2",
                command=self._toggle_nova_playlist,
            )
            rb.pack(anchor="w", pady=2)

        # Opção: criar nova playlist
        rb_nova = tk.Radiobutton(
            frame_playlists,
            text="  ➕  Criar nova playlist...",
            variable=self.var_playlist,
            value="__nova__",
            bg=C["painel"], fg=C["aviso"],
            activebackground=C["painel"],
            selectcolor=C["entrada"],
            font=("Segoe UI", 10),
            cursor="hand2",
            command=self._toggle_nova_playlist,
        )
        rb_nova.pack(anchor="w", pady=2)

        # Campo para nome da nova playlist — fica DENTRO do frame_playlists
        # assim aparece logo abaixo do radiobutton sem problemas de reordenação
        self.frame_nova = tk.Frame(frame_playlists, bg=C["painel"])
        tk.Label(self.frame_nova, text="Nome da nova playlist:",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w", pady=(6, 2))
        self.entry_nova = tk.Entry(
            self.frame_nova,
            font=("Segoe UI", 10),
            bg=C["entrada"], fg=C["texto"],
            insertbackground=C["texto"],
            relief="flat", bd=0
        )
        self.entry_nova.pack(fill="x", ipady=6)
        # frame_nova começa oculto — NÃO chamamos pack() ainda

        # Seleciona primeira opção por padrão
        if todas:
            self.var_playlist.set(todas[0])

        tk.Frame(corpo, bg=C["bg"], height=14).pack()

        # ── Seção 2: Selecionar arquivo ──
        tk.Label(corpo, text="2   Arquivo de música no seu PC",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(anchor="w")
        tk.Label(corpo, text="Formatos aceitos: .mp3 · .wav · .ogg · .m4a",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(2, 6))

        frame_arquivo = tk.Frame(corpo, bg=C["painel"], padx=12, pady=10)
        frame_arquivo.pack(fill="x")

        self.label_arquivo = tk.Label(
            frame_arquivo,
            text="Nenhum arquivo selecionado",
            font=("Segoe UI", 10),
            bg=C["painel"], fg=C["texto2"],
            anchor="w",
        )
        self.label_arquivo.pack(side="left", fill="x", expand=True)

        tk.Button(
            frame_arquivo,
            text="Selecionar Arquivo",
            command=self._selecionar_arquivo,
            bg=C["borda"], fg=C["texto"],
            font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=10, pady=4,
        ).pack(side="right")

        # ── Status ──
        self.label_status = tk.Label(
            corpo, text="",
            font=("Segoe UI", 9),
            bg=C["bg"], fg=C["texto2"],
            anchor="w",
        )
        self.label_status.pack(fill="x", pady=(10, 0))

        # ── Barra de progresso ──
        self.barra = ttk.Progressbar(corpo, mode="indeterminate")
        self.barra.pack(fill="x", pady=(4, 0))

        # ── Botões de ação ──
        frame_acoes = tk.Frame(self.win, bg=C["bg"], padx=20, pady=14)
        frame_acoes.pack(fill="x")

        cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
               "cursor": "hand2", "padx": 16, "pady": 8}

        self.btn_publicar = tk.Button(
            frame_acoes,
            text="📡  Publicar na Alexa",
            command=self._publicar,
            bg=C["ok"], fg="#0f1117",
            activebackground="#35c07a", **cfg
        )
        self.btn_publicar.pack(side="left")

        tk.Button(
            frame_acoes,
            text="Cancelar",
            command=self.win.destroy,
            bg=C["borda"], fg=C["texto"],
            activebackground=C["entrada"], **cfg
        ).pack(side="right")

    # ─────────────────────── INTERAÇÃO ───────────────────────

    def _toggle_nova_playlist(self):
        """Mostra/esconde o campo de nome da nova playlist."""
        if self.var_playlist.get() == "__nova__":
            # Aparece logo abaixo do radiobutton "Criar nova", dentro do mesmo frame
            self.frame_nova.pack(fill="x", padx=4, pady=(4, 6))
            self.entry_nova.focus_set()
        else:
            self.frame_nova.pack_forget()
            self.entry_nova.delete(0, "end")  # limpa o campo ao desselecionar

    def _selecionar_arquivo(self):
        """Abre diálogo para selecionar arquivo de música no PC."""
        caminho = filedialog.askopenfilename(
            parent=self.win,
            title="Selecionar Música",
            filetypes=[
                ("Arquivos de Áudio", "*.mp3 *.wav *.ogg *.m4a *.flac"),
                ("Todos os arquivos", "*.*"),
            ]
        )
        if caminho:
            self.arquivo_selecionado = Path(caminho)
            nome = self.arquivo_selecionado.name
            self.label_arquivo.config(text=f"✓  {nome}", fg=C["ok"])
            self.label_status.config(text="Arquivo pronto. Clique em Publicar na Alexa.", fg=C["texto2"])

    # ─────────────────────── PUBLICAÇÃO ───────────────────────

    def _publicar(self):
        """Valida e inicia o upload em thread separada."""
        # Valida playlist
        playlist = self.var_playlist.get()
        if playlist == "__nova__":
            playlist = self.entry_nova.get().strip()
            if not playlist:
                messagebox.showwarning("Atenção", "Digite o nome da nova playlist.", parent=self.win)
                self.entry_nova.focus_set()
                return

        # Valida arquivo
        if not self.arquivo_selecionado or not self.arquivo_selecionado.exists():
            messagebox.showwarning("Atenção", "Selecione um arquivo de música antes de publicar.", parent=self.win)
            return

        # Confirmação
        resp = messagebox.askyesno(
            "Confirmar Publicação",
            f"Publicar  '{self.arquivo_selecionado.name}'  em:\n"
            f"  Playlist: {playlist}\n\n"
            "Passos:\n"
            "  1) Copia para musicas/<playlist>/\n"
            "  2) Upload para Google Drive\n"
            "  3) Atualiza musicas.json\n"
            "  4) Publica no GitHub Pages\n\n"
            "Deseja continuar?",
            parent=self.win
        )
        if not resp:
            return

        # Bloqueia botões e inicia
        self.btn_publicar.config(state="disabled")
        self.barra.start(12)
        threading.Thread(
            target=self._executar_upload,
            args=(playlist,),
            daemon=True
        ).start()

    def _executar_upload(self, playlist: str):
        """Thread principal de upload."""
        try:
            arquivo = self.arquivo_selecionado
            titulo = arquivo.stem  # nome sem extensão

            # Passo 1: Copiar para pasta local musicas/<playlist>/
            self._status(f"[1/4] Copiando para musicas/{playlist}/...")
            criar_pasta_musicas()
            pasta_destino = PASTA_MUSICAS / playlist
            pasta_destino.mkdir(parents=True, exist_ok=True)

            # Converte para MP3 se for WAV (Alexa só aceita HTTPS + MP3)
            if arquivo.suffix.lower() == ".wav":
                destino = pasta_destino / (arquivo.stem + ".mp3")
                self._status(f"[1/4] Convertendo WAV → MP3...")
                self._converter_wav_para_mp3(arquivo, destino)
            else:
                destino = pasta_destino / arquivo.name
                shutil.copy2(arquivo, destino)

            # Passo 2: Upload para Google Drive
            self._status(f"[2/4] Conectando ao Google Drive...")
            from cloud_uploader import obter_servico_drive, obter_ou_criar_pasta, upload_arquivo
            from config import GDRIVE_CONFIG
            service = obter_servico_drive()

            pasta_raiz_id = GDRIVE_CONFIG.get("pasta_raiz_id") or None
            pasta_drive_id = obter_ou_criar_pasta(service, "Músicas Caxinguele", pasta_raiz_id)

            # Subpasta por playlist no Drive (ex: "Músicas Caxinguele/Capoeira Regional")
            if playlist != "Músicas Caxinguele":
                pasta_drive_id = obter_ou_criar_pasta(service, playlist, pasta_drive_id)

            self._status(f"[2/4] Fazendo upload de '{destino.name}'...")
            resultado = upload_arquivo(service, destino, pasta_drive_id)
            if not resultado:
                raise RuntimeError("Upload para o Google Drive falhou.")
            url = resultado["direct_url"]

            # Passo 3: Atualizar musicas.json local
            self._status("[3/4] Atualizando musicas.json...")
            musicas = []
            if ARQUIVO_MUSICAS_JSON.exists():
                with open(ARQUIVO_MUSICAS_JSON, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    musicas = dados.get("musicas", [])

            idx = next((i for i, m in enumerate(musicas) if m.get("titulo") == titulo), None)
            nova = {"titulo": titulo, "artista": playlist, "url": url}
            if idx is not None:
                musicas[idx].update(nova)
                nova["numero"] = musicas[idx].get("numero", idx + 1)
            else:
                nova["numero"] = max((m.get("numero", 0) for m in musicas), default=0) + 1
                musicas.append(nova)

            with open(ARQUIVO_MUSICAS_JSON, "w", encoding="utf-8") as f:
                json.dump({
                    "musicas":    musicas,
                    "instrucoes": "Edite para gerenciar músicas. URL = link direto do Google Drive.",
                    "atualizado_em": datetime.now().strftime("%Y-%m-%d"),
                }, f, ensure_ascii=False, indent=2)

            # Passo 4: Publicar musicas.json no GitHub Pages
            self._status("[4/4] Publicando no GitHub Pages...")
            from github_uploader import upload_arquivo_github
            upload_arquivo_github(ARQUIVO_MUSICAS_JSON, "musicas.json")

            # Sucesso
            self.barra.stop()
            self._status(f"✅ '{titulo}' publicado na Alexa com sucesso!", cor=C["ok"])
            self.btn_publicar.config(state="normal")
            messagebox.showinfo(
                "Publicado! 🎵",
                f"'{titulo}' está disponível na Alexa!\n\n"
                f"Playlist: {playlist}\n"
                f"URL: {url[:55]}...\n\n"
                "Abra a skill e vá em Música → para ouvir.",
                parent=self.win
            )

        except Exception as e:
            self.barra.stop()
            self._status(f"Erro: {e}", cor=C["erro"])
            self.btn_publicar.config(state="normal")
            messagebox.showerror(
                "Erro ao Publicar",
                f"Não foi possível publicar a música:\n\n{e}\n\n"
                "Verifique se o credentials.json está na pasta do projeto.",
                parent=self.win
            )

    def _converter_wav_para_mp3(self, origem: Path, destino: Path):
        """Converte WAV para MP3 usando ffmpeg (se disponível)."""
        import subprocess
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(origem), "-q:a", "4", str(destino)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # ffmpeg não disponível: copia WAV direto com extensão .mp3
            # (funciona para maioria dos reprodutores, mas pode não ser ideal)
            shutil.copy2(origem, destino)

    def _status(self, msg: str, cor: str = None):
        """Atualiza label de status (pode ser chamado de thread)."""
        cor = cor or C["aviso"]
        self.label_status.after(0, lambda: self.label_status.config(text=msg, fg=cor))


def abrir_enviar_musica(parent):
    """Abre o dialog de envio de música."""
    EnviarMusicaDialog(parent)
