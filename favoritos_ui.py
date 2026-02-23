"""
Favoritos Importantes — Menu 3 do Super Alexa
Gerencia os itens favoritados pelo usuário em cada subcategoria.

Subcategorias:
  1. Salvos para Escutar Mais Tarde
  2. Notícias e Artigos Favoritados
  3. Emails Favoritados
  4. Documentos Importantes

Ação disponível: remover item de qualquer sublista.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

ARQUIVO_FAVORITOS = BASE_DIR / "favoritos.json"

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

SUBLISTAS = [
    "Salvos para Escutar Mais Tarde",
    "Notícias e Artigos Favoritados",
    "Emails Favoritados",
    "Documentos Importantes",
]


# ─────────────────────────── DADOS ────────────────────────────

def carregar_favoritos() -> dict:
    if ARQUIVO_FAVORITOS.exists():
        try:
            return json.loads(ARQUIVO_FAVORITOS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {s: [] for s in SUBLISTAS}


def salvar_favoritos(favoritos: dict):
    ARQUIVO_FAVORITOS.write_text(
        json.dumps(favoritos, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def adicionar_favorito(sublista: str, item: dict):
    """Adiciona item a uma sublista de favoritos (chamado pelo Menu 1)."""
    favs = carregar_favoritos()
    if sublista not in favs:
        favs[sublista] = []
    # Evita duplicata pelo título
    titulos = [f.get("titulo", "") for f in favs[sublista]]
    if item.get("titulo", "") not in titulos:
        item["favoritado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        favs[sublista].insert(0, item)
        salvar_favoritos(favs)


# ─────────────────────────── INTERFACE ────────────────────────────

class FavoritosUI:
    """Painel de gerenciamento de favoritos — Menu 3"""

    def __init__(self, parent):
        self.parent = parent
        self.favoritos = carregar_favoritos()
        self.sublista_selecionada = None

        self.win = tk.Toplevel(parent)
        self.win.title("Favoritos Importantes — Menu 3")
        self.win.geometry("860x540")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(680, 400)

        self._construir_interface()
        self._atualizar_sublistas()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text="FAVORITOS IMPORTANTES",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner,
                 text="Itens salvos pelo usuário — selecione uma lista e gerencie",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Layout dividido
        frame_main = tk.Frame(self.win, bg=C["bg"])
        frame_main.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        # Coluna esquerda — sublistas
        frame_esq = tk.Frame(frame_main, bg=C["bg"])
        frame_esq.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(frame_esq, text="Categorias",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        self.listbox = tk.Listbox(frame_esq,
                                   bg=C["entrada"], fg=C["texto"],
                                   selectbackground=C["acento"],
                                   font=("Segoe UI", 10),
                                   relief="flat", bd=0,
                                   width=30, height=10)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._ao_selecionar_sublista)

        # Coluna direita — itens
        frame_dir = tk.Frame(frame_main, bg=C["bg"])
        frame_dir.pack(side="left", fill="both", expand=True)

        tk.Label(frame_dir, text="Itens",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        style = ttk.Style()
        style.configure("Fav.Treeview",
                        background=C["entrada"], foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10), rowheight=28)
        style.configure("Fav.Treeview.Heading",
                        background=C["painel"], foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Fav.Treeview", background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(frame_dir,
                                  columns=("data", "titulo"),
                                  show="headings",
                                  style="Fav.Treeview",
                                  height=12)
        self.tree.heading("data",   text="Favoritado em")
        self.tree.heading("titulo", text="Título")
        self.tree.column("data",   width=130, minwidth=100, anchor="center")
        self.tree.column("titulo", width=500, minwidth=200)

        scroll = ttk.Scrollbar(frame_dir, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Botões
        frame_acoes = tk.Frame(self.win, bg=C["bg"])
        frame_acoes.pack(fill="x", padx=16, pady=(10, 12))

        tk.Button(frame_acoes, text="Remover dos Favoritos",
                  command=self._remover_item,
                  bg=C["erro"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="left")

        tk.Button(frame_acoes, text="Fechar",
                  command=self.win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="right")

        self.label_status = tk.Label(self.win, text="",
                                     font=("Segoe UI", 9),
                                     bg=C["bg"], fg=C["texto2"])
        self.label_status.pack(fill="x", padx=16, pady=(0, 6))

    # ─────────────────────────── DADOS ────────────────────────────

    def _atualizar_sublistas(self):
        self.listbox.delete(0, "end")
        self.favoritos = carregar_favoritos()
        for sub in SUBLISTAS:
            total = len(self.favoritos.get(sub, []))
            self.listbox.insert("end", f"{sub}  ({total})")

    def _ao_selecionar_sublista(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        nome = self.listbox.get(sel[0]).rsplit("  (", 1)[0]
        self.sublista_selecionada = nome
        self._atualizar_itens()

    def _atualizar_itens(self):
        self.tree.delete(*self.tree.get_children())
        if not self.sublista_selecionada:
            return
        itens = self.favoritos.get(self.sublista_selecionada, [])
        for i, item in enumerate(itens):
            data = item.get("favoritado_em", item.get("data", ""))[:16]
            titulo = item.get("titulo", item.get("texto", "")[:80])
            self.tree.insert("", "end", iid=str(i), values=(data, titulo))

    # ─────────────────────────── AÇÕES ────────────────────────────

    def _remover_item(self):
        if not self.sublista_selecionada:
            messagebox.showinfo("Aviso", "Selecione uma categoria primeiro.",
                                parent=self.win)
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um item para remover.",
                                parent=self.win)
            return

        idx = int(sel[0])
        itens = self.favoritos.get(self.sublista_selecionada, [])
        if idx >= len(itens):
            return

        item = itens[idx]
        titulo = item.get("titulo", item.get("texto", "?"))[:60]

        confirmar = messagebox.askyesno(
            "Remover dos Favoritos",
            f"Remover '{titulo}' de '{self.sublista_selecionada}'?",
            parent=self.win
        )
        if confirmar:
            self.favoritos[self.sublista_selecionada].pop(idx)
            salvar_favoritos(self.favoritos)
            self._atualizar_sublistas()
            self._atualizar_itens()
            self.label_status.config(
                text=f"Removido de '{self.sublista_selecionada}'.",
                fg=C["aviso"])


def abrir_favoritos(parent):
    """Abre o painel de Favoritos Importantes"""
    FavoritosUI(parent)
