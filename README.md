# 🎵 Projeto Caxinguele v2 — Audiobooks para Alexa

Um sistema acessível que converte documentos (PDF, Word, EPUB, Email, etc.) em audiobooks em português brasileiro, com acesso via Alexa e interface intuitiva no desktop.

---

## 🚀 Como Usar

### Interface Desktop

```bash
python audiobook_gui.py
```

**Fluxo principal:**
1. Arraste ou selecione um documento
2. Digite o nome (aparece na Alexa)
3. Clique "CONVERTER E PUBLICAR"
4. Aguarde o processamento
5. Diga ao seu Alexa: "Abre meus audiobooks"

### Comandos Alexa

```
"Alexa, abre meus audiobooks"
→ Lista os menus principais

Dentro de um menu:
"99" → Voltar ao menu principal
"98" → Repetir as opções
"1", "2", "3"... → Selecionar item
```

---

## 📁 O Que Há Aqui

### Menus Principais

| Menu | Acesso | Função |
|------|--------|--------|
| **Organizações Mentais** | Gravar tarefas/ideias | Dita ideias que viram listas |
| **Últimas Atualizações** | Recém-adicionados | Audiobooks novos da semana |
| **Livros** | Biblioteca completa | Todos os audiobooks |
| **Favoritos** | Itens marcados | Salvos, notícias, emails, docs |
| **Música** | Playlists | Músicas organizadas |
| **Calendário** | Compromissos | Proximos eventos, editar datas |
| **Reuniões** | Gravadas | Resumo, detalhes ou íntegra |
| **Configurações** | Voz, velocidade | Personalize a experiência |
| **Listas** | Compras, lembretes | Listas compartilhadas |

### Painel de Edição (Desktop)

- **Labirinto de Números** — estrutura visual dos menus
- **Analytics** — histórico de documentos enviados
- **Histórico** — últimos conversores
- **Gerenciar Equipe** — colaboradores

---

## 🔧 Dependências

### Instaladas

- **Edge-TTS** — Vozes neurais (Francisca, Camila, Antonio, Thalita)
- **PyMuPDF** — Processamento de PDFs
- **Google Drive API** — Upload automático
- **Tkinter** — Interface desktop

### Opcionais

Para ler arquivos Kindle (.mobi):
```bash
pip install mobi
```

Para OCR de imagens digitalizadas:
```bash
pip install pytesseract
```
+ Instalar Tesseract: https://github.com/UB-Mannheim/tesseract/wiki

---

## 🎙️ Vozes Disponíveis

Todas em português brasileiro:

- **Francisca** — Feminina, jovem, natural (padrão)
- **Camila** — Feminina, madura, profissional
- **Antonio** — Masculino, claro
- **Thalita** — Feminina, suave

---

## 📤 Fluxo de Publicação

1. **Leitura** → Extrai texto do documento
2. **Classificação** → Detecta tipo (Livro, Email, etc.)
3. **TTS** → Edge-TTS converte para áudio MP3
4. **Google Drive** → Upload em pastas organizadas
5. **RSS/GitHub Pages** → Publica no feed
6. **Alexa** → Disponível no comando "abre meus audiobooks"

---

## ⚙️ Configuração Inicial

### 1. Google Drive (Obrigatório)

```bash
python configurar_token.py
```

→ Autoriza acesso ao Drive (primeira vez apenas)

### 2. Gmail (Opcional)

Para automação de emails:

```bash
python gmail_daemon.py
```

---

## 🛠️ Troubleshooting

**"Arquivo não suportado"**
→ Formatos aceitos: PDF, DOCX, EPUB, TXT, RTF, ODT, EML, MSG, HTML, PNG, JPG

**"Erro ao fazer upload"**
→ Verifique internet e credenciais Google (./configurar_token.py)

**"Áudio muito rápido/lento"**
→ Use o painel "Configurações" → "Velocidade da Fala"

**"Alexa não reconhece o comando"**
→ Experimente: "Alexa, numero 3" em vez de "Alexa, abre menu 3"

---

## 📞 Suporte

Para o amigo (leitor):
- Use os comandos numerados (1, 2, 3...)
- 98 = repetir as opções
- 99 = voltar

Para o desenvolvedor:
- health_monitor.py — verifica dependências
- pdf2audiobook.log — histórico de erros
- CHECKLIST_TESTES_GUI.md — guia de testes

---

**Versão:** 2.0 (Fases 1-2A completas)
**Data:** 22 de fevereiro de 2026
**Alexa Skill:** Certificada na Amazon
