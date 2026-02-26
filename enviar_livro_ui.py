"""
Janela de Upload de Livro para a Alexa — Projeto Caxinguele v2

Fluxo:
  1. Usuário escolhe a CATEGORIA (dropdown lê menus_config.json)
  2. Usuário digita o NOME DO LIVRO
  3. Usuário seleciona a PASTA com arquivos MP3
  4. Clicar em Publicar:
     → Copia MP3s para audiobooks/<categoria>/<nome_livro>/
     → Upload de cada capítulo para Google Drive
     → Atualiza indice.json com categoria específica
     → Publica no GitHub Pages
     → Alexa já tem o livro disponível
"""

import json
import shutil
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

from config import BASE_DIR

INDICE_JSON = BASE_DIR / "audiobooks" / "indice.json"
MENUS_CONFIG = BASE_DIR / "menus_config.json"

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


def _ler_categorias_livros():
    """Lê categorias de livros do menus_config.json (menu numero 2, tipo filtro)."""
    try:
        with open(MENUS_CONFIG, encoding="utf-8") as f:
            menus = json.load(f)
        for menu in menus:
            if menu.get("numero") == 2 and menu.get("tipo") == "filtro":
                # Retorna os nomes completos como "Livros: Inteligência Sensorial"
                return [op["nome"] for op in menu.get("opcoes", [])]
    except Exception:
        pass
    # Fallback com categorias padrão
    return ["Livros: Inteligência Sensorial", "Livros: Geral"]


class EnviarLivroDialog:
    """Dialog de envio de livro (pasta com MP3s) para a Alexa."""

    def __init__(self, parent):
        self.parent = parent
        self.pasta_selecionada = None  # Path da pasta com MP3s

        self.win = tk.Toplevel(parent)
        self.win.title("Enviar Livro para a Alexa")
        self.win.geometry("650x600")
        self.win.configure(bg=C["bg"])
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.focus_set()

        self._construir()

    # ─────────────────────── INTERFACE ───────────────────────

    def _construir(self):
        # ── Header ──
        header = tk.Frame(self.win, bg=C["painel"], pady=12)
        header.pack(fill="x")
        tk.Frame(header, bg=C["acento"], width=4).pack(side="left", fill="y")
        inner = tk.Frame(header, bg=C["painel"], padx=16)
        inner.pack(side="left")
        tk.Label(inner, text="ENVIAR LIVRO PARA A ALEXA",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["painel"], fg=C["texto"]).pack(anchor="w")
        tk.Label(inner,
                 text="Selecione a categoria, o nome e a pasta com MP3s. O livro ficará disponível na Alexa.",
                 font=("Segoe UI", 9),
                 bg=C["painel"], fg=C["texto2"]).pack(anchor="w")

        corpo = tk.Frame(self.win, bg=C["bg"], padx=20, pady=16)
        corpo.pack(fill="both", expand=True)

        # ── Seção 1: Categoria ──
        tk.Label(corpo, text="1   Categoria do Livro",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(anchor="w")
        tk.Label(corpo, text="Onde o livro aparece no menu da Alexa:",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(2, 6))

        categorias = _ler_categorias_livros()
        self.var_categoria = tk.StringVar(value=categorias[0] if categorias else "")

        frame_cat = tk.Frame(corpo, bg=C["painel"], padx=12, pady=10)
        frame_cat.pack(fill="x")

        # Estiliza o Combobox para combinar com o tema escuro
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Livro.TCombobox",
                        fieldbackground=C["entrada"],
                        background=C["entrada"],
                        foreground=C["texto"],
                        selectbackground=C["acento"],
                        selectforeground=C["texto"],
                        font=("Segoe UI", 10))

        self.combo_categoria = ttk.Combobox(
            frame_cat,
            textvariable=self.var_categoria,
            values=categorias,
            state="readonly",
            font=("Segoe UI", 10),
            style="Livro.TCombobox",
        )
        self.combo_categoria.pack(fill="x", ipady=4)

        tk.Frame(corpo, bg=C["bg"], height=14).pack()

        # ── Seção 2: Nome do livro ──
        tk.Label(corpo, text="2   Nome do Livro  (aparece na Alexa)",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(anchor="w")
        tk.Label(corpo, text="Exemplo: Inteligência Emocional, A Arte da Guerra",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(2, 6))

        self.entry_nome = tk.Entry(
            corpo,
            font=("Segoe UI", 11),
            bg=C["entrada"], fg=C["texto"],
            insertbackground=C["texto"],
            relief="flat", bd=0,
        )
        self.entry_nome.pack(fill="x", ipady=8, pady=(0, 0))

        tk.Frame(corpo, bg=C["bg"], height=14).pack()

        # ── Seção 3: Selecionar pasta com MP3s ──
        tk.Label(corpo, text="3   Pasta com os Capítulos (MP3s)",
                 font=("Segoe UI", 10, "bold"),
                 bg=C["bg"], fg=C["texto"]).pack(anchor="w")
        tk.Label(corpo, text="Selecione a pasta que contém os arquivos .mp3 do livro:",
                 font=("Segoe UI", 9),
                 bg=C["bg"], fg=C["texto2"]).pack(anchor="w", pady=(2, 6))

        frame_pasta = tk.Frame(corpo, bg=C["painel"], padx=12, pady=10)
        frame_pasta.pack(fill="x")

        self.label_pasta = tk.Label(
            frame_pasta,
            text="Nenhuma pasta selecionada",
            font=("Segoe UI", 10),
            bg=C["painel"], fg=C["texto2"],
            anchor="w",
        )
        self.label_pasta.pack(side="left", fill="x", expand=True)

        tk.Button(
            frame_pasta,
            text="Selecionar Pasta",
            command=self._selecionar_pasta,
            bg=C["borda"], fg=C["texto"],
            font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=10, pady=4,
        ).pack(side="right")

        # Contador de MP3s encontrados
        self.label_mp3s = tk.Label(
            corpo, text="",
            font=("Segoe UI", 9),
            bg=C["bg"], fg=C["texto2"],
            anchor="w",
        )
        self.label_mp3s.pack(fill="x", pady=(4, 0))

        # ── Status e barra de progresso ──
        self.label_status = tk.Label(
            corpo, text="",
            font=("Segoe UI", 9),
            bg=C["bg"], fg=C["texto2"],
            anchor="w",
        )
        self.label_status.pack(fill="x", pady=(10, 0))

        self.barra = ttk.Progressbar(corpo, mode="indeterminate")
        self.barra.pack(fill="x", pady=(4, 0))

        # ── Botões de ação ──
        frame_acoes = tk.Frame(self.win, bg=C["bg"], padx=20, pady=14)
        frame_acoes.pack(fill="x")

        cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat",
               "cursor": "hand2", "padx": 16, "pady": 8}

        self.btn_publicar = tk.Button(
            frame_acoes,
            text="📚  Publicar na Alexa",
            command=self._publicar,
            bg=C["ok"], fg="#0f1117",
            activebackground="#35c07a", **cfg
        )
        self.btn_publicar.pack(side="left")

        tk.Button(
            frame_acoes,
            text="Cancelar",
            command=self.win.destroy,
            bg=C["borda"], fg=C["texto"],
            activebackground=C["entrada"], **cfg
        ).pack(side="right")

    # ─────────────────────── INTERAÇÃO ───────────────────────

    def _selecionar_pasta(self):
        """Abre diálogo para selecionar pasta com MP3s."""
        caminho = filedialog.askdirectory(
            parent=self.win,
            title="Selecionar Pasta com MP3s do Livro",
        )
        if caminho:
            self.pasta_selecionada = Path(caminho)
            nome_pasta = self.pasta_selecionada.name

            # Conta os MP3s na pasta
            mp3s = sorted(self.pasta_selecionada.glob("*.mp3"))
            qtd = len(mp3s)

            self.label_pasta.config(text=f"✓  {nome_pasta}", fg=C["ok"])
            self.label_mp3s.config(
                text=f"{qtd} arquivo(s) MP3 encontrado(s) nessa pasta.",
                fg=C["texto2"] if qtd > 0 else C["erro"]
            )

            # Auto-preenche nome do livro com o nome da pasta (se vazio)
            if not self.entry_nome.get().strip():
                self.entry_nome.insert(0, nome_pasta.replace("_", " ").replace("-", " "))

            if qtd > 0:
                self.label_status.config(
                    text="Pasta pronta. Clique em Publicar na Alexa.", fg=C["texto2"]
                )

    # ─────────────────────── PUBLICAÇÃO ───────────────────────

    def _publicar(self):
        """Valida e inicia o upload em thread separada."""
        categoria = self.var_categoria.get().strip()
        if not categoria:
            messagebox.showwarning("Atenção", "Selecione uma categoria.", parent=self.win)
            return

        nome_livro = self.entry_nome.get().strip()
        if not nome_livro:
            messagebox.showwarning("Atenção", "Digite o nome do livro.", parent=self.win)
            self.entry_nome.focus_set()
            return

        if not self.pasta_selecionada or not self.pasta_selecionada.exists():
            messagebox.showwarning("Atenção", "Selecione uma pasta com MP3s antes de publicar.", parent=self.win)
            return

        mp3s = sorted(self.pasta_selecionada.glob("*.mp3"))
        if not mp3s:
            messagebox.showwarning("Atenção", "A pasta selecionada não contém arquivos .mp3.", parent=self.win)
            return

        resp = messagebox.askyesno(
            "Confirmar Publicação",
            f"Publicar o livro:\n"
            f"  Nome: {nome_livro}\n"
            f"  Categoria: {categoria}\n"
            f"  Capítulos: {len(mp3s)} arquivos MP3\n\n"
            "Passos:\n"
            "  1) Copia para audiobooks/<categoria>/<nome>/\n"
            "  2) Upload para Google Drive\n"
            "  3) Atualiza indice.json\n"
            "  4) Publica no GitHub Pages\n\n"
            "Deseja continuar?",
            parent=self.win
        )
        if not resp:
            return

        self.btn_publicar.config(state="disabled")
        self.barra.start(12)
        threading.Thread(
            target=self._executar_upload,
            args=(categoria, nome_livro, mp3s),
            daemon=True
        ).start()

    def _executar_upload(self, categoria: str, nome_livro: str, mp3s: list):
        """Thread principal de upload."""
        try:
            total = len(mp3s)

            # Passo 1: Copiar para pasta local audiobooks/<categoria>/<nome_livro>/
            self._status(f"[1/4] Copiando {total} MP3(s) para audiobooks/{nome_livro}/...")
            pasta_dest = BASE_DIR / "audiobooks" / categoria / nome_livro
            pasta_dest.mkdir(parents=True, exist_ok=True)

            for mp3 in mp3s:
                shutil.copy2(mp3, pasta_dest / mp3.name)

            # Passo 2: Upload para Google Drive
            self._status("[2/4] Conectando ao Google Drive...")
            from cloud_uploader import obter_servico_drive, obter_ou_criar_pasta, upload_arquivo
            from config import GDRIVE_CONFIG

            service = obter_servico_drive()
            pasta_raiz_id = GDRIVE_CONFIG.get("pasta_raiz_id") or None

            # Cria estrutura: Audiobooks Caxinguele / <categoria> / <nome_livro>
            pasta_livros_id = obter_ou_criar_pasta(service, "Audiobooks Caxinguele", pasta_raiz_id)
            pasta_cat_id = obter_ou_criar_pasta(service, categoria, pasta_livros_id)
            pasta_livro_id = obter_ou_criar_pasta(service, nome_livro, pasta_cat_id)

            urls_capitulos = []
            for i, mp3 in enumerate(mp3s, 1):
                self._status(f"[2/4] Upload capítulo {i}/{total}: {mp3.name}...")
                destino = pasta_dest / mp3.name
                resultado = upload_arquivo(service, destino, pasta_livro_id)
                if not resultado:
                    raise RuntimeError(f"Upload falhou para: {mp3.name}")
                urls_capitulos.append({
                    "arquivo": mp3.name,
                    "url": resultado["direct_url"]
                })

            # Passo 3: Atualizar indice.json
            self._status("[3/4] Atualizando indice.json...")
            dados = {"documentos": [], "total": 0, "versao": "2.0"}
            if INDICE_JSON.exists():
                with open(INDICE_JSON, encoding="utf-8") as f:
                    dados = json.load(f)

            hoje = datetime.now().strftime("%Y-%m-%d")
            # Remove entradas antigas deste livro (evita duplicatas)
            dados["documentos"] = [
                d for d in dados.get("documentos", [])
                if not (d.get("titulo", "").startswith(nome_livro) and d.get("categoria") == categoria)
            ]

            # Adiciona cada capítulo
            for cap in urls_capitulos:
                dados["documentos"].append({
                    "titulo": f"{nome_livro} - {cap['arquivo'].replace('.mp3', '')}",
                    "url_audio": cap["url"],
                    "categoria": categoria,
                    "data": hoje,
                })

            dados["total"] = len(dados["documentos"])
            dados["atualizado_em"] = datetime.now().isoformat()

            INDICE_JSON.parent.mkdir(parents=True, exist_ok=True)
            with open(INDICE_JSON, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)

            # Passo 4: Git push
            self._status("[4/4] Publicando no GitHub Pages...")
            _git_push_indice()

            # Sucesso
            self.barra.stop()
            self._status(f"✅ '{nome_livro}' ({total} capítulos) publicado na Alexa!", cor=C["ok"])
            self.btn_publicar.config(state="normal")
            self.win.after(0, lambda: messagebox.showinfo(
                "Publicado! 📚",
                f"'{nome_livro}' está disponível na Alexa!\n\n"
                f"Categoria: {categoria}\n"
                f"Capítulos: {total}\n\n"
                "Diga: 'Alexa, abre meus audiobooks'\n"
                "Vá em Livros para encontrar o livro.",
                parent=self.win
            ))

        except Exception as e:
            self.barra.stop()
            self._status(f"Erro: {e}", cor=C["erro"])
            self.btn_publicar.config(state="normal")
            self.win.after(0, lambda: messagebox.showerror(
                "Erro ao Publicar",
                f"Não foi possível publicar o livro:\n\n{e}\n\n"
                "Verifique se o credentials.json está na pasta do projeto.",
                parent=self.win
            ))

    def _status(self, msg: str, cor: str = None):
        """Atualiza label de status (pode ser chamado de thread)."""
        cor = cor or C["aviso"]
        self.label_status.after(0, lambda: self.label_status.config(text=msg, fg=cor))


def _git_push_indice():
    """Faz git add/commit/push do indice.json para publicar no GitHub Pages."""
    try:
        cwd = str(BASE_DIR)
        subprocess.run(
            ["git", "add", "audiobooks/indice.json"],
            cwd=cwd, check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Livro: novo upload via GUI — {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            cwd=cwd, check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push"],
            cwd=cwd, check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        # Se não há nada a commitar, não é erro crítico
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        if "nothing to commit" not in stderr and "up to date" not in stderr:
            raise RuntimeError(f"Git push falhou: {stderr}") from e


def abrir_enviar_livro(parent):
    """Abre o dialog de envio de livro."""
    EnviarLivroDialog(parent)
