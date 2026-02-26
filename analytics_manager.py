"""
Analytics Manager — Projeto Caxinguele v2

Rastreia documentos enviados e exibe dashboard de uso.
Dados salvos localmente em analytics.json.

Classes:
  - AnalyticsDashboard: Cards resumo + gráfico de categorias
  - HistoricoViewer: Tabela cronológica + botão Exportar CSV
"""

import csv
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

from config import BASE_DIR

# ID de usuário padrão para busca no DynamoDB (substitua pelo user_id real da Alexa se necessário)
DYNAMODB_LISTENING_TABLE = "caxinguele_listening_history"
AWS_REGION = "us-east-1"


def _buscar_tempo_leitura_aws(periodo="mes"):
    """
    Busca estatísticas de tempo de leitura direto do DynamoDB (via boto3 local).
    Retorna dict com total_minutos, horas_minutos, media_por_dia, top_documentos.
    Se não conseguir conectar, retorna zeros sem mostrar erro para o usuário.
    """
    try:
        import boto3
        from boto3.dynamodb.conditions import Key as DynKey

        dynamo = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamo.Table(DYNAMODB_LISTENING_TABLE)

        # Define corte de data
        agora = datetime.utcnow()
        if periodo == "mes":
            corte = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif periodo == "semana":
            corte = agora - timedelta(days=agora.weekday())
            corte = corte.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # hoje
            corte = agora.replace(hour=0, minute=0, second=0, microsecond=0)

        corte_str = corte.isoformat() + "Z"

        # Scan por todas as sessões concluídas após o corte
        resp = table.scan(
            FilterExpression="#s = :s AND data_sessao >= :corte",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "concluida", ":corte": corte_str},
        )
        sessoes = resp.get("Items", [])

        total = sum(int(s.get("minutos_ouvidos", 0)) for s in sessoes)
        horas = total // 60
        mins_rest = total % 60
        horas_str = f"{horas}h {mins_rest}min" if horas > 0 else f"{mins_rest}min"

        dias = max(1, (agora - corte).days + 1)
        media = round(total / dias)

        # Top documentos por tempo
        contagem = {}
        for s in sessoes:
            doc = s.get("documento", "Desconhecido")
            contagem[doc] = contagem.get(doc, 0) + int(s.get("minutos_ouvidos", 0))

        total_pct = max(total, 1)
        top = sorted(
            [{"documento": d, "minutos": m, "percentual": int(m / total_pct * 100)}
             for d, m in contagem.items()],
            key=lambda x: -x["minutos"]
        )[:5]

        return {
            "total_minutos":  total,
            "horas_minutos":  horas_str,
            "media_por_dia":  media,
            "top_documentos": top,
            "disponivel":     True,
        }
    except Exception:
        return {
            "total_minutos":  0,
            "horas_minutos":  "—",
            "media_por_dia":  0,
            "top_documentos": [],
            "disponivel":     False,
        }

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


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD — Cards + Gráfico de Categorias
# ═══════════════════════════════════════════════════════════════

class AnalyticsDashboard:
    """Dashboard com resumo e gráfico de categorias."""

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Analytics — Dashboard de Uso")
        self.win.geometry("760x720")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(600, 500)

        self.dados = _carregar_dados()
        self._construir_interface()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["aviso"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="DASHBOARD DE ANALYTICS",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")

        tk.Label(inner, text="Resumo dos documentos enviados para a Alexa",
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

        # Gráfico de barras por categoria (texto simples)
        frame_grafico = tk.Frame(self.win, bg=C["bg"])
        frame_grafico.pack(fill="both", expand=True, padx=16, pady=(16, 0))

        tk.Label(frame_grafico, text="TOP CATEGORIAS",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(0, 8))

        categorias = self._contar_por_categoria()
        total_docs = sum(categorias.values()) or 1

        for cat, qtd in sorted(categorias.items(), key=lambda x: -x[1])[:6]:
            pct = int(qtd / total_docs * 100)
            barras = "█" * (pct // 5)  # 1 barra = 5%
            espaco = "░" * (20 - len(barras))

            linha = tk.Frame(frame_grafico, bg=C["bg"])
            linha.pack(fill="x", pady=2)

            tk.Label(linha, text=f"{cat[:22]:<22}",
                     font=("Consolas", 9),
                     bg=C["bg"], fg=C["texto2"],
                     width=22, anchor="w").pack(side="left")

            tk.Label(linha, text=f"{barras}{espaco}",
                     font=("Consolas", 9),
                     bg=C["bg"], fg=C["acento"]).pack(side="left", padx=(4, 0))

            tk.Label(linha, text=f" {qtd} ({pct}%)",
                     font=("Consolas", 9),
                     bg=C["bg"], fg=C["texto2"]).pack(side="left")

        if not categorias:
            tk.Label(frame_grafico, text="Nenhum documento enviado ainda.",
                     font=("Segoe UI", 10),
                     bg=C["bg"], fg=C["texto2"]).pack(anchor="w")

        # ── Seção de Tempo de Leitura (dados do DynamoDB) ──
        frame_tempo = tk.Frame(self.win, bg=C["bg"])
        frame_tempo.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(frame_tempo, text="TEMPO DE LEITURA (ESTE MÊS)",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(0, 6))

        tempo_dados = _buscar_tempo_leitura_aws(periodo="mes")

        # Cards de tempo
        frame_cards_tempo = tk.Frame(frame_tempo, bg=C["bg"])
        frame_cards_tempo.pack(fill="x")

        self._card(frame_cards_tempo, "Tempo Este Mês", tempo_dados["horas_minutos"], C["acento"])
        self._card(frame_cards_tempo, "Média por Dia",
                   f"{tempo_dados['media_por_dia']} min" if tempo_dados["media_por_dia"] else "—",
                   C["ok"])

        if not tempo_dados["disponivel"]:
            tk.Label(frame_tempo,
                     text="(configure credenciais AWS para ver dados em tempo real)",
                     font=("Segoe UI", 8),
                     bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(4, 0))

        # Top documentos por tempo
        top = tempo_dados.get("top_documentos", [])
        if top:
            tk.Label(frame_tempo, text="TOP DOCUMENTOS POR TEMPO:",
                     font=("Segoe UI", 9, "bold"),
                     bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(8, 4))

            for item in top:
                doc_nome = item["documento"][:28]
                mins = item["minutos"]
                pct = item["percentual"]
                barras = "█" * (pct // 5)
                espaco = "░" * (20 - len(barras))

                linha = tk.Frame(frame_tempo, bg=C["bg"])
                linha.pack(fill="x", pady=1)

                tk.Label(linha, text=f"{doc_nome:<28}",
                         font=("Consolas", 9),
                         bg=C["bg"], fg=C["texto2"],
                         width=28, anchor="w").pack(side="left")

                tk.Label(linha, text=f"{barras}{espaco}",
                         font=("Consolas", 9),
                         bg=C["bg"], fg=C["acento"]).pack(side="left", padx=(4, 0))

                tk.Label(linha, text=f" {mins} min ({pct}%)",
                         font=("Consolas", 9),
                         bg=C["bg"], fg=C["texto2"]).pack(side="left")

        # Rodapé com data do último envio
        ultimo = self.dados.get("ultimo_envio")
        if ultimo:
            data_fmt = ultimo[:16].replace("T", " às ")
            frame_rod = tk.Frame(self.win, bg=C["bg"])
            frame_rod.pack(fill="x", padx=16, pady=(8, 12))
            tk.Label(frame_rod,
                     text=f"Último envio: {data_fmt}",
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


# ═══════════════════════════════════════════════════════════════
#  HISTÓRICO — Tabela cronológica + Exportar CSV
# ═══════════════════════════════════════════════════════════════

class HistoricoViewer:
    """Tabela cronológica de documentos enviados com opção de exportar CSV."""

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Histórico de Envios")
        self.win.geometry("750x520")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(550, 380)

        self.dados = _carregar_dados()
        self._construir_interface()

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="HISTÓRICO DE ENVIOS",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")

        tk.Label(inner, text="Todos os documentos enviados, do mais recente ao mais antigo",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        # Tabela
        frame_tabela = tk.Frame(self.win, bg=C["bg"])
        frame_tabela.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        colunas = ("data", "documento", "categoria", "tempo")
        self.tree = ttk.Treeview(frame_tabela, columns=colunas,
                                  show="headings", height=14)

        # Estilo
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Historico.Treeview",
                        background=C["entrada"],
                        foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10),
                        rowheight=26)
        style.configure("Historico.Treeview.Heading",
                        background=C["painel"],
                        foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Historico.Treeview",
                  background=[("selected", C["acento"])])

        self.tree.configure(style="Historico.Treeview")

        self.tree.heading("data",      text="Data")
        self.tree.heading("documento", text="Documento")
        self.tree.heading("categoria", text="Tipo")
        self.tree.heading("tempo",     text="Conversão")

        self.tree.column("data",      width=130, minwidth=100)
        self.tree.column("documento", width=300, minwidth=150)
        self.tree.column("categoria", width=140, minwidth=80)
        self.tree.column("tempo",     width=90,  minwidth=70, anchor="center")

        scroll = ttk.Scrollbar(frame_tabela, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._popular_tabela()

        # Barra inferior: total + botão exportar
        frame_rodape = tk.Frame(self.win, bg=C["bg"], padx=16, pady=12)
        frame_rodape.pack(fill="x")

        eventos = [e for e in self.dados.get("eventos", []) if e.get("tipo") == "envio"]
        tk.Label(frame_rodape,
                 text=f"Total: {len(eventos)} documento(s)",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(side="left")

        tk.Button(
            frame_rodape,
            text="📥  Exportar CSV",
            command=self._exportar_csv,
            bg=C["borda"], fg=C["texto"],
            font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=6,
            activebackground=C["entrada"],
            activeforeground=C["texto"],
        ).pack(side="right")

    def _popular_tabela(self):
        """Preenche tabela com envios (mais recentes primeiro)"""
        eventos = [e for e in self.dados.get("eventos", []) if e.get("tipo") == "envio"]
        eventos.reverse()  # mais recente primeiro

        for i, e in enumerate(eventos):
            data = e.get("data", "?")[:16].replace("T", " ")
            doc  = e.get("documento", "?")
            cat  = e.get("categoria", "?")
            tempo = e.get("tempo_conversao", 0)
            tempo_str = f"{tempo // 60}m{tempo % 60:02d}s" if tempo > 0 else "—"

            self.tree.insert("", "end", iid=str(i),
                            values=(data, doc, cat, tempo_str))

    def _exportar_csv(self):
        """Exporta a tabela como CSV no Desktop."""
        eventos = [e for e in self.dados.get("eventos", []) if e.get("tipo") == "envio"]
        if not eventos:
            messagebox.showinfo("Histórico vazio",
                                "Nenhum documento enviado ainda para exportar.",
                                parent=self.win)
            return

        destino = Path.home() / "Desktop" / "historico_envios.csv"
        try:
            with open(destino, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Data", "Documento", "Tipo", "Conversão (seg)"])
                for e in reversed(eventos):  # mais recente primeiro
                    data  = e.get("data", "")[:16].replace("T", " ")
                    doc   = e.get("documento", "")
                    cat   = e.get("categoria", "")
                    tempo = e.get("tempo_conversao", 0)
                    writer.writerow([data, doc, cat, tempo])

            messagebox.showinfo(
                "Exportado!",
                f"Histórico exportado para:\n{destino}",
                parent=self.win
            )
        except Exception as ex:
            messagebox.showerror(
                "Erro ao exportar",
                f"Não foi possível salvar o CSV:\n{ex}",
                parent=self.win
            )


# ═══════════════════════════════════════════════════════════════
#  Funções de abertura (chamadas pelo audiobook_gui.py)
# ═══════════════════════════════════════════════════════════════

def abrir_analytics(parent):
    """Abre o dashboard com estatísticas e gráfico de categorias."""
    AnalyticsDashboard(parent)


def abrir_historico(parent):
    """Abre a tabela cronológica de envios com botão Exportar CSV."""
    HistoricoViewer(parent)
