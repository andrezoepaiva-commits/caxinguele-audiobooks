"""
Livros e Audiobooks — Menu 2 do Super Alexa
Estrutura: Categorias → Livros → Capítulos
Reproduz via ffplay (já instalado no sistema).
Salva posição de leitura em ultimo_ouvido.json.
"""

import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
from config import BASE_DIR

PASTA_AUDIOBOOKS  = BASE_DIR / "audiobooks"
ARQUIVO_POSICAO   = BASE_DIR / "ultimo_ouvido.json"

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

def carregar_posicao() -> dict:
    """Carrega onde o amigo parou em cada livro."""
    if ARQUIVO_POSICAO.exists():
        try:
            return json.loads(ARQUIVO_POSICAO.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def salvar_posicao(posicao: dict):
    ARQUIVO_POSICAO.write_text(
        json.dumps(posicao, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def listar_categorias() -> list:
    """
    Retorna lista de categorias (subpastas de audiobooks/).
    Ex: "Inteligencia_sensorial", "Geral"
    """
    categorias = []
    if not PASTA_AUDIOBOOKS.exists():
        return categorias

    for pasta in sorted(PASTA_AUDIOBOOKS.iterdir()):
        if not pasta.is_dir():
            continue
        # Contar livros nesta categoria
        livros_na_cat = [p for p in pasta.iterdir() if p.is_dir() and list(p.glob("*.mp3"))]
        if livros_na_cat:
            categorias.append({
                "nome":  pasta.name,
                "pasta": str(pasta),
                "quantidade": len(livros_na_cat),
            })
    return categorias


def listar_livros_por_categoria(categoria_nome: str) -> list:
    """
    Retorna lista de livros de uma categoria específica.
    Cada livro tem: nome, pasta, capitulos (lista de mp3s ordenados).
    """
    livros = []
    pasta_categoria = PASTA_AUDIOBOOKS / categoria_nome

    if not pasta_categoria.exists():
        return livros

    for pasta in sorted(pasta_categoria.iterdir()):
        if not pasta.is_dir():
            continue
        mp3s = sorted(pasta.glob("*.mp3"))
        if not mp3s:
            continue
        livros.append({
            "nome":      pasta.name,
            "pasta":     str(pasta),
            "capitulos": [str(m) for m in mp3s],
            "total":     len(mp3s),
        })
    return livros


# ─────────────────────────── PLAYER ────────────────────────────

_processo_atual = None  # ffplay rodando


def reproduzir_mp3(caminho: str):
    """Inicia reprodução de um MP3 via ffplay."""
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
    """Para o player atual se estiver rodando."""
    global _processo_atual
    if _processo_atual and _processo_atual.poll() is None:
        _processo_atual.terminate()
    _processo_atual = None


# ─────────────────────────── INTERFACE ────────────────────────────

class LivrosUI:
    """Painel de Livros e Audiobooks — Menu 2 com categorias"""

    def __init__(self, parent):
        self.parent = parent
        self.posicao = carregar_posicao()
        self.livros = []
        self.tocando = None   # dict do capítulo atual

        # Navegação: None = categorias, "categoria_name" = livros, ("categoria", "livro") = capítulos
        self.nivel = None
        self.categoria_selecionada = None

        self.win = tk.Toplevel(parent)
        self.win.title("Livros e Audiobooks — Menu 2")
        self.win.geometry("860x560")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(680, 420)
        self.win.protocol("WM_DELETE_WINDOW", self._ao_fechar)

        self._construir_interface()
        self._mostrar_categorias()

    def _construir_interface(self):
        # ── Header com Breadcrumb ──
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        top_line = tk.Frame(inner, bg=C["painel"])
        top_line.pack(anchor="w", fill="x")

        tk.Label(top_line, text="LIVROS E AUDIOBOOKS",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w", side="left")

        # Breadcrumb será atualizado dinamicamente
        self.breadcrumb_label = tk.Label(top_line, text="",
                                         font=("Segoe UI", 9),
                                         bg=C["painel"], fg=C["texto2"])
        self.breadcrumb_label.pack(anchor="w", side="left", padx=(16, 0))

        tk.Label(inner,
                 text="Selecione uma categoria, depois um livro, depois um capítulo",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # ── Treeview ──
        frame_tree = tk.Frame(self.win, bg=C["bg"])
        frame_tree.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        style = ttk.Style()
        style.configure("Liv.Treeview",
                        background=C["entrada"], foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10), rowheight=28)
        style.configure("Liv.Treeview.Heading",
                        background=C["painel"], foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Liv.Treeview", background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(frame_tree,
                                  columns=("info",),
                                  show="tree headings",
                                  style="Liv.Treeview",
                                  height=14)
        self.tree.heading("#0",    text="Livro / Capítulo")
        self.tree.heading("info",  text="Info")
        self.tree.column("#0",    width=560, minwidth=300)
        self.tree.column("info",  width=200, minwidth=100, anchor="e")

        scroll = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Tags de cor
        self.tree.tag_configure("livro",    foreground=C["aviso"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("capitulo", foreground=C["texto"])
        self.tree.tag_configure("tocando",  foreground=C["ok"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("parado",   foreground=C["texto2"])

        self.tree.bind("<Double-1>", self._ao_duplo_clique)

        # ── Painel do player ──
        frame_player = tk.Frame(self.win, bg=C["painel"], pady=8, padx=16)
        frame_player.pack(fill="x", padx=16, pady=(10, 0))

        self.label_tocando = tk.Label(frame_player,
                                      text="Nenhum capítulo selecionado",
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

        # Botões à esquerda
        left_frame = tk.Frame(frame_acoes, bg=C["bg"])
        left_frame.pack(side="left")

        self.btn_voltar = tk.Button(left_frame, text="◀ Voltar",
                                    command=self._voltar,
                                    bg=C["aviso"], fg="black",
                                    activebackground="#ffd700", **cfg)
        # Será mostrado/escondido conforme navegação

        tk.Button(left_frame, text="▶ Reproduzir",
                  command=self._reproduzir_selecionado,
                  bg=C["acento"], fg="white",
                  activebackground="#5a52e0", **cfg
                  ).pack(side="left")

        tk.Button(left_frame, text="Atualizar",
                  command=self._atualizar_lista,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
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

    # ─────────────────────────── NAVEGAÇÃO ────────────────────────────

    def _atualizar_lista(self):
        """Recarrega conteúdo baseado no nível de navegação atual."""
        if self.nivel is None:
            self._mostrar_categorias()
        elif self.categoria_selecionada and self.nivel == "categoria":
            self._mostrar_livros(self.categoria_selecionada)
        else:
            # Nível de capítulos
            self._mostrar_capítulos()

    def _mostrar_categorias(self):
        """Mostra todas as categorias disponíveis."""
        self.nivel = None
        self.categoria_selecionada = None
        self.breadcrumb_label.config(text="")
        self.btn_voltar.pack_forget()  # Esconde botão Voltar

        self.tree.delete(*self.tree.get_children())
        categorias = listar_categorias()

        if not categorias:
            self.tree.insert("", "end",
                             text="  Nenhuma categoria encontrada",
                             values=("",), tags=("parado",))
            self.label_status.config(
                text="Crie pastas em audiobooks/ (Ex: Inteligencia_sensorial, Geral)",
                fg=C["texto2"])
            return

        for cat in categorias:
            cat_iid = f"cat_{cat['nome']}"
            self.tree.insert("", "end",
                             iid=cat_iid,
                             text=f"  📚  {cat['nome']}",
                             values=(f"{cat['quantidade']} livro(s)",),
                             tags=("livro",))

        self.label_status.config(
            text=f"{len(categorias)} categoria(s) disponível(is)  |  Duplo-clique para selecionar",
            fg=C["texto2"])

    def _mostrar_livros(self, categoria_nome: str):
        """Mostra livros de uma categoria específica."""
        self.nivel = "categoria"
        self.categoria_selecionada = categoria_nome
        self.breadcrumb_label.config(text=f"▶ {categoria_nome}")
        self.btn_voltar.pack(side="left")

        self.tree.delete(*self.tree.get_children())
        self.livros = listar_livros_por_categoria(categoria_nome)

        if not self.livros:
            self.tree.insert("", "end",
                             text=f"  Nenhum livro em {categoria_nome}/",
                             values=("",), tags=("parado",))
            self.label_status.config(
                text=f"Nenhum livro encontrado em '{categoria_nome}'",
                fg=C["texto2"])
            return

        for livro in self.livros:
            nome_livro = livro["nome"]
            total_caps = livro["total"]

            pos_salva = self.posicao.get(f"{categoria_nome}_{nome_livro}")
            info_livro = f"{total_caps} cap."
            if pos_salva:
                info_livro = f"▶ cap. {pos_salva['capitulo'] + 1}/{total_caps}"

            livro_iid = f"livro_{nome_livro}"
            self.tree.insert("", "end",
                             iid=livro_iid,
                             text=f"  📖  {nome_livro}",
                             values=(info_livro,),
                             tags=("livro",), open=True)

            for idx, mp3 in enumerate(livro["capitulos"]):
                nome_cap = Path(mp3).stem
                cap_iid = f"cap_{nome_livro}_{idx}"
                tag = "tocando" if (self.tocando and self.tocando.get("caminho") == mp3) else "capitulo"
                self.tree.insert(livro_iid, "end",
                                 iid=cap_iid,
                                 text=f"        {idx + 1:02d}.  {nome_cap}",
                                 values=("",),
                                 tags=(tag,))

        total = len(self.livros)
        self.label_status.config(
            text=f"{total} livro(s) em '{categoria_nome}'  |  Duplo-clique em capítulo para ouvir",
            fg=C["texto2"])

    def _mostrar_capítulos(self):
        """Reimplementar se necessário para um terceiro nível (raro)."""
        pass

    def _voltar(self):
        """Volta para o nível anterior."""
        if self.nivel == "categoria":
            self._mostrar_categorias()
        else:
            self._mostrar_categorias()

    def _categoria_selecionada(self) -> str | None:
        """Retorna nome da categoria selecionada, ou None."""
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if not iid.startswith("cat_"):
            return None
        # Formato: cat_NomeCategoria
        return iid.replace("cat_", "", 1)

    def _capitulo_selecionado(self) -> dict | None:
        """Retorna info do capítulo selecionado, ou None."""
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if not iid.startswith("cap_"):
            return None
        # Formato: cap_NomeLivro_idx
        partes = iid.split("_", 2)
        if len(partes) < 3:
            return None
        nome_livro = partes[1]
        idx = int(partes[2])
        livro = next((l for l in self.livros if l["nome"] == nome_livro), None)
        if not livro or idx >= len(livro["capitulos"]):
            return None
        return {
            "livro":       nome_livro,
            "categoria":   self.categoria_selecionada,
            "idx":         idx,
            "caminho":     livro["capitulos"][idx],
            "nome_cap":    Path(livro["capitulos"][idx]).stem,
        }

    # ─────────────────────────── PLAYER ────────────────────────────

    def _ao_duplo_clique(self, event=None):
        """Duplo-clique: navega ou reproduz conforme o nível."""
        # Nível de categorias
        if self.nivel is None:
            cat = self._categoria_selecionada()
            if cat:
                self._mostrar_livros(cat)
            return

        # Nível de livros/capítulos
        cap = self._capitulo_selecionado()
        if cap:
            self._iniciar_reproducao(cap)

    def _reproduzir_selecionado(self):
        cap = self._capitulo_selecionado()
        if not cap:
            messagebox.showinfo("Aviso",
                "Selecione um capítulo para reproduzir.",
                parent=self.win)
            return
        self._iniciar_reproducao(cap)

    def _iniciar_reproducao(self, cap: dict):
        """Inicia reprodução e salva posição."""
        reproduzir_mp3(cap["caminho"])
        self.tocando = cap

        # Salva posição com chave categoria_livro
        chave = f"{cap['categoria']}_{cap['livro']}"
        self.posicao[chave] = {
            "capitulo":   cap["idx"],
            "nome_cap":   cap["nome_cap"],
            "ouvido_em":  datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        salvar_posicao(self.posicao)

        self.label_tocando.config(
            text=f"▶  {cap['livro']}  —  Cap. {cap['idx'] + 1}: {cap['nome_cap']}",
            fg=C["ok"])
        self.label_status.config(
            text=f"Reproduzindo: {cap['nome_cap']}",
            fg=C["ok"])
        self._atualizar_lista()

    def _parar(self):
        parar_reproducao()
        self.tocando = None
        self.label_tocando.config(text="Reprodução parada.", fg=C["texto2"])
        self.label_status.config(text="Parado.", fg=C["texto2"])
        self._atualizar_lista()

    def _ao_fechar(self):
        parar_reproducao()
        self.win.destroy()


def abrir_livros(parent):
    """Abre o painel de Livros e Audiobooks"""
    LivrosUI(parent)
