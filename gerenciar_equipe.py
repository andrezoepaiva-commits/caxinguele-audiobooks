"""
Gerenciar Equipe — Projeto Caxinguele v2
Gerencia os membros da equipe que têm acesso ao aplicativo.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from config import BASE_DIR
import uuid
import hashlib
from datetime import datetime
import webbrowser

ARQUIVO_EQUIPE = BASE_DIR / "equipe.json"
ARQUIVO_CONVITES = BASE_DIR / "convites.json"


def gerar_codigo_convite():
    """Gera um código único de convite"""
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:12].upper()


def carregar_convites():
    """Carrega os convites gerados"""
    if ARQUIVO_CONVITES.exists():
        try:
            return json.loads(ARQUIVO_CONVITES.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def salvar_convites(convites: dict):
    """Salva os convites em disco"""
    ARQUIVO_CONVITES.write_text(
        json.dumps(convites, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

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


def carregar_equipe():
    """Carrega lista de membros da equipe"""
    if ARQUIVO_EQUIPE.exists():
        try:
            return json.loads(ARQUIVO_EQUIPE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def salvar_equipe(membros: list):
    """Salva lista de membros em disco"""
    ARQUIVO_EQUIPE.write_text(
        json.dumps(membros, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


class DialogGerenciarEquipe:
    """Janela de gerenciamento da equipe"""

    def __init__(self, parent):
        self.parent = parent
        self.membros = carregar_equipe()

        self.win = tk.Toplevel(parent)
        self.win.title("Gerenciar Equipe")
        self.win.geometry("560x460")
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(True, True)
        self.win.minsize(460, 360)

        self._construir_interface()
        self._atualizar_lista()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="GERENCIAR EQUIPE",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner, text="Membros com acesso ao aplicativo Caxinguele",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Tabela
        frame_tree = tk.Frame(self.win, bg=C["bg"])
        frame_tree.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        style = ttk.Style()
        style.configure("Equipe.Treeview",
                        background=C["entrada"],
                        foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10),
                        rowheight=30)
        style.configure("Equipe.Treeview.Heading",
                        background=C["painel"],
                        foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Equipe.Treeview",
                  background=[("selected", C["acento"])])

        colunas = ("nome", "email", "funcao", "desde")
        self.tree = ttk.Treeview(frame_tree, columns=colunas,
                                  show="headings", height=10,
                                  style="Equipe.Treeview",
                                  selectmode="browse")

        self.tree.heading("nome",   text="Nome")
        self.tree.heading("email",  text="Email")
        self.tree.heading("funcao", text="Função")
        self.tree.heading("desde",  text="Desde")

        self.tree.column("nome",   width=160, minwidth=100)
        self.tree.column("email",  width=180, minwidth=140)
        self.tree.column("funcao", width=120, minwidth=80)
        self.tree.column("desde",  width=80, minwidth=70, anchor="center")

        scroll = ttk.Scrollbar(frame_tree, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Botões
        frame_btn = tk.Frame(self.win, bg=C["bg"])
        frame_btn.pack(fill="x", padx=16, pady=(10, 14))

        tk.Button(frame_btn, text="+ Adicionar Membro",
                  command=self._adicionar_membro,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6,
                  activebackground="#35c07a"
                  ).pack(side="left")

        tk.Button(frame_btn, text="📧 Gerar Convite",
                  command=self._gerar_convite,
                  bg=C["acento"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6,
                  activebackground="#5a52e0"
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_btn, text="Remover Selecionado",
                  command=self._remover_membro,
                  bg=C["erro"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6,
                  activebackground="#e04060"
                  ).pack(side="left", padx=(8, 0))

        tk.Button(frame_btn, text="Fechar",
                  command=self.win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6
                  ).pack(side="right")

    def _atualizar_lista(self):
        """Atualiza a tabela com membros atuais"""
        self.tree.delete(*self.tree.get_children())
        for m in self.membros:
            self.tree.insert("", "end", values=(
                m.get("nome", ""),
                m.get("email", ""),
                m.get("funcao", ""),
                m.get("desde", ""),
            ))

    def _adicionar_membro(self):
        """Abre dialog para adicionar novo membro"""
        win = tk.Toplevel(self.win)
        win.title("Adicionar Membro")
        win.geometry("360x280")
        win.configure(bg=C["bg"])
        win.transient(self.win)
        win.grab_set()
        win.resizable(False, False)

        corpo = tk.Frame(win, bg=C["bg"], padx=20, pady=16)
        corpo.pack(fill="both", expand=True)

        tk.Label(corpo, text="Nome completo",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")
        entry_nome = tk.Entry(corpo, font=("Segoe UI", 10),
                              bg=C["entrada"], fg=C["texto"],
                              insertbackground=C["texto"], relief="flat")
        entry_nome.pack(fill="x", ipady=6, pady=(2, 8))
        entry_nome.focus()

        tk.Label(corpo, text="Email (para enviar convite)",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")
        entry_email = tk.Entry(corpo, font=("Segoe UI", 10),
                               bg=C["entrada"], fg=C["texto"],
                               insertbackground=C["texto"], relief="flat")
        entry_email.pack(fill="x", ipady=6, pady=(2, 8))

        tk.Label(corpo, text="Função na equipe",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")
        entry_funcao = tk.Entry(corpo, font=("Segoe UI", 10),
                                bg=C["entrada"], fg=C["texto"],
                                insertbackground=C["texto"], relief="flat")
        entry_funcao.pack(fill="x", ipady=6, pady=(2, 0))

        def salvar():
            nome = entry_nome.get().strip()
            email = entry_email.get().strip()
            funcao = entry_funcao.get().strip()
            if not nome:
                messagebox.showwarning("Aviso", "Digite o nome do membro.", parent=win)
                return
            if not email or "@" not in email:
                messagebox.showwarning("Aviso", "Digite um email válido.", parent=win)
                return
            self.membros.append({
                "nome": nome,
                "email": email,
                "funcao": funcao or "Colaborador",
                "desde": datetime.now().strftime("%d/%m/%Y"),
            })
            salvar_equipe(self.membros)
            self._atualizar_lista()
            win.destroy()

        frame_btn = tk.Frame(win, bg=C["bg"])
        frame_btn.pack(fill="x", padx=20, pady=(0, 14))

        tk.Button(frame_btn, text="Salvar",
                  command=salvar,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6
                  ).pack(side="right")

        tk.Button(frame_btn, text="Cancelar",
                  command=win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=10, pady=6
                  ).pack(side="right", padx=(0, 8))

        win.bind("<Return>", lambda e: salvar())

    def _gerar_convite(self):
        """Gera um link de convite para o membro selecionado"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um membro para gerar convite.", parent=self.win)
            return

        idx = self.tree.index(sel[0])
        membro = self.membros[idx]
        nome = membro.get("nome", "")
        email = membro.get("email", "")

        # Gera código único
        codigo = gerar_codigo_convite()
        convites = carregar_convites()
        convites[codigo] = {
            "email": email,
            "nome": nome,
            "gerado_em": datetime.now().isoformat(),
            "aceito": False
        }
        salvar_convites(convites)

        # Mostra janela com o convite
        win = tk.Toplevel(self.win)
        win.title("Convite Gerado")
        win.geometry("500x280")
        win.configure(bg=C["bg"])
        win.transient(self.win)
        win.grab_set()
        win.resizable(False, False)

        corpo = tk.Frame(win, bg=C["bg"], padx=16, pady=16)
        corpo.pack(fill="both", expand=True)

        tk.Label(corpo, text=f"Convite para {nome}",
                 font=("Segoe UI", 12, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(anchor="w")

        tk.Label(corpo, text=f"Email: {email}",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(4, 12))

        tk.Label(corpo, text="Código de convite:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        frame_codigo = tk.Frame(corpo, bg=C["entrada"], relief="flat", bd=1)
        frame_codigo.pack(fill="x", pady=(4, 12), ipady=8, padx=4)

        tk.Label(frame_codigo, text=codigo,
                 font=("Consolas", 14, "bold"),
                 bg=C["entrada"], fg=C["ok"]).pack()

        tk.Label(corpo, text="Instruções:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        txt_instr = tk.Text(corpo, font=("Segoe UI", 9),
                           bg=C["entrada"], fg=C["texto"],
                           height=4, relief="flat", bd=0)
        txt_instr.pack(fill="both", expand=True, ipady=6, padx=4)
        txt_instr.insert("1.0", f"1. Compartilhe este código com {nome}:\n"
                                f"   {codigo}\n\n"
                                f"2. Ele abrirá o app Caxinguele\n"
                                f"3. Colocará o código para se autenticar")
        txt_instr.config(state="disabled")

        def copiar():
            self.win.clipboard_clear()
            self.win.clipboard_append(codigo)
            messagebox.showinfo("Sucesso", f"Código copiado para clipboard!", parent=win)

        frame_btn = tk.Frame(win, bg=C["bg"])
        frame_btn.pack(fill="x", padx=16, pady=(0, 16))

        tk.Button(frame_btn, text="Copiar Código",
                  command=copiar,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=14, pady=6).pack(side="left")

        tk.Button(frame_btn, text="Fechar",
                  command=win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=10, pady=6).pack(side="right")

    def _remover_membro(self):
        """Remove o membro selecionado"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um membro para remover.", parent=self.win)
            return

        idx = self.tree.index(sel[0])
        nome = self.membros[idx].get("nome", "")

        confirmar = messagebox.askyesno(
            "Confirmar",
            f"Remover '{nome}' da equipe?",
            parent=self.win
        )
        if confirmar:
            self.membros.pop(idx)
            salvar_equipe(self.membros)
            self._atualizar_lista()


def abrir_gerenciar_equipe(parent):
    """Abre o painel de gerenciamento da equipe"""
    DialogGerenciarEquipe(parent)
