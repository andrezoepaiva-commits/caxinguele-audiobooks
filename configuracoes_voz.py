"""
Configurações de Voz — Projeto Caxinguele v2
Permite personalizar a voz usada para geração dos audiobooks.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from config import BASE_DIR

ARQUIVO_CONFIG = BASE_DIR / "config_voz.json"

VOZES_DISPONIVEIS = [
    ("Thalita (padrão)",    "pt-BR-ThalitaNeural"),
    ("Francisca",           "pt-BR-FranciscaNeural"),
    ("Antônio",             "pt-BR-AntonioNeural"),
]

VELOCIDADES = [
    ("Muito devagar  (−30%)",  "-30%"),
    ("Devagar        (−15%)",  "-15%"),
    ("Normal          (0%)",    "0%"),
    ("Rápido         (+15%)",  "+15%"),
    ("Muito rápido   (+30%)",  "+30%"),
]

C = {
    "bg":      "#0f1117",
    "painel":  "#1a1d27",
    "borda":   "#2a2d3e",
    "acento":  "#6c63ff",
    "ok":      "#43d98c",
    "erro":    "#ff5370",
    "texto":   "#e8eaf6",
    "texto2":  "#8b8fa8",
    "entrada": "#252836",
}


def carregar_config():
    """Carrega configurações salvas ou retorna padrão"""
    if ARQUIVO_CONFIG.exists():
        try:
            return json.loads(ARQUIVO_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"voz": "pt-BR-ThalitaNeural", "velocidade": "0%"}


def salvar_config(config: dict):
    """Salva configurações em disco"""
    ARQUIVO_CONFIG.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


class DialogConfiguracoesVoz:
    """Janela de configurações de voz"""

    def __init__(self, parent):
        self.parent = parent
        self.config = carregar_config()

        self.win = tk.Toplevel(parent)
        self.win.title("Configurações de Voz")
        self.win.geometry("460x380")
        self.win.configure(bg=C["bg"])
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, False)

        self._construir_interface()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="CONFIGURAÇÕES DE VOZ",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner, text="Personalize a voz dos audiobooks do seu amigo",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Corpo
        corpo = tk.Frame(self.win, bg=C["bg"], padx=20, pady=16)
        corpo.pack(fill="both", expand=True)

        # --- Seleção de voz ---
        tk.Label(corpo, text="Voz",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        self.var_voz = tk.StringVar(value=self.config.get("voz", "pt-BR-ThalitaNeural"))

        for nome, valor in VOZES_DISPONIVEIS:
            tk.Radiobutton(
                corpo, text=nome,
                variable=self.var_voz, value=valor,
                bg=C["bg"], fg=C["texto"],
                selectcolor=C["entrada"],
                activebackground=C["bg"],
                font=("Segoe UI", 10),
                cursor="hand2"
            ).pack(anchor="w", pady=2)

        tk.Frame(corpo, bg=C["borda"], height=1).pack(fill="x", pady=12)

        # --- Velocidade ---
        tk.Label(corpo, text="Velocidade de fala",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        self.var_velocidade = tk.StringVar(value=self.config.get("velocidade", "0%"))

        frame_vel = tk.Frame(corpo, bg=C["bg"])
        frame_vel.pack(anchor="w", pady=(4, 0))

        for nome, valor in VELOCIDADES:
            tk.Radiobutton(
                frame_vel, text=nome,
                variable=self.var_velocidade, value=valor,
                bg=C["bg"], fg=C["texto"],
                selectcolor=C["entrada"],
                activebackground=C["bg"],
                font=("Segoe UI", 10),
                cursor="hand2"
            ).pack(anchor="w", pady=1)

        # Botões
        frame_btn = tk.Frame(self.win, bg=C["bg"])
        frame_btn.pack(fill="x", padx=20, pady=(0, 14))

        tk.Button(frame_btn, text="Salvar",
                  command=self._salvar,
                  bg=C["ok"], fg=C["bg"],
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=16, pady=6,
                  activebackground="#35c07a"
                  ).pack(side="right")

        tk.Button(frame_btn, text="Cancelar",
                  command=self.win.destroy,
                  bg=C["borda"], fg=C["texto"],
                  font=("Segoe UI", 10),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6
                  ).pack(side="right", padx=(0, 8))

    def _salvar(self):
        config = {
            "voz": self.var_voz.get(),
            "velocidade": self.var_velocidade.get(),
        }
        salvar_config(config)
        messagebox.showinfo(
            "Salvo",
            "Configurações de voz salvas com sucesso!\n"
            "Serão aplicadas no próximo documento convertido.",
            parent=self.win
        )
        self.win.destroy()


def abrir_configuracoes_voz(parent):
    """Abre o painel de configurações de voz"""
    DialogConfiguracoesVoz(parent)
