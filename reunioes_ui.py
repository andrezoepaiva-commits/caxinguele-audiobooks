"""
Reuniões Caxinguelê — Menu 8 do Super Alexa
Gerencia o histórico de reuniões: agenda, resumos e transcrições.

Submenus:
  1. Próximas reuniões agendadas
  2. Resumo da última reunião
  3. Íntegra da última reunião
  4. Histórico de reuniões (todas)

Ações disponíveis: adicionar, editar, remover reunião.
"""

import json
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

ARQUIVO_REUNIOES = BASE_DIR / "reunioes.json"

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

SUBMENUS = [
    "Próximas reuniões agendadas",
    "Resumo da última reunião",
    "Íntegra da última reunião",
    "Histórico de reuniões (todas)",
]


# ─────────────────────────── DADOS ────────────────────────────

def carregar_reunioes() -> list:
    if ARQUIVO_REUNIOES.exists():
        try:
            return json.loads(ARQUIVO_REUNIOES.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def salvar_reunioes(reunioes: list):
    ARQUIVO_REUNIOES.write_text(
        json.dumps(reunioes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ─────────────────────────── INTERFACE ────────────────────────────

class ReunioesUI:
    """Painel de Reuniões Caxinguelê — Menu 8"""

    def __init__(self, parent):
        self.parent = parent
        self.reunioes = carregar_reunioes()
        self.aba_atual = "todas"   # "proximas", "ultima", "integra", "todas"

        self.win = tk.Toplevel(parent)
        self.win.title("Reuniões Caxinguelê — Menu 8")
        self.win.geometry("900x600")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(720, 440)

        self._construir_interface()
        self._mostrar_todas()

    def _construir_interface(self):
        # ── Header ──
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text="REUNIÕES CAXINGUELÊ",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner,
                 text="Gerencie reuniões passadas e futuras  |  duplo-clique para ver detalhes",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # ── Abas (submenus) ──
        frame_abas = tk.Frame(self.win, bg=C["bg"])
        frame_abas.pack(fill="x", padx=16, pady=(10, 0))

        self.btn_abas = {}
        abas = [
            ("proximas", "1. Próximas"),
            ("ultima",   "2. Resumo da Última"),
            ("integra",  "3. Íntegra da Última"),
            ("todas",    "4. Histórico Completo"),
        ]
        for chave, texto in abas:
            b = tk.Button(frame_abas, text=texto,
                          command=lambda c=chave: self._mudar_aba(c),
                          bg=C["borda"], fg=C["texto2"],
                          font=("Segoe UI", 9), relief="flat",
                          cursor="hand2", padx=10, pady=5)
            b.pack(side="left", padx=(0, 4))
            self.btn_abas[chave] = b

        # ── Painel de conteúdo ──
        self.frame_conteudo = tk.Frame(self.win, bg=C["bg"])
        self.frame_conteudo.pack(fill="both", expand=True, padx=16, pady=(8, 0))

        # Treeview de reuniões (histórico)
        style = ttk.Style()
        style.configure("Reu.Treeview",
                        background=C["entrada"], foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10), rowheight=28)
        style.configure("Reu.Treeview.Heading",
                        background=C["painel"], foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Reu.Treeview", background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(self.frame_conteudo,
                                  columns=("data", "hora", "participantes", "resumo"),
                                  show="headings",
                                  style="Reu.Treeview",
                                  height=10)
        self.tree.heading("data",          text="Data")
        self.tree.heading("hora",          text="Hora")
        self.tree.heading("participantes", text="Participantes")
        self.tree.heading("resumo",        text="Resumo / Assunto")
        self.tree.column("data",          width=100, minwidth=80,  anchor="center")
        self.tree.column("hora",          width=70,  minwidth=60,  anchor="center")
        self.tree.column("participantes", width=180, minwidth=100)
        self.tree.column("resumo",        width=400, minwidth=150)

        scroll = ttk.Scrollbar(self.frame_conteudo, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.tag_configure("futura",  foreground=C["ok"])
        self.tree.tag_configure("hoje",    foreground=C["aviso"])
        self.tree.tag_configure("passada", foreground=C["texto2"])

        self.tree.bind("<Double-1>", self._ver_detalhes)

        # ── Painel de texto (resumo/íntegra) ──
        self.frame_texto = tk.Frame(self.win, bg=C["bg"])
        # (montado sob demanda nas abas)

        # ── Botões de ação ──
        frame_acoes = tk.Frame(self.win, bg=C["bg"])
        frame_acoes.pack(fill="x", padx=16, pady=(10, 12))

        cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
               "cursor": "hand2", "padx": 14, "pady": 6}

        tk.Button(frame_acoes, text="+ Nova Reunião",
                  command=self._nova_reuniao,
                  bg=C["acento"], fg="white",
                  activebackground="#5a52e0", **cfg
                  ).pack(side="left")

        tk.Button(frame_acoes, text="Editar",
                  command=self._editar_reuniao,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_acoes, text="Remover",
                  command=self._remover_reuniao,
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

        # Destaca aba inicial
        self._mudar_aba("todas")

    # ─────────────────────────── ABAS ────────────────────────────

    def _mudar_aba(self, chave: str):
        """Muda a aba ativa e atualiza conteúdo."""
        self.aba_atual = chave
        for k, b in self.btn_abas.items():
            if k == chave:
                b.config(bg=C["acento"], fg="white")
            else:
                b.config(bg=C["borda"], fg=C["texto2"])

        if chave == "proximas":
            self._mostrar_proximas()
        elif chave == "ultima":
            self._mostrar_resumo_ultima()
        elif chave == "integra":
            self._mostrar_integra_ultima()
        else:
            self._mostrar_todas()

    def _reunioes_ordenadas(self) -> list:
        """Retorna reuniões ordenadas por data+hora."""
        def chave(r):
            try:
                return datetime.strptime(
                    f"{r.get('data', '01/01/2099')} {r.get('hora', '00:00')}",
                    "%d/%m/%Y %H:%M"
                )
            except Exception:
                return datetime(2099, 1, 1)
        return sorted(self.reunioes, key=chave)

    def _tag_por_data(self, data_str: str) -> str:
        try:
            dt = datetime.strptime(data_str, "%d/%m/%Y").date()
            hoje = datetime.now().date()
            if dt < hoje:
                return "passada"
            elif dt == hoje:
                return "hoje"
            else:
                return "futura"
        except Exception:
            return "passada"

    def _preencher_tree(self, reunioes: list):
        self.tree.delete(*self.tree.get_children())
        for r in reunioes:
            self.tree.insert("", "end",
                             iid=r.get("id"),
                             values=(
                                 r.get("data", ""),
                                 r.get("hora", ""),
                                 r.get("participantes", "")[:40],
                                 r.get("resumo", "")[:60],
                             ),
                             tags=(self._tag_por_data(r.get("data", "")),))

    def _mostrar_todas(self):
        self._preencher_tree(self._reunioes_ordenadas())
        total = len(self.reunioes)
        self.label_status.config(
            text=f"{total} reunião(ões)  |  verde = futuras  |  amarelo = hoje  |  cinza = passadas",
            fg=C["texto2"])

    def _mostrar_proximas(self):
        hoje = datetime.now().date()
        proximas = [
            r for r in self._reunioes_ordenadas()
            if self._tag_por_data(r.get("data", "")) in ("futura", "hoje")
        ]
        self._preencher_tree(proximas)
        self.label_status.config(
            text=f"{len(proximas)} reunião(ões) agendada(s) a partir de hoje",
            fg=C["ok"] if proximas else C["texto2"])

    def _mostrar_resumo_ultima(self):
        """Mostra resumo da última reunião passada."""
        self.tree.delete(*self.tree.get_children())
        passadas = [
            r for r in self._reunioes_ordenadas()
            if self._tag_por_data(r.get("data", "")) == "passada"
        ]
        if not passadas:
            self.label_status.config(
                text="Nenhuma reunião passada registrada.", fg=C["texto2"])
            return

        ultima = passadas[-1]  # mais recente das passadas
        resumo = ultima.get("resumo", "(sem resumo)")

        self.tree.insert("", "end",
                         values=(ultima.get("data"), ultima.get("hora"),
                                 ultima.get("participantes", "")[:40],
                                 resumo[:60]),
                         tags=(self._tag_por_data(ultima.get("data", "")),))

        self.label_status.config(
            text=f"Última reunião: {ultima.get('data')}  |  {resumo[:80]}",
            fg=C["texto2"])

    def _mostrar_integra_ultima(self):
        """Mostra a transcrição completa da última reunião."""
        self.tree.delete(*self.tree.get_children())
        passadas = [
            r for r in self._reunioes_ordenadas()
            if self._tag_por_data(r.get("data", "")) == "passada"
        ]
        if not passadas:
            self.label_status.config(
                text="Nenhuma reunião passada registrada.", fg=C["texto2"])
            return

        ultima = passadas[-1]
        transcricao = ultima.get("transcricao", "(sem transcrição)")

        self.tree.insert("", "end",
                         values=(ultima.get("data"), ultima.get("hora"),
                                 ultima.get("participantes", "")[:40],
                                 transcricao[:60]),
                         tags=(self._tag_por_data(ultima.get("data", "")),))

        self.label_status.config(
            text=f"Íntegra de {ultima.get('data')}  |  {len(transcricao)} caracteres",
            fg=C["texto2"])

    # ─────────────────────────── DIALOGS ────────────────────────────

    def _dialog_reuniao(self, titulo_dialog: str, dados: dict = None) -> dict | None:
        """Dialog reutilizável para criar ou editar reunião."""
        dados = dados or {}

        win = tk.Toplevel(self.win)
        win.title(titulo_dialog)
        win.geometry("500x460")
        win.configure(bg=C["bg"])
        win.transient(self.win)
        win.grab_set()

        resultado = {}

        campos = [
            ("Título / Assunto:",         "titulo",        dados.get("titulo", "")),
            ("Data (DD/MM/AAAA):",        "data",          dados.get("data", datetime.now().strftime("%d/%m/%Y"))),
            ("Hora (HH:MM):",             "hora",          dados.get("hora", "19:00")),
            ("Participantes:",            "participantes", dados.get("participantes", "Equipe Caxinguelê")),
        ]

        entries = {}
        for label_txt, chave, valor in campos:
            tk.Label(win, text=label_txt,
                     font=("Segoe UI", 9, "bold"),
                     bg=C["bg"], fg=C["texto2"]).pack(anchor="w", padx=16, pady=(8, 2))
            e = tk.Entry(win, font=("Segoe UI", 10),
                         bg=C["entrada"], fg=C["texto"],
                         insertbackground=C["texto"], relief="flat")
            e.pack(fill="x", padx=16, ipady=5)
            e.insert(0, valor)
            entries[chave] = e

        # Resumo (text widget)
        tk.Label(win, text="Resumo:", font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", padx=16, pady=(8, 2))
        txt_resumo = tk.Text(win, height=4,
                             font=("Segoe UI", 10),
                             bg=C["entrada"], fg=C["texto"],
                             insertbackground=C["texto"], relief="flat",
                             padx=8, pady=6)
        txt_resumo.pack(fill="x", padx=16)
        txt_resumo.insert("1.0", dados.get("resumo", ""))

        entries["titulo"].focus()

        def confirmar(event=None):
            titulo_val = entries["titulo"].get().strip()
            if not titulo_val:
                messagebox.showwarning("Aviso", "O título é obrigatório.", parent=win)
                return
            resultado["titulo"]        = titulo_val
            resultado["data"]          = entries["data"].get().strip() or datetime.now().strftime("%d/%m/%Y")
            resultado["hora"]          = entries["hora"].get().strip() or ""
            resultado["participantes"] = entries["participantes"].get().strip()
            resultado["resumo"]        = txt_resumo.get("1.0", "end").strip()
            resultado["transcricao"]   = dados.get("transcricao", "")
            win.destroy()

        frame_btns = tk.Frame(win, bg=C["bg"])
        frame_btns.pack(fill="x", padx=16, pady=(12, 0))

        tk.Button(frame_btns, text="Confirmar", command=confirmar,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="left")

        tk.Button(frame_btns, text="Cancelar", command=win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="left", padx=(8, 0))

        win.bind("<Return>", confirmar)
        win.wait_window()

        return resultado if resultado else None

    def _ver_detalhes(self, event=None):
        """Mostra detalhes completos da reunião selecionada."""
        sel = self.tree.selection()
        if not sel:
            return
        rid = sel[0]
        r = next((x for x in self.reunioes if x.get("id") == rid), None)
        if not r:
            return

        win = tk.Toplevel(self.win)
        win.title(f"Detalhes — {r.get('titulo', '?')}")
        win.geometry("560x400")
        win.configure(bg=C["bg"])
        win.transient(self.win)

        tk.Label(win, text=r.get("titulo", "?"),
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(pady=(16, 4), padx=16, anchor="w")

        tk.Label(win,
                 text=f"Data: {r.get('data', '?')}   Hora: {r.get('hora', '?')}   Participantes: {r.get('participantes', '?')}",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(padx=16, anchor="w")

        sep = tk.Frame(win, bg=C["borda"], height=1)
        sep.pack(fill="x", padx=16, pady=8)

        tk.Label(win, text="Resumo:", font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["aviso"]).pack(padx=16, anchor="w")

        txt = tk.Text(win, font=("Segoe UI", 10),
                      bg=C["entrada"], fg=C["texto"],
                      relief="flat", padx=10, pady=8,
                      state="disabled", wrap="word")
        txt.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        txt.config(state="normal")
        conteudo = r.get("resumo") or r.get("transcricao") or "(sem conteúdo)"
        txt.insert("1.0", conteudo)
        txt.config(state="disabled")

    # ─────────────────────────── AÇÕES ────────────────────────────

    def _nova_reuniao(self):
        dados = self._dialog_reuniao("Nova Reunião")
        if not dados:
            return
        dados["id"]         = str(uuid.uuid4())[:8]
        dados["criado_em"]  = datetime.now().strftime("%d/%m/%Y %H:%M")
        dados["editado_em"] = ""
        self.reunioes.append(dados)
        salvar_reunioes(self.reunioes)
        self._mudar_aba(self.aba_atual)
        self.label_status.config(
            text=f"Reunião '{dados['titulo']}' adicionada.",
            fg=C["ok"])

    def _reuniao_selecionada(self) -> dict | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Aviso", "Selecione uma reunião primeiro.",
                                parent=self.win)
            return None
        rid = sel[0]
        r = next((x for x in self.reunioes if x.get("id") == rid), None)
        return r

    def _editar_reuniao(self):
        r = self._reuniao_selecionada()
        if not r:
            return
        novos = self._dialog_reuniao("Editar Reunião", dados=r)
        if not novos:
            return
        r.update(novos)
        r["editado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        salvar_reunioes(self.reunioes)
        self._mudar_aba(self.aba_atual)
        self.label_status.config(
            text=f"Reunião '{r['titulo']}' atualizada.",
            fg=C["ok"])

    def _remover_reuniao(self):
        r = self._reuniao_selecionada()
        if not r:
            return
        if not messagebox.askyesno(
                "Remover Reunião",
                f"Remover '{r.get('titulo', '?')}'?\n"
                f"Data: {r.get('data', '?')}  {r.get('hora', '')}",
                parent=self.win):
            return
        self.reunioes = [x for x in self.reunioes if x.get("id") != r.get("id")]
        salvar_reunioes(self.reunioes)
        self._mudar_aba(self.aba_atual)
        self.label_status.config(
            text=f"Reunião '{r.get('titulo')}' removida.",
            fg=C["aviso"])


def abrir_reunioes(parent):
    """Abre o painel de Reuniões Caxinguelê"""
    ReunioesUI(parent)
