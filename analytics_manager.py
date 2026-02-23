"""
Analytics Manager — Projeto Caxinguele v2

Rastreia documentos enviados e exibe dashboard de uso.
Dados salvos localmente em analytics.json.
"""

import json
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

from config import BASE_DIR

# Cores (mesmas do app principal)
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

ANALYTICS_FILE = BASE_DIR / "analytics.json"


def registrar_envio(nome_documento, categoria, arquivo_origem, tempo_conversao_seg=0):
    """Registra um documento enviado no historico de analytics"""
    dados = _carregar_dados()

    evento = {
        "tipo": "envio",
        "documento": nome_documento,
        "categoria": categoria,
        "arquivo": str(arquivo_origem),
        "tempo_conversao": tempo_conversao_seg,
        "data": datetime.now().isoformat(),
    }

    dados["eventos"].append(evento)
    dados["total_envios"] = len([e for e in dados["eventos"] if e["tipo"] == "envio"])
    dados["ultimo_envio"] = evento["data"]

    _salvar_dados(dados)


def _carregar_dados():
    """Carrega analytics.json ou cria estrutura vazia"""
    if ANALYTICS_FILE.exists():
        try:
            with open(ANALYTICS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "eventos": [],
        "total_envios": 0,
        "ultimo_envio": None,
        "criado_em": datetime.now().isoformat(),
    }


def _salvar_dados(dados):
    """Salva analytics.json"""
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


class AnalyticsViewer:
    """Janela de dashboard de analytics"""

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Analytics — Uso do Amigo")
        self.win.geometry("700x550")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(550, 400)

        self.dados = _carregar_dados()
        self._construir_interface()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["aviso"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="ANALYTICS DE USO",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")

        tk.Label(inner, text="Documentos enviados para o amigo",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Cards de resumo
        frame_cards = tk.Frame(self.win, bg=C["bg"])
        frame_cards.pack(fill="x", padx=16, pady=(12, 0))

        envios = self._contar_envios()
        self._card(frame_cards, "Total Enviados", str(envios["total"]), C["acento"])
        self._card(frame_cards, "Este Mes", str(envios["mes"]), C["ok"])
        self._card(frame_cards, "Esta Semana", str(envios["semana"]), C["aviso"])
        self._card(frame_cards, "Categorias", str(envios["categorias"]), C["erro"])

        # Tabela de documentos enviados
        frame_tabela = tk.Frame(self.win, bg=C["bg"])
        frame_tabela.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        tk.Label(frame_tabela, text="HISTORICO DE ENVIOS",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(0, 6))

        colunas = ("data", "documento", "categoria", "tempo")
        self.tree = ttk.Treeview(frame_tabela, columns=colunas,
                                  show="headings", height=10)

        # Estilo
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Analytics.Treeview",
                        background=C["entrada"],
                        foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10),
                        rowheight=26)
        style.configure("Analytics.Treeview.Heading",
                        background=C["painel"],
                        foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Analytics.Treeview",
                  background=[("selected", C["acento"])])

        self.tree.configure(style="Analytics.Treeview")

        self.tree.heading("data", text="Data")
        self.tree.heading("documento", text="Documento")
        self.tree.heading("categoria", text="Tipo")
        self.tree.heading("tempo", text="Conversao")

        self.tree.column("data", width=130, minwidth=100)
        self.tree.column("documento", width=280, minwidth=150)
        self.tree.column("categoria", width=130, minwidth=80)
        self.tree.column("tempo", width=90, minwidth=70, anchor="center")

        scroll = ttk.Scrollbar(frame_tabela, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._popular_tabela()

        # Categorias breakdown
        frame_cat = tk.Frame(self.win, bg=C["bg"])
        frame_cat.pack(fill="x", padx=16, pady=(10, 12))

        categorias = self._contar_por_categoria()
        if categorias:
            tk.Label(frame_cat, text="POR CATEGORIA:  " +
                     "  |  ".join(f"{cat}: {n}" for cat, n in categorias.items()),
                     font=("Segoe UI", 9),
                     bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

    def _card(self, parent, titulo, valor, cor):
        """Cria um card de estatistica"""
        card = tk.Frame(parent, bg=C["entrada"], padx=14, pady=10,
                        highlightbackground=C["borda"], highlightthickness=1)
        card.pack(side="left", fill="x", expand=True, padx=(0, 8))

        tk.Label(card, text=valor,
                 font=("Segoe UI", 22, "bold"),
                 bg=C["entrada"], fg=cor).pack(anchor="w")

        tk.Label(card, text=titulo,
                 font=("Segoe UI", 9),
                 bg=C["entrada"], fg=C["texto2"]).pack(anchor="w")

    def _contar_envios(self):
        """Conta envios por periodo"""
        eventos = [e for e in self.dados.get("eventos", []) if e.get("tipo") == "envio"]
        agora = datetime.now()
        inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = agora - timedelta(days=agora.weekday())
        inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)

        mes = 0
        semana = 0
        cats = set()

        for e in eventos:
            try:
                dt = datetime.fromisoformat(e["data"])
                if dt >= inicio_mes:
                    mes += 1
                if dt >= inicio_semana:
                    semana += 1
            except Exception:
                pass
            cats.add(e.get("categoria", "?"))

        return {
            "total": len(eventos),
            "mes": mes,
            "semana": semana,
            "categorias": len(cats) if cats else 0,
        }

    def _contar_por_categoria(self):
        """Conta documentos por categoria"""
        eventos = [e for e in self.dados.get("eventos", []) if e.get("tipo") == "envio"]
        return dict(Counter(e.get("categoria", "Outros") for e in eventos))

    def _popular_tabela(self):
        """Preenche tabela com envios (mais recentes primeiro)"""
        eventos = [e for e in self.dados.get("eventos", []) if e.get("tipo") == "envio"]
        eventos.reverse()

        for i, e in enumerate(eventos):
            data = e.get("data", "?")[:16].replace("T", " ")
            doc = e.get("documento", "?")
            cat = e.get("categoria", "?")
            tempo = e.get("tempo_conversao", 0)
            tempo_str = f"{tempo // 60}m{tempo % 60:02d}s" if tempo > 0 else "—"

            self.tree.insert("", "end", iid=str(i),
                            values=(data, doc, cat, tempo_str))


def abrir_analytics(parent):
    """Abre a janela de analytics"""
    AnalyticsViewer(parent)


def abrir_historico(parent):
    """Abre o histórico de documentos enviados"""
    AnalyticsViewer(parent)
