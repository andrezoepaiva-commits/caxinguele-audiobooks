"""
Calendário e Compromissos — Menu 5 do Super Alexa
Gerencia compromissos criados pelo usuário.

Ações disponíveis:
- Adicionar novo compromisso (título, data, hora, descrição)
- Editar compromisso existente (qualquer campo)
- Remover compromisso com confirmação
"""

import json
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

ARQUIVO_COMPROMISSOS = BASE_DIR / "compromissos.json"

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

def carregar_compromissos() -> list:
    if ARQUIVO_COMPROMISSOS.exists():
        try:
            return json.loads(ARQUIVO_COMPROMISSOS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def salvar_compromissos(compromissos: list):
    ARQUIVO_COMPROMISSOS.write_text(
        json.dumps(compromissos, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ─────────────────────────── INTERFACE ────────────────────────────

class CalendarioUI:
    """Painel de gerenciamento de compromissos — Menu 5"""

    def __init__(self, parent):
        self.parent = parent
        self.compromissos = carregar_compromissos()

        self.win = tk.Toplevel(parent)
        self.win.title("Calendário e Compromissos — Menu 5")
        self.win.geometry("820x560")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(680, 420)

        self._construir_interface()
        self._atualizar_lista()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text="CALENDÁRIO E COMPROMISSOS",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner,
                 text="Compromissos agendados pelo usuário — duplo-clique para editar",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Tabela de compromissos
        frame_tree = tk.Frame(self.win, bg=C["bg"])
        frame_tree.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        style = ttk.Style()
        style.configure("Cal.Treeview",
                        background=C["entrada"], foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10), rowheight=28)
        style.configure("Cal.Treeview.Heading",
                        background=C["painel"], foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Cal.Treeview", background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(frame_tree,
                                  columns=("data", "hora", "titulo", "descricao"),
                                  show="headings",
                                  style="Cal.Treeview",
                                  height=14)
        self.tree.heading("data",      text="Data")
        self.tree.heading("hora",      text="Hora")
        self.tree.heading("titulo",    text="Compromisso")
        self.tree.heading("descricao", text="Descrição")
        self.tree.column("data",      width=100, minwidth=80,  anchor="center")
        self.tree.column("hora",      width=70,  minwidth=60,  anchor="center")
        self.tree.column("titulo",    width=220, minwidth=150)
        self.tree.column("descricao", width=340, minwidth=150)

        scroll = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self._editar_compromisso())

        # Tags de cor
        self.tree.tag_configure("proximo",  foreground=C["ok"])
        self.tree.tag_configure("hoje",     foreground=C["aviso"])
        self.tree.tag_configure("passado",  foreground=C["texto2"])

        # Botões de ação
        frame_acoes = tk.Frame(self.win, bg=C["bg"])
        frame_acoes.pack(fill="x", padx=16, pady=(10, 12))

        cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
               "cursor": "hand2", "padx": 14, "pady": 6}

        tk.Button(frame_acoes, text="+ Novo Compromisso",
                  command=self._novo_compromisso,
                  bg=C["acento"], fg="white",
                  activebackground="#5a52e0", **cfg
                  ).pack(side="left")

        tk.Button(frame_acoes, text="Editar",
                  command=self._editar_compromisso,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Remover",
                  command=self._remover_compromisso,
                  bg=C["erro"], fg="white",
                  activebackground="#cc3355", **cfg
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Fechar",
                  command=self.win.destroy,
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
        self.compromissos = carregar_compromissos()

        hoje_str = datetime.now().strftime("%d/%m/%Y")
        hoje_dt  = datetime.now().date()

        # Ordena por data+hora (mais próximos primeiro)
        def chave_ordem(c):
            try:
                return datetime.strptime(
                    f"{c.get('data','01/01/2099')} {c.get('hora','00:00')}",
                    "%d/%m/%Y %H:%M"
                )
            except Exception:
                return datetime(2099, 1, 1)

        ordenados = sorted(self.compromissos, key=chave_ordem)

        for comp in ordenados:
            data = comp.get("data", "")
            hora = comp.get("hora", "")
            titulo = comp.get("titulo", "")
            desc = comp.get("descricao", "")[:60]

            # Cor por data
            try:
                data_dt = datetime.strptime(data, "%d/%m/%Y").date()
                if data_dt < hoje_dt:
                    tag = "passado"
                elif data_dt == hoje_dt:
                    tag = "hoje"
                else:
                    tag = "proximo"
            except Exception:
                tag = "proximo"

            self.tree.insert("", "end",
                             iid=comp.get("id"),
                             values=(data, hora, titulo, desc),
                             tags=(tag,))

        total = len(self.compromissos)
        self.label_status.config(
            text=f"{total} compromisso(s)  |  verde = próximos  |  amarelo = hoje  |  cinza = passados"
        )

    def _compromisso_selecionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione um compromisso primeiro.",
                                parent=self.win)
            return None
        comp_id = sel[0]
        for c in self.compromissos:
            if c.get("id") == comp_id:
                return c
        return None

    # ─────────────────────────── DIALOGS ────────────────────────────

    def _dialog_compromisso(self, titulo_dialog: str, dados: dict = None) -> dict | None:
        """
        Dialog reutilizável para criar ou editar compromisso.
        Retorna dict com os dados preenchidos, ou None se cancelado.
        """
        dados = dados or {}

        win = tk.Toplevel(self.win)
        win.title(titulo_dialog)
        win.geometry("460x320")
        win.configure(bg=C["bg"])
        win.transient(self.win)
        win.grab_set()

        resultado = {}

        campos = [
            ("Título do compromisso:",  "titulo",    dados.get("titulo", "")),
            ("Data (DD/MM/AAAA):",      "data",      dados.get("data",  datetime.now().strftime("%d/%m/%Y"))),
            ("Hora (HH:MM):",           "hora",      dados.get("hora",  datetime.now().strftime("%H:%M"))),
            ("Descrição (opcional):",   "descricao", dados.get("descricao", "")),
        ]

        entries = {}
        for label_txt, chave, valor_padrao in campos:
            tk.Label(win, text=label_txt,
                     font=("Segoe UI", 9, "bold"),
                     bg=C["bg"], fg=C["texto2"]).pack(anchor="w", padx=16, pady=(10, 2))
            e = tk.Entry(win, font=("Segoe UI", 10),
                         bg=C["entrada"], fg=C["texto"],
                         insertbackground=C["texto"], relief="flat")
            e.pack(fill="x", padx=16, ipady=6)
            e.insert(0, valor_padrao)
            entries[chave] = e

        entries["titulo"].focus()

        def confirmar(event=None):
            titulo_val = entries["titulo"].get().strip()
            if not titulo_val:
                messagebox.showwarning("Aviso", "O título é obrigatório.", parent=win)
                return
            resultado["titulo"]    = titulo_val
            resultado["data"]      = entries["data"].get().strip() or datetime.now().strftime("%d/%m/%Y")
            resultado["hora"]      = entries["hora"].get().strip() or ""
            resultado["descricao"] = entries["descricao"].get().strip()
            win.destroy()

        frame_btns = tk.Frame(win, bg=C["bg"])
        frame_btns.pack(fill="x", padx=16, pady=(12, 0))

        tk.Button(frame_btns, text="Confirmar",
                  command=confirmar,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="left")

        tk.Button(frame_btns, text="Cancelar",
                  command=win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="left", padx=(8, 0))

        win.bind("<Return>", confirmar)
        win.wait_window()

        return resultado if resultado else None

    def _novo_compromisso(self):
        dados = self._dialog_compromisso("Novo Compromisso")
        if not dados:
            return
        dados["id"] = str(uuid.uuid4())[:8]
        dados["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.compromissos.append(dados)
        salvar_compromissos(self.compromissos)
        self._atualizar_lista()
        self.label_status.config(
            text=f"Compromisso '{dados['titulo']}' adicionado.",
            fg=C["ok"])

    def _editar_compromisso(self):
        comp = self._compromisso_selecionado()
        if not comp:
            return
        novos = self._dialog_compromisso("Editar Compromisso", dados=comp)
        if not novos:
            return
        # Atualiza campos no objeto original
        comp["titulo"]    = novos["titulo"]
        comp["data"]      = novos["data"]
        comp["hora"]      = novos["hora"]
        comp["descricao"] = novos["descricao"]
        comp["editado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        salvar_compromissos(self.compromissos)
        self._atualizar_lista()
        self.label_status.config(
            text=f"Compromisso '{comp['titulo']}' atualizado.",
            fg=C["ok"])

    def _remover_compromisso(self):
        comp = self._compromisso_selecionado()
        if not comp:
            return
        confirmar = messagebox.askyesno(
            "Remover Compromisso",
            f"Remover '{comp['titulo']}'?\n\n"
            f"Data: {comp.get('data', '?')}  {comp.get('hora', '')}\n"
            f"{comp.get('descricao', '')}",
            parent=self.win
        )
        if confirmar:
            self.compromissos = [c for c in self.compromissos
                                 if c.get("id") != comp.get("id")]
            salvar_compromissos(self.compromissos)
            self._atualizar_lista()
            self.label_status.config(
                text=f"Compromisso '{comp['titulo']}' removido.",
                fg=C["aviso"])


def abrir_calendario(parent):
    """Abre o painel de Calendário e Compromissos"""
    CalendarioUI(parent)
