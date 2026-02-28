# Checkpoints - Projeto Caxinguele v2

## Status: Fase 2A concluida (22 FEV 2026)

### Fase 1: Suporte Multi-Formato - CONCLUIDA
- [x] `doc_processor.py` criado
- [x] Suporte: DOCX, RTF, ODT, TXT, MD, EPUB, MOBI, EML, MSG, HTML, Imagens (OCR)
- [x] Reutiliza classes LivroProcessado/Capitulo do pdf_processor.py
- [x] Deteccao automatica de headings em DOCX para capitulos
- [x] EPUB extrai capitulos do spine
- [x] Imagens processadas via pytesseract

### Fase 2: Deteccao de Tipo de Documento - CONCLUIDA
- [x] `doc_classifier.py` criado
- [x] Camada 1: por extensao (.epub=Livro, .eml=Email)
- [x] Camada 2: por conteudo (palavras-chave)
- [x] Camada 3: fallback (OUTRO, GUI pode pedir)
- [x] Tipos: LIVRO, ARTIGO_CIENTIFICO, EMAIL, DOCUMENTO_LEGAL, MATERIA_JORNAL, RELATORIO, OUTRO
- [x] Icones e nomes por tipo
- [x] Mapeamento tipo -> pasta Drive

### Fase 3: GUI Multi-Formato + Drag-Drop + Destinatario - CONCLUIDA
- [x] `audiobook_gui.py` reescrito para v2
- [x] Filtro multi-formato no seletor de arquivos
- [x] Area de drag-and-drop (tkinterdnd2, com fallback)
- [x] Icone visual por tipo detectado
- [x] Seletor de destinatario (Eu / Meu Amigo)
- [x] PERFIS_USUARIOS em config.py

### Fase 4: Guia de Operacao em Audio - CONCLUIDA
- [x] `GUIA_ALEXA_ACESSIVEL.md` criado
- [x] ~10 min de conteudo narrado
- [x] Secoes: Cambio, Biblioteca, Comandos, Favoritos, Navegacao, Problemas

### Fase 5: Organizacao Drive por Tipo/Data - CONCLUIDA
- [x] `cloud_uploader.py` atualizado com subpastas automaticas
- [x] Estrutura: Livros/ Artigos/ Emails/ Documentos/ Favoritos/
- [x] `rss_generator.py` atualizado com tags de categoria
- [x] Categoria passada do classificador ao RSS

### Fase 6: Custom Skill Alexa - CONCLUIDA E CERTIFICADA
- [x] Conta developer.amazon.com configurada
- [x] AWS Lambda (Python 3.11) deployada
- [x] Intents: SelecionarNumero, ListarDocumentos, FiltrarPorTipo, LerDocumento, DocumentoNovos
- [x] Interaction model com 84 samples de voz
- [x] `indice_generator.py` — Gera indice.json para Lambda consumir
- [x] `alexa_skill/skill_manifest.json` — Manifesto da skill
- [x] Skill "Meus Audiobooks" aprovada na certificacao Amazon

### Fase 1D-1E: Menus GUI + Dados - CONCLUIDA
- [x] `labirinto_ui.py` — editor visual de estrutura de menus
- [x] `calendario_ui.py` — Menu [5] Calendario e Compromissos
- [x] `favoritos_ui.py` — Menu [3] Favoritos Importantes
- [x] `listas_mentais.py` — Menu [10] Organizacoes da Mente em Listas
- [x] `gravacao_mental.py` — Menu [0] Organizacoes Mentais
- [x] `livros_ui.py` — Menu [2] Livros e Audiobooks
- [x] `musica_ui.py` — Menu [4] Musica
- [x] `reunioes_ui.py` — Menu [8] Reunioes Caxinguele
- [x] JSONs de dados: compromissos, favoritos, listas_mentais, reunioes, menus_config
- [x] Persistencia em menus_config.json

### Fase 2A: Voice Editing Lambda - CONCLUIDA
- [x] Lambda reescrita: state machine multi-nivel (menu/submenu/item/editar)
- [x] Voice editing: Favoritos (remover), Calendario (editar/remover), Reunioes (3 modos), Listas (remover/editar)
- [x] Repetir (98) / Voltar (99) universal em todos os niveis
- [x] Interaction model expandido: 84 samples de voz
- [x] JSONs publicados no GitHub Pages
- [x] .gitignore atualizado para proteger secrets

### Config/Pipeline - CONCLUIDO
- [x] `config.py` atualizado (PERFIS_USUARIOS, MAX_DOC_SIZE_MB, mensagens v2)
- [x] `pipeline_mvp.py` aceita --arquivo (qualquer formato)
- [x] Compatibilidade com --pdf mantida
- [x] Classificacao integrada no pipeline (etapa 2)
- [x] Categoria passada ao upload Drive e RSS
- [x] `requirements.txt` atualizado com novas dependencias

### Sistemas Perpetuos
- [x] `health_monitor.py` — "Avise, nao conserta" (14 pacotes + 11 arquivos verificados)
- [x] `teste_multiformat.py` — Script de teste rapido (5 formatos)
- [x] `CHECKPOINTS.md` — Este arquivo

### Fase 7: Refatoração Menu Livros + Menu YouTube — PRONTO PARA DEPLOY (27 FEV 2026)

#### Parte 1 — Menu Livros
- [x] `indice.json`: removidas 4 duplicatas (3 Livros: Geral sem subcategoria + 1 untitled). Total 14→10. Git push feito.
- [x] `LIVROS_CATEGORIAS`: adicionados `nome_display` e `filtro_subcategoria`
- [x] Filtro por subcategoria em 4 pontos: `_selecionar_submenu`, `_selecionar_acao_item`, `_reconstruir_menu`, `_repetir_opcoes`
- [x] Texto falado: "1 para Livros: Inteligencia Sensorial. 2 para Livros: Geral."
- [x] Sinopse automática: fala n. capítulos + data formatada (ex: "3 capítulos, adicionado em fevereiro de 2026.")
- [x] `AMAZON.PauseIntent`: para o áudio + fala menu de opções (1 pular, 2 voltar, 3 velocidade, 98 repetir, 99 menu)
- [x] Handler `playback_pausado` em `_selecionar_submenu`: reconstrói contexto do token para pular/voltar capítulo
- [x] `_PARENT_MENU`: adicionado `playback_pausado`

#### Parte 2 — Menu YouTube (novo Menu [9])
- [x] `MENU_DEFAULT[9]`: "YouTube e Videos" (tipo "youtube")
- [x] Constantes: `YOUTUBE_API_KEY`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_DEST` (env vars)
- [x] `_menu_youtube()`, `_menu_youtube_canais()`
- [x] `_buscar_videos_canal_rss()`: RSS feed gratuito por channel_id
- [x] `_buscar_youtube_api()`: YouTube Data API v3 + filtro Shorts (< 2 min)
- [x] `_resumir_video_youtube()`: verifica legendas (Claude API = futura integração)
- [x] `_enviar_whatsapp()`: WhatsApp Cloud API
- [x] `_get_canais_youtube()` / `_salvar_canais_youtube()`: DynamoDB (campo `canais_youtube`)
- [x] `_buscar_canal_youtube_api()`: busca canal por nome
- [x] Handlers: `youtube`, `youtube_canal`, `youtube_busca`, `youtube_busca_aguardando`, `youtube_video`, `youtube_canais`, `youtube_canais_remover`
- [x] `YoutubeSearchIntent` no `interaction_model.json` (10 samples, slot AMAZON.SearchQuery)
- [x] `_PARENT_MENU`: 8 novos tipos YouTube

#### Bugs corrigidos na validação
- [x] Bug: PauseIntent durante música (token "MUSICA|||0") exibia "MUSICA, capitulo 1" → adicionado guard `if not livro_base_token.startswith("MUSICA")`
- [x] Bug: Sinopse automática duplicava o título → removido `{titulo}` do fallback
- [x] Bug: `youtube_parent_tipo` não era salvo na sessão → corrigido ao criar `youtube_video`
- [x] Bug: `youtube_busca_aguardando` sem handler → adicionado handler guia o usuário a falar o termo

#### Arquivos modificados
- `C:\Users\andre\Desktop\código.txt` — Lambda (pronto para copiar ao Console)
- `C:\Users\andre\Desktop\interaction_model.json` — pronto para copiar ao Alexa Dev Console
- `audiobooks/indice.json` — limpo, commit f15dbf4, pushed

### Fase 8: Fix YouTube Summary — CONCLUÍDA (28 FEV 2026)
- [x] `_resumir_video_youtube()` reescrita: placeholder → youtube-transcript-api v1.2.4
- [x] Método correto: `YouTubeTranscriptApi().fetch(video_id, languages=['pt','pt-BR','en'])`
- [x] Prioriza legendas em português, fallback para inglês
- [x] Limita transcrição a 3000 chars (Alexa não trunca)
- [x] Edge cases tratados: ID vazio, vídeo inexistente, legendas vazias
- [x] Testado localmente: Rick Astley (dQw4w9WgXcQ) — transcrição em PT extraída OK
- [x] `requirements.txt` atualizado: `youtube-transcript-api>=1.0.0`
- [x] `lambda_function_atual.py` sincronizado com `código.txt`
- [x] Lambda Layer zip criado: `youtube-transcript-layer.zip` (1.7MB, no Desktop)

## Proximos Passos — DEPLOY
1. **Upload Lambda Layer** `youtube-transcript-layer.zip` no Lambda Console
2. **Copiar código.txt para Lambda Console** → Deploy
3. **Copiar interaction_model.json** para Alexa Dev Console → Build (se não feito)
4. **Configurar variáveis de ambiente no Lambda** (se não feito):
   - `YOUTUBE_API_KEY` (obter no Google Cloud Console)
   - `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_DEST` (Meta Business)
5. **Testar no Simulator**: Menu YouTube → escolher vídeo → pedir resumo
6. **Testar no dispositivo real**: dizer "sete" → YouTube → pesquisar → resumo

## Dependencias Opcionais Faltantes
- `mobi` — para ler arquivos .mobi (Kindle). Instalar: `pip install mobi`
- `pytesseract` — para OCR de imagens. Requer Tesseract instalado no sistema.
