# Checkpoints - Projeto Caxinguele v2

## Status: Fases 1-5 implementadas (19 FEV 2026)

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

### Fase 6: Custom Skill Alexa com "Cambio" - PENDENTE
- [ ] Conta developer.amazon.com
- [ ] AWS Lambda (Python)
- [ ] Intents: AbrirBiblioteca, ListarDocumentos, FiltrarPorTipo, etc.
- [ ] Palavra de confirmacao "cambio"

### Config/Pipeline - CONCLUIDO
- [x] `config.py` atualizado (PERFIS_USUARIOS, MAX_DOC_SIZE_MB, mensagens v2)
- [x] `pipeline_mvp.py` aceita --arquivo (qualquer formato)
- [x] Compatibilidade com --pdf mantida
- [x] Classificacao integrada no pipeline (etapa 2)
- [x] Categoria passada ao upload Drive e RSS
- [x] `requirements.txt` atualizado com novas dependencias

### Fase 6: Custom Skill Alexa + CAMBIO - ESTRUTURA PRONTA
- [x] `alexa_skill/lambda/lambda_function.py` — Lambda Function completa (Python)
- [x] `alexa_skill/interaction_model.json` — Modelo de interacao (intents, slots, utterances)
- [x] `alexa_skill/skill_manifest.json` — Manifesto da skill
- [x] `alexa_skill/ALEXA_SETUP.md` — Guia de instalacao passo-a-passo
- [x] `indice_generator.py` — Gera indice.json para Lambda consumir
- [x] Palavra "cambio" implementada nas utterances de todos os intents
- [ ] **Deploy pendente**: precisa de conta developer.amazon.com + AWS Lambda

### Sistemas Perpetuos
- [x] `health_monitor.py` — "Avise, nao conserta" (14 pacotes + 11 arquivos verificados)
- [x] `teste_multiformat.py` — Script de teste rapido (5 formatos)
- [x] `CHECKPOINTS.md` — Este arquivo

### Botao "Guia p/ Alexa" na GUI
- [x] Botao amarelo que converte GUIA_ALEXA_ACESSIVEL.md direto para MP3 com 1 clique

### Classificador Melhorado
- [x] Normalizacao de acentos na comparacao (sem acento = com acento na busca)
- [x] Livro detectado com 77-80% de confianca mesmo sem acentos

## Proximos Passos
1. Deploy Fase 6: criar conta developer.amazon.com + AWS Lambda
2. Amazon Household: configurar (amazon.com.br/myh/manage)
3. Instalar Tesseract OCR (opcional, para imagens digitalizadas)
4. Testar botao "Guia p/ Alexa" com TTS real
