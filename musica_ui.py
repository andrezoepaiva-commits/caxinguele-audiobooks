"""
Música — Menu 4 do Super Alexa
Lista playlists e músicas de arquivos locais (pasta musicas/).
Reproduz via ffplay.

Estrutura de pastas:
  musicas/
    Samba/
      01 - Nome da musica.mp3
    Capoeira/
      ...
    Playlists Personalizadas/
      ...
"""

import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
from config import BASE_DIR

ARQUIVO_MUSICAS_JSON = BASE_DIR / "musicas.json"

PASTA_MUSICAS   = BASE_DIR / "musicas"
ARQUIVO_MUSICAS = BASE_DIR / "musicas_config.json"

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


# ─────────────────────────── DADOS ────────────────────────────

def listar_playlists() -> list:
    """
    Lê subpastas de musicas/ como playlists.
    Cada playlist tem: nome, pasta, musicas (lista de mp3s).
    """
    playlists = []
    if not PASTA_MUSICAS.exists():
        return playlists

    for pasta in sorted(PASTA_MUSICAS.iterdir()):
        if not pasta.is_dir():
            continue
        mp3s = sorted(pasta.glob("*.mp3"))
        playlists.append({
            "nome":    pasta.name,
            "pasta":   str(pasta),
            "musicas": [{"nome": m.stem, "caminho": str(m)} for m in mp3s],
            "total":   len(mp3s),
        })
    return playlists


def criar_pasta_musicas():
    """Cria estrutura de pastas padrão se não existir."""
    PASTA_MUSICAS.mkdir(exist_ok=True)
    for nome in ["Músicas Caxinguelê", "Capoeira", "Playlists Personalizadas"]:
        (PASTA_MUSICAS / nome).mkdir(exist_ok=True)


# ─────────────────────────── PLAYER ────────────────────────────

_processo_atual = None


def reproduzir_mp3(caminho: str):
    global _processo_atual
    parar_reproducao()
    try:
        _processo_atual = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", caminho],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível reproduzir:\n{e}")


def parar_reproducao():
    global _processo_atual
    if _processo_atual and _processo_atual.poll() is None:
        _processo_atual.terminate()
    _processo_atual = None


# ─────────────────────────── INTERFACE ────────────────────────────

class MusicaUI:
    """Painel de Música — Menu 4"""

    def __init__(self, parent):
        self.parent = parent
        self.playlists = []
        self.tocando = None

        self.win = tk.Toplevel(parent)
        self.win.title("Música — Menu 4")
        self.win.geometry("820x560")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(660, 420)
        self.win.protocol("WM_DELETE_WINDOW", self._ao_fechar)

        self._construir_interface()
        self._atualizar_lista()

    def _construir_interface(self):
        # ── Header ──
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text="MÚSICA",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner,
                 text="Playlists em musicas/  |  duplo-clique para tocar  |  ffplay como player",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # ── Treeview ──
        frame_tree = tk.Frame(self.win, bg=C["bg"])
        frame_tree.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        style = ttk.Style()
        style.configure("Mus.Treeview",
                        background=C["entrada"], foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10), rowheight=28)
        style.configure("Mus.Treeview.Heading",
                        background=C["painel"], foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Mus.Treeview", background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(frame_tree,
                                  columns=("info",),
                                  show="tree headings",
                                  style="Mus.Treeview",
                                  height=14)
        self.tree.heading("#0",   text="Playlist / Música")
        self.tree.heading("info", text="Info")
        self.tree.column("#0",   width=540, minwidth=300)
        self.tree.column("info", width=180, minwidth=100, anchor="e")

        scroll = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.tag_configure("playlist", foreground=C["aviso"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("musica",   foreground=C["texto"])
        self.tree.tag_configure("tocando",  foreground=C["ok"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("vazio",    foreground=C["texto2"])

        self.tree.bind("<Double-1>", self._ao_duplo_clique)

        # ── Painel do player ──
        frame_player = tk.Frame(self.win, bg=C["painel"], pady=8, padx=16)
        frame_player.pack(fill="x", padx=16, pady=(10, 0))

        self.label_tocando = tk.Label(frame_player,
                                      text="Nenhuma música selecionada",
                                      font=("Segoe UI", 10),
                                      bg=C["painel"], fg=C["texto2"],
                                      anchor="w")
        self.label_tocando.pack(side="left", fill="x", expand=True)

        tk.Button(frame_player, text="⏹ Parar",
                  command=self._parar,
                  bg=C["erro"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=10, pady=4).pack(side="right")

        # ── Botões de ação ──
        frame_acoes = tk.Frame(self.win, bg=C["bg"])
        frame_acoes.pack(fill="x", padx=16, pady=(10, 12))

        cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
               "cursor": "hand2", "padx": 14, "pady": 6}

        tk.Button(frame_acoes, text="▶ Tocar",
                  command=self._reproduzir_selecionado,
                  bg=C["acento"], fg="white",
                  activebackground="#5a52e0", **cfg
                  ).pack(side="left")

        tk.Button(frame_acoes, text="Criar Pastas",
                  command=self._criar_pastas,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Atualizar",
                  command=self._atualizar_lista,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="📡 Publicar na Alexa",
                  command=self._publicar_na_alexa,
                  bg=C["ok"], fg="#0f1117",
                  activebackground="#35c07a", **cfg
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Fechar",
                  command=self._ao_fechar,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="right")

        self.label_status = tk.Label(self.win, text="",
                                     font=("Segoe UI", 9),
                                     bg=C["bg"], fg=C["texto2"])
        self.label_status.pack(fill="x", padx=16, pady=(0, 6))

    # ─────────────────────────── DADOS ────────────────────────────

    def _atualizar_lista(self):
        self.tree.delete(*self.tree.get_children())
        self.playlists = listar_playlists()

        if not self.playlists:
            self.tree.insert("", "end",
                             text="  Nenhuma playlist encontrada em musicas/",
                             values=("",), tags=("vazio",))
            self.tree.insert("", "end",
                             text="  → Clique em 'Criar Pastas' para criar a estrutura",
                             values=("",), tags=("vazio",))
            self.tree.insert("", "end",
                             text="  → Depois coloque MP3s nas subpastas",
                             values=("",), tags=("vazio",))
            self.label_status.config(
                text="Pasta musicas/ vazia — crie a estrutura e coloque MP3s.",
                fg=C["texto2"])
            return

        total_musicas = sum(p["total"] for p in self.playlists)
        for pl in self.playlists:
            pl_iid = f"pl_{pl['nome']}"
            info = f"{pl['total']} música(s)" if pl["total"] else "vazia"
            self.tree.insert("", "end",
                             iid=pl_iid,
                             text=f"  🎵  {pl['nome']}",
                             values=(info,),
                             tags=("playlist",),
                             open=(pl["total"] > 0))

            for idx, m in enumerate(pl["musicas"]):
                m_iid = f"m_{pl['nome']}_{idx}"
                tag = "tocando" if (self.tocando and self.tocando.get("caminho") == m["caminho"]) else "musica"
                self.tree.insert(pl_iid, "end",
                                 iid=m_iid,
                                 text=f"        {idx + 1:02d}.  {m['nome']}",
                                 values=("",),
                                 tags=(tag,))

        self.label_status.config(
            text=f"{len(self.playlists)} playlist(s)  |  {total_musicas} música(s)",
            fg=C["texto2"])

    def _musica_selecionada(self) -> dict | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if not iid.startswith("m_"):
            return None
        partes = iid.split("_", 2)
        if len(partes) < 3:
            return None
        nome_pl = partes[1]
        idx = int(partes[2])
        pl = next((p for p in self.playlists if p["nome"] == nome_pl), None)
        if not pl or idx >= len(pl["musicas"]):
            return None
        m = pl["musicas"][idx]
        return {"playlist": nome_pl, "idx": idx, **m}

    # ─────────────────────────── PLAYER ────────────────────────────

    def _ao_duplo_clique(self, event=None):
        m = self._musica_selecionada()
        if m:
            self._iniciar_reproducao(m)

    def _reproduzir_selecionado(self):
        m = self._musica_selecionada()
        if not m:
            messagebox.showinfo("Aviso",
                "Selecione uma música para tocar.",
                parent=self.win)
            return
        self._iniciar_reproducao(m)

    def _iniciar_reproducao(self, m: dict):
        reproduzir_mp3(m["caminho"])
        self.tocando = m
        self.label_tocando.config(
            text=f"▶  {m['playlist']}  —  {m['nome']}",
            fg=C["ok"])
        self.label_status.config(text=f"Tocando: {m['nome']}", fg=C["ok"])
        self._atualizar_lista()

    def _parar(self):
        parar_reproducao()
        self.tocando = None
        self.label_tocando.config(text="Reprodução parada.", fg=C["texto2"])
        self.label_status.config(text="Parado.", fg=C["texto2"])
        self._atualizar_lista()

    def _publicar_na_alexa(self):
        """Publica música selecionada na Alexa: Drive → musicas.json → GitHub Pages."""
        m = self._musica_selecionada()
        if not m:
            messagebox.showinfo("Aviso",
                "Selecione uma música para publicar.\n"
                "Clique em uma música na lista, depois clique Publicar na Alexa.",
                parent=self.win)
            return

        resposta = messagebox.askyesno(
            "Publicar na Alexa",
            f"Publicar  '{m['nome']}'  na Alexa?\n\n"
            "Isso vai:\n"
            "  1) Fazer upload para Google Drive\n"
            "  2) Atualizar musicas.json\n"
            "  3) Publicar no GitHub Pages\n\n"
            "A música ficará disponível na Alexa automaticamente.",
            parent=self.win
        )
        if not resposta:
            return

        self.label_status.config(text=f"Publicando '{m['nome']}'... aguarde.", fg=C["aviso"])
        threading.Thread(target=self._fazer_upload_alexa, args=(m,), daemon=True).start()

    def _fazer_upload_alexa(self, m: dict):
        """Thread: faz upload da música para Drive + atualiza musicas.json + publica."""
        try:
            # --- Passo 1: Upload para Google Drive ---
            self.label_status.config(text="[1/3] Conectando ao Google Drive...", fg=C["aviso"])
            from cloud_uploader import obter_servico_drive, obter_ou_criar_pasta, upload_arquivo
            from config import GDRIVE_CONFIG

            service = obter_servico_drive()

            # Pasta raiz ("Audiobooks - Alexa") → subpasta "Músicas Caxinguele"
            pasta_raiz_id = GDRIVE_CONFIG.get("pasta_raiz_id") or None
            pasta_musicas_id = obter_ou_criar_pasta(service, "Músicas Caxinguele", pasta_raiz_id)

            self.label_status.config(text=f"[1/3] Fazendo upload de '{m['nome']}'...", fg=C["aviso"])
            resultado = upload_arquivo(service, Path(m["caminho"]), pasta_musicas_id)

            if not resultado:
                self.label_status.config(text="Erro no upload para Google Drive.", fg=C["erro"])
                messagebox.showerror("Erro", "Não foi possível fazer upload para o Google Drive.", parent=self.win)
                return

            url = resultado["direct_url"]

            # --- Passo 2: Atualizar musicas.json local ---
            self.label_status.config(text="[2/3] Atualizando musicas.json...", fg=C["aviso"])
            musicas = []
            if ARQUIVO_MUSICAS_JSON.exists():
                with open(ARQUIVO_MUSICAS_JSON, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    musicas = dados.get("musicas", [])

            # Verifica se esta música já existe (evita duplicatas)
            idx_existente = next(
                (i for i, ms in enumerate(musicas) if ms.get("titulo") == m["nome"]),
                None
            )
            nova_musica = {
                "titulo":  m["nome"],
                "artista": m.get("playlist", "Caxinguele"),
                "url":     url,
            }
            if idx_existente is not None:
                # Atualiza URL da música existente
                musicas[idx_existente].update(nova_musica)
                nova_musica["numero"] = musicas[idx_existente].get("numero", idx_existente + 1)
            else:
                # Adiciona nova — número sequencial
                proximo_num = max((ms.get("numero", 0) for ms in musicas), default=0) + 1
                nova_musica["numero"] = proximo_num
                musicas.append(nova_musica)

            dados_novos = {
                "musicas":       musicas,
                "instrucoes":    "Edite este arquivo para gerenciar músicas. URL = link direto do Google Drive.",
                "atualizado_em": datetime.now().strftime("%Y-%m-%d"),
            }
            with open(ARQUIVO_MUSICAS_JSON, "w", encoding="utf-8") as f:
                json.dump(dados_novos, f, ensure_ascii=False, indent=2)

            # --- Passo 3: Publicar musicas.json no GitHub Pages ---
            self.label_status.config(text="[3/3] Publicando no GitHub Pages...", fg=C["aviso"])
            from github_uploader import upload_arquivo_github
            upload_arquivo_github(ARQUIVO_MUSICAS_JSON, "musicas.json")

            self.label_status.config(
                text=f"✅ '{m['nome']}' publicado! Disponível na Alexa agora.",
                fg=C["ok"])
            messagebox.showinfo(
                "Publicado com Sucesso! 🎵",
                f"'{m['nome']}' está disponível na Alexa!\n\n"
                f"URL: {url[:60]}...\n\n"
                "Próxima vez que abrir a skill, a música aparece no menu Música.",
                parent=self.win
            )

        except Exception as e:
            self.label_status.config(text=f"Erro: {e}", fg=C["erro"])
            messagebox.showerror(
                "Erro ao Publicar",
                f"Não foi possível publicar a música:\n\n{e}\n\n"
                "Verifique se o credentials.json está na pasta do projeto.",
                parent=self.win
            )

    def _criar_pastas(self):
        criar_pasta_musicas()
        self._atualizar_lista()
        self.label_status.config(
            text="Estrutura criada em musicas/  →  Coloque MP3s nas subpastas e clique Atualizar.",
            fg=C["ok"])

    def _ao_fechar(self):
        parar_reproducao()
        self.win.destroy()


def abrir_musica(parent):
    """Abre o painel de Música"""
    MusicaUI(parent)
