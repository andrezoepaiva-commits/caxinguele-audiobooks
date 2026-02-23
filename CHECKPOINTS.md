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

## Proximos Passos
1. Testar GUI visualmente (CHECKLIST_TESTES_GUI.md)
2. Deploy lambda_function.py atualizada no AWS Console
3. Testar Lambda com Alexa real
4. Renomear Skill → "Super Alexa"
5. README.md para o amigo (manual de uso)

## Dependencias Opcionais Faltantes
- `mobi` — para ler arquivos .mobi (Kindle). Instalar: `pip install mobi`
- `pytesseract` — para OCR de imagens. Requer Tesseract instalado no sistema.
