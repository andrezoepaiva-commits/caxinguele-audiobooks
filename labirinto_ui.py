"""
Labirinto de Numeros da Alexa — Projeto Caxinguele v2

Visualiza e edita como o amigo cego navega pelos conteudos:
  Nivel 1: Alexa enumera CATEGORIAS  (Livros=2, Artigos=3...)
  Nivel 2: Alexa enumera DOCUMENTOS  dentro da categoria escolhida
  Amigo diz o numero -> audio toca

Esta janela mostra essa estrutura e permite editar.
"""

import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from pathlib import Path
from datetime import datetime

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

INDICE_LOCAL   = BASE_DIR / "indice.json"
ARQUIVO_MENUS  = BASE_DIR / "menus_config.json"  # persistência da estrutura dos menus


# ==================== HELPERS DE AGRUPAMENTO ====================

def _extrair_livro_base_ui(titulo: str) -> str:
    """Extrai o nome base do livro removendo 'Cap XX' e tudo depois."""
    titulo = titulo.strip()
    if titulo.lower().endswith(".mp3"):
        titulo = titulo[:-4]
    match = re.match(r"^(.+?)\s*[-–]\s*Cap(?:itulo|ítulo)?\s*\d+", titulo, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    partes = titulo.split(" - ")
    return partes[0].strip() if len(partes) > 1 else titulo


def _extrair_num_cap_ui(titulo: str) -> int:
    """Extrai o número do capítulo de um título."""
    match = re.search(r"Cap(?:itulo|ítulo)?\s*(\d+)", titulo, re.IGNORECASE)
    return int(match.group(1)) if match else 999


def _agrupar_livros_ui(docs: list) -> list:
    """Agrupa documentos por livro_base, retorna lista de livros com seus capítulos."""
    livros_dict = {}
    for doc in docs:
        livro_base = _extrair_livro_base_ui(doc.get("titulo", ""))
        if livro_base not in livros_dict:
            livros_dict[livro_base] = []
        livros_dict[livro_base].append(doc)

    for livro_base in livros_dict:
        livros_dict[livro_base].sort(
            key=lambda d: _extrair_num_cap_ui(d.get("titulo", ""))
        )

    livros = []
    for livro_base, caps in livros_dict.items():
        nome_exibir = livro_base
        if livro_base.lower() in ("anonymous", "untitled", ""):
            nome_exibir = "Livro sem nome"
        livros.append({
            "livro_base":      livro_base,
            "titulo":          nome_exibir,
            "total_capitulos": len(caps),
            "capitulos":       caps,
        })
    return livros

# Menu padrao: categorias com seus numeros de acesso
# [numero] = o que o amigo fala para entrar naquela categoria
# tipo "recentes" = automatico (ultimos 7 dias), nao editavel
# tipo "filtro"   = filtra documentos pelo campo "categoria"
MENU_PADRAO = [
    # Menu 0 — Gravação livre: sem docs, controlado por Lambda/voz
    {"numero": 0,  "nome": "Organizações Mentais",    "tipo": "gravacao"},

    # Menu 1 — Feed inteligente: só o que ainda não foi visto
    {"numero": 1,  "nome": "Últimas Atualizações",    "tipo": "recentes"},

    # Menu 2 — Livros com submenu de categorias
    {"numero": 2,  "nome": "Livros",                  "tipo": "filtro",  "categoria": "Livros",
     "opcoes": [
         {"numero": 1, "nome": "Livros: Inteligência Sensorial"},
         {"numero": 2, "nome": "Livros: Geral"},
     ],
     "opcoes_apos_selecao": [
         {"numero": 1, "nome": "Começar do Início"},
         {"numero": 2, "nome": "Continuar (onde parou)"},
         {"numero": 3, "nome": "Escolher Capítulo"},
         {"numero": 4, "nome": "Sinopse do Livro"},
     ]},

    # Menu 3 — Favoritos centralizados
    {"numero": 3,  "nome": "Favoritos Importantes",   "tipo": "favoritos",
     "opcoes": [
         {"numero": 1, "nome": "Salvos para Escutar Mais Tarde"},
         {"numero": 2, "nome": "Notícias e Artigos Favoritados"},
         {"numero": 3, "nome": "Emails Favoritados"},
         {"numero": 4, "nome": "Documentos Importantes"},
     ]},

    # Menu 4 — Música com submenus de estilo
    {"numero": 4,  "nome": "Música",                  "tipo": "musica",
     "opcoes": [
         {"numero": 1, "nome": "Músicas Caxinguelê"},
         {"numero": 2, "nome": "Músicas Capoeira",
          "sub": [
              {"numero": 1, "nome": "Música Capoeira Regional"},
              {"numero": 2, "nome": "Música Capoeira Angola"},
          ]},
         {"numero": 3, "nome": "Playlists Personalizadas"},
     ]},

    # Menu 5 — Calendário (lista compromissos → seleciona → edita)
    {"numero": 5,  "nome": "Calendário e Compromissos", "tipo": "calendario",
     "opcoes": [
         {"numero": 1, "nome": "Próximos Compromissos (com opção de editar cada um)"},
         {"numero": 2, "nome": "Marcar Novo Compromisso"},
     ]},

    # Menu 8 — Reuniões: lista numerada (recente→antiga) → escolhe → modo de escuta
    {"numero": 8,  "nome": "Reuniões Caxinguelê",     "tipo": "reunioes",
     "nota": "Alexa lista reuniões numeradas. Amigo escolhe → ouve detalhes → escolhe modo",
     "opcoes_apos_selecao": [
         {"numero": 1, "nome": "Resumo em tópicos"},
         {"numero": 2, "nome": "Resumo pragmático"},
         {"numero": 3, "nome": "Áudio na íntegra"},
     ]},

    # Menu 9 — Configurações (Voz / Velocidade / Guia)
    {"numero": 9,  "nome": "Configurações",           "tipo": "configuracoes",
     "opcoes": [
         {"numero": 1, "nome": "Escolher Voz de Hoje"},
         {"numero": 2, "nome": "Velocidade da Fala"},
         {"numero": 3, "nome": "Guia do Usuário"},
     ]},

    # Menu 10 — Listas de anotações mentais com Editar
    {"numero": 10, "nome": "Organizações da Mente em Listas", "tipo": "listas_mentais",
     "listas_fixas": [
         {"nome": "Ideias Caxinguelê"},
         {"nome": "Compras"},
         {"nome": "Consultas Médicas",
          "sub": ["Endocrinologista", "Dentista", "Urologista", "Cardiologista"]},
         {"nome": "Lembretes Gerais"},
         {"nome": "Tarefas da Semana"},
         {"nome": "Insights Pessoais"},
     ]},
]


def _titulo_curto(titulo):
    """Limpa titulo para exibicao legivel"""
    if titulo.lower().endswith(".mp3"):
        titulo = titulo[:-4]
    titulo = re.sub(r"^.*?Cap\s*\d+\s*[-–]\s*", "", titulo)
    titulo = re.sub(r"\s*[-–]\s*Parte\s*\d+$", "", titulo)
    titulo = re.sub(r"\s+", " ", titulo).strip()
    if titulo.lower() in ("untitled", "sem titulo", ""):
        titulo = "Documento sem nome"
    return titulo


class LabirintoUI:
    """Janela do Labirinto de Numeros da Alexa"""

    def __init__(self, parent):
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title("Labirinto de Numeros da Alexa")
        self.win.geometry("840x600")
        self.win.configure(bg=C["bg"])
        self.win.resizable(True, True)
        self.win.minsize(640, 460)

        self.documentos = []   # Todos os docs do indice.json
        self.menu = []         # Categorias do menu (nivel 1)
        self.modificado = False

        self._construir_interface()
        self._carregar_dados()

    # ─────────────────────────── INTERFACE ────────────────────────────

    def _construir_interface(self):
        # Header
        header = tk.Frame(self.win, bg=C["painel"], pady=10)
        header.pack(fill="x")

        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")

        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text="LABIRINTO DE NÚMEROS DA ALEXA",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")

        tk.Label(inner,
                 text="Nivel 1: amigo escolhe CATEGORIA  |  Nivel 2: amigo escolhe DOCUMENTO",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        self.label_info = tk.Label(inner, text="Carregando...",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"])
        self.label_info.pack(anchor="w")

        # Preview do que Alexa diz ao abrir
        frame_preview = tk.Frame(self.win, bg=C["entrada"], padx=12, pady=8)
        frame_preview.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(frame_preview, text="Alexa dira ao abrir a skill:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["entrada"], fg=C["aviso"]).pack(anchor="w")

        self.label_preview = tk.Label(frame_preview, text="",
                 font=("Consolas", 9),
                 bg=C["entrada"], fg=C["texto"],
                 wraplength=760, justify="left")
        self.label_preview.pack(anchor="w", pady=(4, 0))

        # Arvore de navegacao
        frame_tree = tk.Frame(self.win, bg=C["bg"])
        frame_tree.pack(fill="both", expand=True, padx=16, pady=(10, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Lab.Treeview",
                        background=C["entrada"],
                        foreground=C["texto"],
                        fieldbackground=C["entrada"],
                        font=("Segoe UI", 10),
                        rowheight=26)
        style.configure("Lab.Treeview.Heading",
                        background=C["painel"],
                        foreground=C["texto"],
                        font=("Segoe UI", 10, "bold"))
        style.map("Lab.Treeview",
                  background=[("selected", C["acento"])])

        self.tree = ttk.Treeview(frame_tree,
                                  show="tree headings",
                                  columns=("detalhe",),
                                  selectmode="browse",
                                  style="Lab.Treeview",
                                  height=13)
        self.tree.heading("#0", text="Estrutura de Navegacao")
        self.tree.heading("detalhe", text="Info")
        self.tree.column("#0", width=560, minwidth=300)
        self.tree.column("detalhe", width=180, minwidth=100, anchor="e")

        scroll = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Tags de cor por tipo
        self.tree.tag_configure("cat_com_docs",  foreground=C["aviso"], font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("cat_recentes",  foreground=C["ok"],    font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("cat_vazio",     foreground=C["texto2"])
        self.tree.tag_configure("documento",     foreground=C["texto"])

        self.tree.bind("<Double-1>", self._on_duplo_clique)

        # Botoes
        frame_acoes = tk.Frame(self.win, bg=C["bg"])
        frame_acoes.pack(fill="x", padx=16, pady=(8, 0))

        cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
               "cursor": "hand2", "padx": 12, "pady": 6}

        tk.Button(frame_acoes, text="Renomear",
                  command=self._renomear,
                  bg=C["acento"], fg="white",
                  activebackground="#5a52e0", **cfg
                  ).pack(side="left", padx=(0, 6))

        tk.Button(frame_acoes, text="Subir",
                  command=lambda: self._mover(-1),
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(0, 6))

        tk.Button(frame_acoes, text="Descer",
                  command=lambda: self._mover(1),
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(0, 6))

        tk.Button(frame_acoes, text="+ Submenu",
                  command=self._adicionar_submenu,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="left", padx=(0, 6))

        tk.Button(frame_acoes, text="Remover",
                  command=self._remover,
                  bg=C["erro"], fg="white",
                  activebackground="#cc3355", **cfg
                  ).pack(side="left", padx=(0, 6))

        tk.Button(frame_acoes, text="SALVAR E PUBLICAR",
                  command=self._salvar_e_publicar,
                  bg=C["ok"], fg=C["bg"],
                  activebackground="#35c07a", **cfg
                  ).pack(side="right")

        tk.Button(frame_acoes, text="Atualizar",
                  command=self._carregar_dados,
                  bg=C["borda"], fg=C["texto"],
                  activebackground=C["entrada"], **cfg
                  ).pack(side="right", padx=(0, 6))

        # Status
        self.label_status = tk.Label(self.win, text="",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"])
        self.label_status.pack(fill="x", padx=16, pady=(6, 10))

    # ─────────────────────────── DADOS ────────────────────────────

    def _carregar_dados(self):
        """Carrega indice.json e menus_config.json"""
        self.documentos = []
        self.menu = []

        # Carrega estrutura de menus — prioridade: menus_config.json > indice.json > MENU_PADRAO
        if ARQUIVO_MENUS.exists():
            try:
                self.menu = json.loads(ARQUIVO_MENUS.read_text(encoding="utf-8"))
            except Exception:
                self.menu = list(MENU_PADRAO)
        else:
            self.menu = list(MENU_PADRAO)

        if not INDICE_LOCAL.exists():
            self.label_info.config(text="Nenhum documento publicado ainda.")
            self._popular_tree()
            self._atualizar_preview()
            return

        try:
            with open(INDICE_LOCAL, encoding="utf-8") as f:
                dados = json.load(f)

            self.documentos = dados.get("documentos", [])

            # Se não havia menus_config.json, tenta pegar do indice.json
            if not ARQUIVO_MENUS.exists():
                menu_dados = dados.get("menu", {})
                self.menu = menu_dados.get("categorias", list(MENU_PADRAO))

            atualizado = dados.get("atualizado_em", "?")[:16].replace("T", " ")
            self.label_info.config(
                text=f"{len(self.documentos)} documentos  |  Atualizado: {atualizado}")

        except Exception as e:
            self.label_info.config(text=f"Erro ao carregar: {e}")

        self.modificado = False
        self._popular_tree()
        self._atualizar_preview()

    def _salvar_estrutura(self):
        """Salva estrutura dos menus em menus_config.json (persiste entre sessões)"""
        try:
            ARQUIVO_MENUS.write_text(
                json.dumps(self.menu, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self.label_status.config(
                text=f"Aviso: não foi possível salvar estrutura — {e}",
                fg=C["aviso"])

    def _popular_tree(self):
        """Monta a arvore de navegacao com categorias, submenus e documentos"""
        self.tree.delete(*self.tree.get_children())

        # Agrupa documentos por categoria
        cat_docs = {}
        for orig_idx, doc in enumerate(self.documentos):
            cat = doc.get("categoria", "Documentos")
            if cat not in cat_docs:
                cat_docs[cat] = []
            cat_docs[cat].append((orig_idx, doc))

        for cat in self.menu:
            num = cat["numero"]
            nome = cat["nome"]
            tipo = cat.get("tipo", "filtro")
            cat_iid = f"cat_{num}"

            if tipo == "recentes":
                # Feed inteligente: tudo nao visto, sem limite de dias
                self.tree.insert("", "end", iid=cat_iid,
                               text=f"[{num}]  {nome}",
                               values=("automático — tudo não visto",),
                               tags=("cat_recentes",), open=False)

            elif tipo == "gravacao":
                # Menu 0: gravação livre por voz — duplo-clique abre painel
                self.tree.insert("", "end", iid=cat_iid,
                               text=f"[{num}]  {nome}  ✦ clique duplo para testar",
                               values=('voz livre  |  sinal: "Registrar"',),
                               tags=("cat_recentes",), open=True)
                for txt, info in [
                    ("IA classifica cada trecho automaticamente", "offline"),
                    ('Usuário confirma ou redireciona por número', "interativo"),
                    ("Item salvo na lista correta  →  Menu 10", ""),
                ]:
                    self.tree.insert(cat_iid, "end",
                                   text=f"               →   {txt}",
                                   values=(info,), tags=("documento",))

            elif tipo == "reunioes":
                # Menu 8: lista numerada de reuniões → amigo escolhe → modo de escuta
                hint = "  ✦ clique duplo para gerenciar"
                self.tree.insert("", "end", iid=cat_iid,
                               text=f"[{num}]  {nome}{hint}",
                               values=("listagem numerada",),
                               tags=("cat_recentes",), open=True)
                self.tree.insert(cat_iid, "end",
                               text="          Alexa lista reuniões: [1] Reunião tal — 15/02, [2] ...",
                               values=("recente → antiga",), tags=("cat_vazio",))
                self.tree.insert(cat_iid, "end",
                               text="          Amigo escolhe número → ouve detalhes → escolhe modo:",
                               values=("",), tags=("cat_vazio",))
                for opt in cat.get("opcoes_apos_selecao", []):
                    opt_iid = f"opt_{num}_{opt['numero']}"
                    self.tree.insert(cat_iid, "end",
                                   iid=opt_iid,
                                   text=f"              {opt['numero']}.   {opt['nome']}",
                                   values=("modo de escuta",), tags=("documento",))
                # Repetir / Voltar (padrão em todos)
                self.tree.insert(cat_iid, "end",
                               text=f"              4.   Repetir opções",
                               values=("navegação",), tags=("cat_vazio",))
                self.tree.insert(cat_iid, "end",
                               text=f"              5.   Voltar ao menu principal",
                               values=("navegação",), tags=("cat_vazio",))

            elif tipo in ("configuracoes", "favoritos", "musica", "calendario"):
                # Menus com opções estruturadas — mostra submenus expandidos
                opcoes = cat.get("opcoes", [])
                hint = "  ✦ clique duplo para gerenciar" if tipo in ("calendario", "favoritos", "musica") else ""
                self.tree.insert("", "end", iid=cat_iid,
                               text=f"[{num}]  {nome}{hint}",
                               values=(f"{len(opcoes)} opções",),
                               tags=("cat_recentes",), open=True)
                for opt in opcoes:
                    opt_num = opt.get("numero")
                    opt_nome = opt.get("nome")
                    opt_iid = f"opt_{num}_{opt_num}"
                    sub_opts = opt.get("sub", [])
                    self.tree.insert(cat_iid, "end",
                                   iid=opt_iid,
                                   text=f"          {opt_num}.   {opt_nome}",
                                   values=(f"{len(sub_opts)} sub" if sub_opts else "submenu",),
                                   tags=("documento",), open=bool(sub_opts))
                    for sub in sub_opts:
                        self.tree.insert(opt_iid, "end",
                                       text=f"                    {sub.get('numero')}.   {sub.get('nome')}",
                                       values=("",), tags=("documento",))
                # Repetir / Voltar (padrão em todos os submenus)
                prox_num = len(opcoes) + 1
                self.tree.insert(cat_iid, "end",
                               text=f"          {prox_num}.   Repetir opções",
                               values=("navegação",), tags=("cat_vazio",))
                self.tree.insert(cat_iid, "end",
                               text=f"          {prox_num + 1}.   Voltar ao menu principal",
                               values=("navegação",), tags=("cat_vazio",))

            elif tipo == "listas_mentais":
                # Menu 10: listas de anotações — duplo-clique abre gerenciador
                listas = cat.get("listas_fixas", [])
                self.tree.insert("", "end", iid=cat_iid,
                               text=f"[{num}]  {nome}  ✦ clique duplo para editar",
                               values=(f"{len(listas)} listas",),
                               tags=("cat_recentes",), open=True)
                # Linha de modos de escuta
                self.tree.insert(cat_iid, "end",
                               text="               →   Modos: 1=Resumo  2=Íntegra  3=Elaborar IA  4=Áudio original",
                               values=("",), tags=("cat_vazio",))
                for i, lista in enumerate(listas, 1):
                    lista_nome = lista.get("nome", f"Lista {i}")
                    lista_iid = f"lista_{num}_{i}"
                    sub_listas = lista.get("sub", [])
                    self.tree.insert(cat_iid, "end",
                                   iid=lista_iid,
                                   text=f"          {i}.   {lista_nome}",
                                   values=(f"{len(sub_listas)} sublistas" if sub_listas else "lista",),
                                   tags=("documento",), open=bool(sub_listas))
                    for sub in sub_listas:
                        self.tree.insert(lista_iid, "end",
                                       text=f"                    →   {sub}",
                                       values=("",), tags=("documento",))
                # Repetir / Voltar
                prox = len(listas) + 1
                self.tree.insert(cat_iid, "end",
                               text=f"          {prox}.   Repetir opções",
                               values=("navegação",), tags=("cat_vazio",))
                self.tree.insert(cat_iid, "end",
                               text=f"          {prox + 1}.   Voltar ao menu principal",
                               values=("navegação",), tags=("cat_vazio",))

            else:
                # tipo "filtro" — mostra documentos reais do indice.json
                cat_filtro = cat.get("categoria", nome)
                docs_cat = cat_docs.get(cat_filtro, [])
                count = len(docs_cat)

                if count > 0:
                    info = f"{count} doc{'s' if count != 1 else ''}"
                    tag = "cat_com_docs"
                else:
                    info = "vazio"
                    tag = "cat_vazio"

                # Menu [2] Livros — com submenu de categorias
                opcoes_cat = cat.get("opcoes", [])
                opcoes_livro_acao = cat.get("opcoes_apos_selecao", [])

                if opcoes_cat:
                    # Tem categorias definidas → mostrar submenu de categorias primeiro
                    hint = "  ✦ clique duplo para gerenciar"
                    n_opcoes = len(opcoes_cat)
                    self.tree.insert("", "end", iid=cat_iid,
                                   text=f"[{num}]  {nome}{hint}",
                                   values=(f"{n_opcoes} categorias",), tags=(tag,),
                                   open=True)

                    for opt in opcoes_cat:
                        opt_num = opt.get("numero")
                        opt_nome = opt.get("nome", "")
                        opt_iid = f"opt_{num}_{opt_num}"

                        # Busca livros desta categoria no indice.json
                        # Tenta match pelo nome da categoria
                        livros_desta_cat = []
                        for _, doc in docs_cat:
                            livros_desta_cat.append(doc)
                        livros_agrupados = _agrupar_livros_ui(livros_desta_cat)

                        self.tree.insert(cat_iid, "end",
                                       iid=opt_iid,
                                       text=f"          {opt_num}.   {opt_nome}",
                                       values=("submenu",),
                                       tags=("documento",), open=True)

                        # Dentro da categoria: livros agrupados
                        if livros_agrupados:
                            for i, livro in enumerate(livros_agrupados, 1):
                                n_caps = livro["total_capitulos"]
                                livro_iid = f"livro_{num}_{opt_num}_{i}"
                                self.tree.insert(opt_iid, "end",
                                               iid=livro_iid,
                                               text=f"                    {i}.   {livro['titulo']}  ({n_caps} cap.)",
                                               values=(f"{n_caps} cap.",),
                                               tags=("documento",), open=False)

                                # Opções do livro (após seleção)
                                if opcoes_livro_acao:
                                    for acao in opcoes_livro_acao:
                                        acao_num = acao.get("numero")
                                        acao_nome = acao.get("nome", "")
                                        acao_info = ""
                                        if acao_num == 1:
                                            acao_info = "reproduz cap. 1"
                                        elif acao_num == 2:
                                            acao_info = "DynamoDB salva posição"
                                        elif acao_num == 3:
                                            acao_info = f"submenu com {n_caps} caps"
                                        elif acao_num == 4:
                                            acao_info = "texto descritivo"
                                        self.tree.insert(livro_iid, "end",
                                                       text=f"                              {acao_num}.   {acao_nome}",
                                                       values=(acao_info,), tags=("cat_vazio",))

                                    # Capítulos (submenu da opção 3)
                                    if n_caps > 0:
                                        caps_iid = f"caps_{num}_{opt_num}_{i}"
                                        self.tree.insert(livro_iid, "end",
                                                       iid=caps_iid,
                                                       text=f"                              3 →   Capítulos:",
                                                       values=("",), tags=("cat_vazio",), open=False)
                                        for j, cap_doc in enumerate(livro["capitulos"], 1):
                                            cap_titulo = _titulo_curto(cap_doc.get("titulo", f"Capítulo {j}"))
                                            self.tree.insert(caps_iid, "end",
                                                           text=f"                                        {j}.   {cap_titulo}",
                                                           values=("",), tags=("documento",))

                                # 98/99 por livro
                                self.tree.insert(livro_iid, "end",
                                               text=f"                              98.   Repetir opções",
                                               values=("navegação",), tags=("cat_vazio",))
                                self.tree.insert(livro_iid, "end",
                                               text=f"                              99.   Voltar",
                                               values=("navegação",), tags=("cat_vazio",))

                        # 98/99 por categoria
                        self.tree.insert(opt_iid, "end",
                                       text=f"                    98.   Repetir opções",
                                       values=("navegação",), tags=("cat_vazio",))
                        self.tree.insert(opt_iid, "end",
                                       text=f"                    99.   Voltar",
                                       values=("navegação",), tags=("cat_vazio",))

                    # 98/99 do menu principal de categorias
                    self.tree.insert(cat_iid, "end",
                                   text="          98.   Repetir opções",
                                   values=("navegação",), tags=("cat_vazio",))
                    self.tree.insert(cat_iid, "end",
                                   text="          99.   Voltar ao menu principal",
                                   values=("navegação",), tags=("cat_vazio",))

                else:
                    # Sem categorias definidas — mostra documentos direto
                    hint = ""
                    self.tree.insert("", "end", iid=cat_iid,
                                   text=f"[{num}]  {nome}{hint}",
                                   values=(info,), tags=(tag,),
                                   open=(count > 0))
                    for i, (orig_idx, doc) in enumerate(docs_cat):
                        titulo = _titulo_curto(doc.get("titulo", "?"))
                        data = doc.get("data", "")[:10]
                        self.tree.insert(cat_iid, "end",
                                       iid=f"doc_{orig_idx}",
                                       text=f"          {i + 1}.   {titulo}",
                                       values=(data,), tags=("documento",))

    def _atualizar_preview(self):
        """Mostra exatamente o que Alexa dira ao nivel 1"""
        partes = []
        for cat in self.menu:
            num = cat["numero"]
            nome = cat["nome"]
            tipo = cat.get("tipo", "filtro")

            if tipo in ("recentes", "gravacao", "configuracoes",
                        "favoritos", "musica", "calendario", "reunioes", "listas_mentais"):
                # Menus permanentes: sempre aparecem, independente de documentos
                partes.append(f"{num} para {nome}")
            else:
                # tipo "filtro": só aparece se tiver documentos publicados
                cat_filtro = cat.get("categoria", nome)
                count = sum(1 for d in self.documentos
                           if d.get("categoria", "") == cat_filtro)
                if count > 0:
                    partes.append(f"{num} para {nome}")

        if not partes:
            self.label_preview.config(text='"Sua biblioteca esta vazia."')
        else:
            lista = ", ".join(partes)
            total = len(partes)
            self.label_preview.config(
                text=f'"Você tem {total} opções. {lista}. Qual número?"')

    # ─────────────────────────── ACOES ────────────────────────────

    def _on_duplo_clique(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("doc_"):
            self._renomear()
        elif iid == "cat_0":
            self._abrir_menu0()
        elif iid == "cat_2":
            from livros_ui import abrir_livros
            abrir_livros(self.win)
        elif iid == "cat_3":
            from favoritos_ui import abrir_favoritos
            abrir_favoritos(self.win)
        elif iid == "cat_4":
            from musica_ui import abrir_musica
            abrir_musica(self.win)
        elif iid == "cat_5":
            from calendario_ui import abrir_calendario
            abrir_calendario(self.win)
        elif iid == "cat_8":
            from reunioes_ui import abrir_reunioes
            abrir_reunioes(self.win)
        elif iid == "cat_10":
            from listas_mentais import abrir_listas_mentais
            abrir_listas_mentais(self.win)
        elif iid.startswith("cat_") or iid.startswith("opt_") or iid.startswith("lista_"):
            self._renomear()

    def _abrir_menu0(self):
        """Painel de teste do Menu 0 — Organizações Mentais"""
        from gravacao_mental import simular_gravacao, salvar_itens_nas_listas

        win = tk.Toplevel(self.win)
        win.title("Menu 0 — Organizações Mentais")
        win.geometry("680x520")
        win.configure(bg=C["bg"])
        win.grab_set()

        tk.Label(win, text="ORGANIZAÇÕES MENTAIS  —  Menu 0",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(pady=(16, 2))
        tk.Label(win,
                 text="Simula a fala livre do usuário. A IA classifica e salva nas listas.",
                 font=("Segoe UI", 9), bg=C["bg"], fg=C["texto2"]).pack()

        tk.Label(win, text="Digite como se estivesse falando (encerra com 'Registrar'):",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", padx=16, pady=(14, 2))

        frame_txt = tk.Frame(win, bg=C["borda"], pady=1)
        frame_txt.pack(fill="x", padx=16)
        entrada = tk.Text(frame_txt, height=5, font=("Segoe UI", 10),
                          bg=C["entrada"], fg=C["texto"], insertbackground=C["texto"],
                          relief="flat", padx=10, pady=8, wrap="word")
        entrada.pack(fill="x")
        entrada.insert("1.0",
            "Preciso comprar leite e pão. "
            "Também queria anotar uma ideia para o Caxinguelê: criar playlist por humor. "
            "Me lembre da consulta com o endocrinologista na quinta às 15h.")

        tk.Label(win, text="Resultado da classificação:",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", padx=16, pady=(12, 2))

        frame_res = tk.Frame(win, bg="#0a0c12",
                             highlightbackground=C["borda"], highlightthickness=1)
        frame_res.pack(fill="both", expand=True, padx=16)
        res_txt = tk.Text(frame_res, font=("Consolas", 9), bg="#0a0c12", fg="#82aaff",
                          relief="flat", padx=10, pady=8, state="disabled", wrap="word")
        res_txt.pack(fill="both", expand=True)
        res_txt.tag_config("ok",   foreground=C["ok"])
        res_txt.tag_config("bold", font=("Consolas", 9, "bold"))

        label_alexa = tk.Label(win, text="", font=("Segoe UI", 9, "italic"),
                               bg=C["bg"], fg=C["aviso"], wraplength=640, justify="left")
        label_alexa.pack(anchor="w", padx=16, pady=(6, 0))

        def classificar():
            texto = entrada.get("1.0", "end").strip()
            if not texto:
                return
            res = simular_gravacao(texto)
            res_txt.config(state="normal")
            res_txt.delete("1.0", "end")
            res_txt.insert("end", f"Total: {res['total']} itens\n\n", "bold")
            for i, item in enumerate(res["itens"], 1):
                res_txt.insert("end", f"  [{i}] ", "bold")
                res_txt.insert("end", f"{item['categoria_sugerida']:25}", "ok")
                t = item['texto']
                res_txt.insert("end", f"  {t[:60]}...\n" if len(t) > 60 else f"  {t}\n")
            res_txt.config(state="disabled")
            label_alexa.config(text=f"Alexa diria: \"{res['confirmacao_alexa']}\"")

        def confirmar_salvar():
            texto = entrada.get("1.0", "end").strip()
            if not texto:
                return
            res = simular_gravacao(texto)
            salvar_itens_nas_listas(res["itens"])
            label_alexa.config(text=f"Salvo! {res['total']} item(s) nas listas (Menu 10).")
            win.after(2000, win.destroy)

        frame_btns = tk.Frame(win, bg=C["bg"])
        frame_btns.pack(fill="x", padx=16, pady=10)
        tk.Button(frame_btns, text="Classificar", command=classificar,
                  bg=C["acento"], fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2", padx=16, pady=6).pack(side="left")
        tk.Button(frame_btns, text="Confirmar e Salvar", command=confirmar_salvar,
                  bg=C["ok"], fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2", padx=16, pady=6).pack(side="left", padx=(8, 0))
        tk.Button(frame_btns, text="Fechar", command=win.destroy,
                  bg=C["borda"], fg=C["texto"], font=("Segoe UI", 10),
                  relief="flat", cursor="hand2", padx=16, pady=6).pack(side="right")
        classificar()

    def _renomear(self):
        """Renomeia menu, submenu ou documento selecionado"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um item para renomear.",
                                   parent=self.win)
            return
        iid = sel[0]

        if iid.startswith("doc_"):
            # ── Documento ──
            orig_idx = int(iid.replace("doc_", ""))
            nome_atual = self.documentos[orig_idx].get("titulo", "")
            label = "Novo nome (como a Alexa vai falar):"
            def aplicar(novo):
                self.documentos[orig_idx]["titulo"] = novo
        elif iid.startswith("cat_"):
            # ── Menu principal ──
            num = int(iid.replace("cat_", ""))
            cat = next((c for c in self.menu if c["numero"] == num), None)
            if not cat:
                return
            nome_atual = cat["nome"]
            label = f"Novo nome para Menu [{num}]:"
            def aplicar(novo):
                cat["nome"] = novo
        elif iid.startswith("opt_"):
            # ── Submenu de opções ──
            partes = iid.split("_")
            num_menu, num_opt = int(partes[1]), int(partes[2])
            cat = next((c for c in self.menu if c["numero"] == num_menu), None)
            if not cat:
                return
            opt = next((o for o in cat.get("opcoes", []) if o.get("numero") == num_opt), None)
            if not opt:
                return
            nome_atual = opt["nome"]
            label = f"Novo nome para o submenu [{num_opt}]:"
            def aplicar(novo):
                opt["nome"] = novo
        elif iid.startswith("lista_"):
            # ── Lista do Menu 10 ──
            partes = iid.split("_")
            idx_lista = int(partes[2]) - 1
            listas = next(
                (c.get("listas_fixas", []) for c in self.menu if c["numero"] == 10), []
            )
            if idx_lista >= len(listas):
                return
            nome_atual = listas[idx_lista].get("nome", "")
            label = "Novo nome para esta lista:"
            def aplicar(novo):
                listas[idx_lista]["nome"] = novo
        else:
            messagebox.showinfo("Aviso",
                "Selecione um menu, submenu ou documento para renomear.",
                parent=self.win)
            return

        # Dialog de renomeação (reutilizado para todos os tipos)
        dialog = tk.Toplevel(self.win)
        dialog.title("Renomear")
        dialog.geometry("460x140")
        dialog.configure(bg=C["bg"])
        dialog.transient(self.win)
        dialog.grab_set()

        tk.Label(dialog, text=label,
                 font=("Segoe UI", 10),
                 bg=C["bg"], fg=C["texto"]).pack(padx=16, pady=(16, 4), anchor="w")

        entry = tk.Entry(dialog, font=("Segoe UI", 12),
                         bg=C["entrada"], fg=C["texto"],
                         insertbackground=C["texto"], relief="flat")
        entry.pack(fill="x", padx=16, ipady=6)
        entry.insert(0, nome_atual)
        entry.select_range(0, "end")
        entry.focus_set()

        def confirmar(event=None):
            novo = entry.get().strip()
            if novo and novo != nome_atual:
                aplicar(novo)
                self.modificado = True
                self._salvar_estrutura()
                self._popular_tree()
                self._atualizar_preview()
                self.label_status.config(
                    text=f"Renomeado: '{nome_atual[:30]}' → '{novo[:30]}'",
                    fg=C["ok"])
            dialog.destroy()

        entry.bind("<Return>", confirmar)
        tk.Button(dialog, text="Confirmar", command=confirmar,
                  bg=C["acento"], fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2",
                  padx=16, pady=4).pack(pady=(10, 0))

    def _mover(self, direcao):
        """Move menu inteiro ou documento dentro da categoria (-1=subir, 1=descer)"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um item para mover.",
                                   parent=self.win)
            return
        iid = sel[0]

        if iid.startswith("cat_"):
            # ── Reordenar menu inteiro ──
            num = int(iid.replace("cat_", ""))
            pos = next((i for i, c in enumerate(self.menu) if c["numero"] == num), None)
            if pos is None:
                return
            nova_pos = pos + direcao
            if nova_pos < 0 or nova_pos >= len(self.menu):
                return
            self.menu[pos], self.menu[nova_pos] = self.menu[nova_pos], self.menu[pos]
            self.modificado = True
            self._salvar_estrutura()
            self._popular_tree()
            self._atualizar_preview()
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self.label_status.config(
                text=f"Menu movido para posição {nova_pos + 1}",
                fg=C["ok"])

        elif iid.startswith("doc_"):
            # ── Reordenar documento dentro da categoria ──
            orig_idx = int(iid.replace("doc_", ""))
            doc = self.documentos[orig_idx]
            cat_filtro = doc.get("categoria", "")
            cat_docs = [(i, d) for i, d in enumerate(self.documentos)
                        if d.get("categoria", "") == cat_filtro]
            pos_in_cat = next((p for p, (i, _) in enumerate(cat_docs) if i == orig_idx), None)
            if pos_in_cat is None:
                return
            nova_pos = pos_in_cat + direcao
            if nova_pos < 0 or nova_pos >= len(cat_docs):
                return
            idx_a = cat_docs[pos_in_cat][0]
            idx_b = cat_docs[nova_pos][0]
            self.documentos[idx_a], self.documentos[idx_b] = \
                self.documentos[idx_b], self.documentos[idx_a]
            self.modificado = True
            self._popular_tree()
            self._atualizar_preview()
            self.tree.selection_set(f"doc_{idx_b}")
            self.tree.see(f"doc_{idx_b}")
            self.label_status.config(
                text=f"Movido para posição {nova_pos + 1} em '{cat_filtro}'",
                fg=C["ok"])
        else:
            messagebox.showinfo("Aviso",
                "Selecione um menu ou documento para reordenar.",
                parent=self.win)

    def _remover(self):
        """Remove documento ou submenu selecionado"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um item para remover.",
                                   parent=self.win)
            return
        iid = sel[0]

        if iid.startswith("doc_"):
            # ── Remover documento da biblioteca ──
            orig_idx = int(iid.replace("doc_", ""))
            titulo = _titulo_curto(self.documentos[orig_idx].get("titulo", "?"))
            if not messagebox.askyesno("Confirmar",
                    f"Remover '{titulo}' da biblioteca?\n\n"
                    "O arquivo de áudio não será deletado,\n"
                    "só não aparecerá mais na Alexa.",
                    parent=self.win):
                return
            del self.documentos[orig_idx]
            self.modificado = True
            self._popular_tree()
            self._atualizar_preview()
            self.label_status.config(text=f"Removido: '{titulo}'", fg=C["aviso"])

        elif iid.startswith("opt_"):
            # ── Remover submenu de opções ──
            partes = iid.split("_")
            num_menu, num_opt = int(partes[1]), int(partes[2])
            cat = next((c for c in self.menu if c["numero"] == num_menu), None)
            if not cat:
                return
            opcoes = cat.get("opcoes", [])
            opt = next((o for o in opcoes if o.get("numero") == num_opt), None)
            if not opt:
                return
            if not messagebox.askyesno("Confirmar",
                    f"Remover o submenu '{opt['nome']}' do Menu [{num_menu}]?",
                    parent=self.win):
                return
            cat["opcoes"] = [o for o in opcoes if o.get("numero") != num_opt]
            self.modificado = True
            self._salvar_estrutura()
            self._popular_tree()
            self._atualizar_preview()
            self.label_status.config(
                text=f"Submenu '{opt['nome']}' removido.", fg=C["aviso"])
        else:
            messagebox.showinfo("Aviso",
                "Selecione um documento ou submenu para remover.",
                parent=self.win)

    def _adicionar_submenu(self):
        """Adiciona um novo submenu ao menu selecionado"""
        sel = self.tree.selection()
        if not sel or not sel[0].startswith("cat_"):
            messagebox.showinfo("Aviso",
                "Selecione um menu principal para adicionar submenu.",
                parent=self.win)
            return

        num = int(sel[0].replace("cat_", ""))
        cat = next((c for c in self.menu if c["numero"] == num), None)
        if not cat:
            return

        # Só menus com lista de opções podem receber submenus
        if "opcoes" not in cat:
            messagebox.showinfo("Aviso",
                f"Menu [{num}] não suporta submenus.\n"
                "Apenas menus com opções (Favoritos, Música, Calendário, etc.) aceitam.",
                parent=self.win)
            return

        nome = simpledialog.askstring(
            "Novo Submenu",
            f"Nome do novo submenu no Menu [{num}] — {cat['nome']}:",
            parent=self.win
        )
        if not nome or not nome.strip():
            return

        opcoes = cat["opcoes"]
        novo_num = max((o.get("numero", 0) for o in opcoes), default=0) + 1
        opcoes.append({"numero": novo_num, "nome": nome.strip()})
        self.modificado = True
        self._salvar_estrutura()
        self._popular_tree()
        self._atualizar_preview()
        self.label_status.config(
            text=f"Submenu '{nome.strip()}' adicionado ao Menu [{num}].",
            fg=C["ok"])

    # ─────────────────────────── SALVAR ────────────────────────────

    def _salvar_e_publicar(self):
        """Salva indice.json local e publica no GitHub Pages"""
        if not self.modificado:
            self.label_status.config(text="Nenhuma alteracao para salvar.", fg=C["texto2"])
            return

        indice = {
            "menu": {"categorias": self.menu},
            "documentos": self.documentos,
            "total": len(self.documentos),
            "atualizado_em": datetime.now().isoformat(),
            "versao": "2.0",
        }

        try:
            with open(INDICE_LOCAL, "w", encoding="utf-8") as f:
                json.dump(indice, f, ensure_ascii=False, indent=2)
            self.label_status.config(text="Salvo localmente. Publicando...", fg=C["aviso"])
        except Exception as e:
            self.label_status.config(text=f"Erro ao salvar: {e}", fg=C["erro"])
            return

        threading.Thread(target=self._publicar_github, daemon=True).start()

    def _publicar_github(self):
        """Publica no GitHub Pages em thread separada"""
        try:
            from github_uploader import upload_arquivo_github
            upload_arquivo_github(INDICE_LOCAL, "indice.json")

            self.win.after(0, lambda: self.label_status.config(
                text=f"Publicado! {len(self.documentos)} documentos na Alexa.",
                fg=C["ok"]))
            self.win.after(0, lambda: self.label_info.config(
                text=f"{len(self.documentos)} documentos  |  Publicado: {datetime.now().strftime('%H:%M')}"))
            self.modificado = False

        except Exception as e:
            self.win.after(0, lambda: self.label_status.config(
                text=f"Erro ao publicar: {e}", fg=C["erro"]))


def abrir_labirinto(parent):
    """Abre a janela do Labirinto de Numeros"""
    LabirintoUI(parent)
