"""
Organizações da Mente em Listas — Menu 10 do Super Alexa
Visualização e gerenciamento de todas as listas criadas pelo Menu 0.

4 modos de escuta (TODOS individuais por item, nunca resumo geral):
  1 = Resumo pragmático de cada item (curto, objetivo)
  2 = Leitura completa de cada item (tom original preservado)
  3 = Elaboração com sugestões da IA (aprofunda + sugere)
  4 = Áudio original da voz (gravação bruta do usuário)

Comandos suportados:
  "Editar"  — adiciona conteúdo a um item existente
  "Pular"   — próximo item
  "Voltar"  — item anterior
  "Buscar"  — filtra por palavra-chave em todas as listas
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from datetime import datetime
from config import BASE_DIR
from gravacao_mental import carregar_listas, salvar_listas, classificar_texto

ARQUIVO_LISTAS = BASE_DIR / "listas_mentais.json"

# Paleta de cores (mesma do app principal)
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

# Listas com submenus fixos
SUBLISTAS = {
    "Consultas Médicas": ["Endocrinologista", "Dentista", "Urologista",
                          "Cardiologista", "Geral"],
}


def resumo_pragmatico(texto: str) -> str:
    """
    Versão 1: Resumo curto e objetivo de um único item.
    Remove redundâncias, preserva a essência.
    """
    # Remove expressões introdutórias comuns
    prefixos = [
        "queria anotar que ", "gostaria de lembrar que ", "preciso de ",
        "tenho que ", "não esquecer de ", "me lembre de ",
    ]
    resultado = texto.strip()
    for p in prefixos:
        if resultado.lower().startswith(p):
            resultado = resultado[len(p):]
            break
    # Capitaliza e garante ponto final
    resultado = resultado[0].upper() + resultado[1:]
    if not resultado.endswith((".", "!", "?")):
        resultado += "."
    return resultado


def elaborar_com_sugestoes(texto: str, categoria: str) -> str:
    """
    Versão 3: Repete o item + adiciona aprofundamento/sugestões.
    TODO: Conectar à Google Summarization API para versão real.
    Por ora, gera texto estruturado localmente.
    """
    base = resumo_pragmatico(texto)

    sugestoes = {
        "Compras": "Sugestão: verifique preços online antes de comprar e compare marcas.",
        "Consultas Médicas": "Sugestão: anote os sintomas antes da consulta para não esquecer na hora.",
        "Ideias Caxinguelê": "Sugestão: avalie o esforço de implementação e o impacto para o usuário.",
        "Tarefas da Semana": "Sugestão: defina um prazo e divida em passos menores se necessário.",
        "Lembretes Gerais": "Sugestão: considere adicionar ao calendário para não perder o prazo.",
        "Insights Pessoais": "Sugestão: reflita se esse insight pode virar uma ação concreta.",
    }

    plus = sugestoes.get(categoria, "Sugestão: considere o próximo passo prático.")
    return f"Você anotou: {base} {plus}"


class ListasMentaisUI:
    """Janela de visualização e edição das Organizações da Mente em Listas"""

    def __init__(self, parent):
        self.parent = parent
        self.listas = carregar_listas()
        self.lista_selecionada = None
        self.item_selecionado_idx = None

        self.win = tk.Toplevel(parent)
        self.win.title("Organizações da Mente em Listas — Menu 10")
        self.win.geometry("900x640")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(720, 500)

        self._construir_interface()
        self._atualizar_lista_de_listas()

    # ───────────────────────────── INTERFACE ──────────────────────────────

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text="ORGANIZAÇÕES DA MENTE EM LISTAS",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner, text="Anotações organizadas por categoria — 4 modos de escuta",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Busca
        frame_busca = tk.Frame(self.win, bg=C["bg"])
        frame_busca.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(frame_busca, text="Buscar:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(side="left")
        self.entry_busca = tk.Entry(frame_busca, font=("Segoe UI", 10),
                                    bg=C["entrada"], fg=C["texto"],
                                    insertbackground=C["texto"], relief="flat",
                                    width=40)
        self.entry_busca.pack(side="left", padx=(6, 0), ipady=5)
        self.entry_busca.bind("<Return>", lambda e: self._buscar())
        tk.Button(frame_busca, text="Buscar",
                  command=self._buscar,
                  bg=C["acento"], fg="white",
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2",
                  padx=10, pady=4).pack(side="left", padx=(6, 0))

        # Layout dividido: listas à esquerda, itens à direita
        frame_main = tk.Frame(self.win, bg=C["bg"])
        frame_main.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        # Coluna esquerda — Lista de categorias
        frame_cats = tk.Frame(frame_main, bg=C["bg"])
        frame_cats.pack(side="left", fill="y", padx=(0, 8))

        tk.Label(frame_cats, text="Listas",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        self.listbox_cats = tk.Listbox(frame_cats,
                                        bg=C["entrada"], fg=C["texto"],
                                        selectbackground=C["acento"],
                                        font=("Segoe UI", 10),
                                        relief="flat", bd=0,
                                        width=26, height=20)
        self.listbox_cats.pack(fill="y", expand=True)
        self.listbox_cats.bind("<<ListboxSelect>>", self._ao_selecionar_lista)

        # Coluna direita — Itens da lista selecionada
        frame_itens = tk.Frame(frame_main, bg=C["bg"])
        frame_itens.pack(side="left", fill="both", expand=True)

        tk.Label(frame_itens, text="Itens",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        style = ttk.Style()
        style.configure("Listas.Treeview",
                         background=C["entrada"], foreground=C["texto"],
                         fieldbackground=C["entrada"],
                         font=("Segoe UI", 10), rowheight=28)
        style.configure("Listas.Treeview.Heading",
                         background=C["painel"], foreground=C["texto"],
                         font=("Segoe UI", 10, "bold"))
        style.map("Listas.Treeview", background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(frame_itens,
                                  columns=("data", "preview"),
                                  show="headings",
                                  style="Listas.Treeview",
                                  height=16)
        self.tree.heading("data",    text="Data")
        self.tree.heading("preview", text="Anotação")
        self.tree.column("data",    width=100, minwidth=80, anchor="center")
        self.tree.column("preview", width=500, minwidth=200)

        scroll = ttk.Scrollbar(frame_itens, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Painel de modos de escuta
        frame_modos = tk.Frame(self.win, bg=C["bg"])
        frame_modos.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(frame_modos, text="Modo de escuta:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(side="left")

        modos = [
            ("1  Resumo Pragmático", self._modo_resumo),
            ("2  Leitura Completa",  self._modo_completo),
            ("3  Elaborado + IA",    self._modo_elaborado),
            ("4  Áudio Original",    self._modo_audio),
        ]
        for label, cmd in modos:
            tk.Button(frame_modos, text=label, command=cmd,
                      bg=C["borda"], fg=C["texto"],
                      font=("Segoe UI", 9, "bold"),
                      relief="flat", cursor="hand2",
                      padx=10, pady=5,
                      activebackground=C["acento"],
                      activeforeground="white"
                      ).pack(side="left", padx=(8, 0))

        # Botões de ação
        frame_acoes = tk.Frame(self.win, bg=C["bg"])
        frame_acoes.pack(fill="x", padx=16, pady=(8, 12))

        tk.Button(frame_acoes, text="Editar Item",
                  command=self._editar_item,
                  bg=C["acento"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(side="left")

        tk.Button(frame_acoes, text="Nova Lista",
                  command=self._nova_lista,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Renomear Lista",
                  command=self._renomear_lista,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Remover Item",
                  command=self._remover_item,
                  bg=C["erro"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Remover Lista",
                  command=self._remover_lista,
                  bg=C["erro"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Fechar",
                  command=self.win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=10, pady=6).pack(side="right")

    # ───────────────────────────── DADOS ──────────────────────────────────

    def _atualizar_lista_de_listas(self):
        self.listbox_cats.delete(0, "end")
        self.listas = carregar_listas()
        for cat, itens in self.listas.items():
            total = len(itens)
            self.listbox_cats.insert("end", f"{cat}  ({total})")

    def _ao_selecionar_lista(self, event=None):
        sel = self.listbox_cats.curselection()
        if not sel:
            return
        nome_exibido = self.listbox_cats.get(sel[0])
        # Remove o contador "(N)" do final
        self.lista_selecionada = nome_exibido.rsplit("  (", 1)[0]
        self._atualizar_itens()

    def _atualizar_itens(self):
        self.tree.delete(*self.tree.get_children())
        if not self.lista_selecionada:
            return
        itens = self.listas.get(self.lista_selecionada, [])
        for item in itens:
            data = item.get("data", "")[:10]
            preview = item.get("texto", "")[:80]
            self.tree.insert("", "end",
                             iid=item.get("id", ""),
                             values=(data, preview))

    # ───────────────────────── MODOS DE ESCUTA ────────────────────────────

    def _item_selecionado(self):
        """Retorna o item selecionado na árvore, ou None."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um item primeiro.", parent=self.win)
            return None
        item_id = sel[0]
        itens = self.listas.get(self.lista_selecionada, [])
        for item in itens:
            if item.get("id") == item_id:
                return item
        return None

    def _modo_resumo(self):
        """Modo 1: Resumo pragmático"""
        item = self._item_selecionado()
        if not item:
            return
        resumo = resumo_pragmatico(item["texto"])
        self._exibir_conteudo("Resumo Pragmático", resumo, item)

    def _modo_completo(self):
        """Modo 2: Leitura completa"""
        item = self._item_selecionado()
        if not item:
            return
        self._exibir_conteudo("Leitura Completa", item["texto"], item)

    def _modo_elaborado(self):
        """Modo 3: Elaborado com sugestões"""
        item = self._item_selecionado()
        if not item:
            return
        cat = self.lista_selecionada or "Lembretes Gerais"
        elaborado = elaborar_com_sugestoes(item["texto"], cat)
        self._exibir_conteudo("Elaborado + Sugestões", elaborado, item)

    def _modo_audio(self):
        """Modo 4: Áudio original"""
        item = self._item_selecionado()
        if not item:
            return
        audio = item.get("audio_original")
        if audio and Path(audio).exists():
            import subprocess
            subprocess.Popen(["start", audio], shell=True)
        else:
            messagebox.showinfo(
                "Áudio Original",
                f"Áudio original não disponível para este item.\n\n"
                f"Data: {item.get('data', '?')}\n"
                f"Texto: {item['texto'][:120]}...",
                parent=self.win
            )

    def _exibir_conteudo(self, titulo: str, conteudo: str, item: dict):
        """Janela para exibir o conteúdo do item no modo escolhido"""
        win = tk.Toplevel(self.win)
        win.title(f"Modo: {titulo}")
        win.geometry("520x300")
        win.configure(bg=C["bg"])
        win.transient(self.win)
        win.grab_set()

        tk.Label(win, text=titulo,
                 font=("Segoe UI", 12, "bold"),
                 bg=C["bg"], fg=C["acento"]).pack(padx=16, pady=(16, 4), anchor="w")

        tk.Label(win, text=f"Data: {item.get('data', '?')}",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(padx=16, anchor="w")

        frame_txt = tk.Frame(win, bg=C["entrada"], relief="flat")
        frame_txt.pack(fill="both", expand=True, padx=16, pady=(8, 12))

        txt = tk.Text(frame_txt, font=("Segoe UI", 10),
                      bg=C["entrada"], fg=C["texto"],
                      relief="flat", bd=0, wrap="word",
                      padx=12, pady=10)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", conteudo)
        txt.config(state="disabled")

        tk.Button(win, text="Fechar",
                  command=win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(pady=(0, 12))

    # ───────────────────────────── AÇÕES ──────────────────────────────────

    def _editar_item(self):
        """Adiciona mais conteúdo a um item existente (comando Editar)"""
        item = self._item_selecionado()
        if not item:
            return

        win = tk.Toplevel(self.win)
        win.title("Editar — Adicionar conteúdo")
        win.geometry("480x200")
        win.configure(bg=C["bg"])
        win.transient(self.win)
        win.grab_set()

        tk.Label(win, text="Item atual:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(padx=16, pady=(12, 2), anchor="w")
        tk.Label(win, text=item["texto"][:80] + "...",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto"]).pack(padx=16, anchor="w")

        tk.Label(win, text="Adicionar informação:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(padx=16, pady=(10, 2), anchor="w")

        entry = tk.Entry(win, font=("Segoe UI", 10),
                         bg=C["entrada"], fg=C["texto"],
                         insertbackground=C["texto"], relief="flat")
        entry.pack(fill="x", padx=16, ipady=6)
        entry.focus()

        def salvar():
            adicional = entry.get().strip()
            if not adicional:
                return
            # Une o texto original com o adicional
            item["texto"] = item["texto"].rstrip(".") + ". " + adicional
            item["editado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            salvar_listas(self.listas)
            self._atualizar_itens()
            win.destroy()

        tk.Button(win, text="Salvar",
                  command=salvar,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(pady=(8, 0))

        win.bind("<Return>", lambda e: salvar())

    def _nova_lista(self):
        """Cria uma nova lista manualmente"""
        nome = simpledialog.askstring("Nova Lista", "Nome da nova lista:",
                                      parent=self.win)
        if nome and nome.strip():
            nome = nome.strip()
            if nome not in self.listas:
                self.listas[nome] = []
                salvar_listas(self.listas)
                self._atualizar_lista_de_listas()
            else:
                messagebox.showinfo("Aviso", f"Lista '{nome}' já existe.",
                                    parent=self.win)

    def _renomear_lista(self):
        """Renomeia a lista selecionada"""
        if not self.lista_selecionada:
            messagebox.showinfo("Aviso", "Selecione uma lista primeiro.",
                                parent=self.win)
            return
        novo_nome = simpledialog.askstring(
            "Renomear Lista",
            f"Novo nome para '{self.lista_selecionada}':",
            initialvalue=self.lista_selecionada,
            parent=self.win
        )
        if not novo_nome or not novo_nome.strip():
            return
        novo_nome = novo_nome.strip()
        if novo_nome == self.lista_selecionada:
            return
        if novo_nome in self.listas:
            messagebox.showinfo("Aviso", f"Já existe uma lista chamada '{novo_nome}'.",
                                parent=self.win)
            return
        # Recria a lista com o novo nome preservando os itens e a ordem
        nova_listas = {}
        for chave, itens in self.listas.items():
            if chave == self.lista_selecionada:
                nova_listas[novo_nome] = itens
            else:
                nova_listas[chave] = itens
        self.listas = nova_listas
        salvar_listas(self.listas)
        self.lista_selecionada = novo_nome
        self._atualizar_lista_de_listas()
        self._atualizar_itens()

    def _remover_lista(self):
        """Remove a lista inteira selecionada com confirmação"""
        if not self.lista_selecionada:
            messagebox.showinfo("Aviso", "Selecione uma lista primeiro.",
                                parent=self.win)
            return
        total = len(self.listas.get(self.lista_selecionada, []))
        confirmar = messagebox.askyesno(
            "Remover Lista",
            f"Remover a lista '{self.lista_selecionada}'?\n\n"
            f"Ela contém {total} item(s). Essa ação não pode ser desfeita.",
            parent=self.win
        )
        if confirmar:
            del self.listas[self.lista_selecionada]
            salvar_listas(self.listas)
            self.lista_selecionada = None
            self._atualizar_lista_de_listas()
            self.tree.delete(*self.tree.get_children())

    def _remover_item(self):
        """Remove o item selecionado com confirmação"""
        item = self._item_selecionado()
        if not item:
            return

        confirmar = messagebox.askyesno(
            "Remover",
            f"Remover este item?\n\n{item['texto'][:80]}...",
            parent=self.win
        )
        if confirmar:
            itens = self.listas.get(self.lista_selecionada, [])
            self.listas[self.lista_selecionada] = [
                i for i in itens if i.get("id") != item.get("id")
            ]
            salvar_listas(self.listas)
            self._atualizar_lista_de_listas()
            self._atualizar_itens()

    def _buscar(self):
        """Busca por palavra-chave em todas as listas"""
        termo = self.entry_busca.get().strip().lower()
        if not termo:
            return

        resultados = []
        for cat, itens in self.listas.items():
            for item in itens:
                if termo in item.get("texto", "").lower():
                    resultados.append((cat, item))

        if not resultados:
            messagebox.showinfo("Busca", f"Nenhum resultado para '{termo}'.",
                                parent=self.win)
            return

        # Exibe resultados em janela
        win = tk.Toplevel(self.win)
        win.title(f"Resultados: {termo}")
        win.geometry("560x360")
        win.configure(bg=C["bg"])
        win.transient(self.win)

        tk.Label(win, text=f"{len(resultados)} resultado(s) para: '{termo}'",
                 font=("Segoe UI", 11, "bold"),
                 bg=C["bg"], fg=C["ok"]).pack(padx=16, pady=(16, 8), anchor="w")

        frame = tk.Frame(win, bg=C["bg"])
        frame.pack(fill="both", expand=True, padx=16)

        txt = tk.Text(frame, font=("Segoe UI", 10),
                      bg=C["entrada"], fg=C["texto"],
                      relief="flat", bd=0, wrap="word",
                      padx=12, pady=10)
        txt.pack(fill="both", expand=True)

        for cat, item in resultados:
            txt.insert("end", f"[{cat}]  {item.get('data', '')[:10]}\n",
                       )
            txt.insert("end", f"  {item['texto']}\n\n")

        txt.config(state="disabled")

        tk.Button(win, text="Fechar",
                  command=win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(pady=(8, 12))


def abrir_listas_mentais(parent):
    """Abre o painel de Organizações da Mente em Listas"""
    ListasMentaisUI(parent)
