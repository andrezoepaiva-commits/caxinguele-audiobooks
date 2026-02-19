# 📚 PDF2Audiobook - Sistema Alexa para Pessoas Cegas

Sistema automatizado que converte PDFs em audiobooks de alta qualidade, acessíveis via Alexa Echo Dot com comandos de voz.

## 🎯 Objetivo

Permitir que pessoas cegas possam ouvir **qualquer PDF** pela Alexa, com controle 100% por voz, sem depender de terceiros.

## ✨ Features

- ✅ **Conversão automática**: PDF → Áudio MP3
- ✅ **Voz natural**: Edge-TTS do Azure (gratuito)
- ✅ **OCR automático**: Detecta e processa PDFs escaneados
- ✅ **Controle por voz**: Play, pause, próximo, anterior, velocidade
- ✅ **Memória de posição**: Alexa lembra onde parou
- ✅ **Upload automático**: Google Drive (15GB grátis)
- ✅ **Integração Alexa**: Via skill MyPod
- ✅ **Resiliente**: Retry automático, fallbacks, nunca trava

## 🚀 Instalação

### Pré-requisitos

- Python 3.9+
- Internet (para TTS e upload)

### Passo 1: Instalar dependências

```bash
pip install -r requirements.txt
```

### Passo 2: Instalar Tesseract (para OCR - opcional)

**Windows:**
- Baixe: https://github.com/UB-Mannheim/tesseract/wiki
- Instale com idioma português

**Linux:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

**Mac:**
```bash
brew install tesseract tesseract-lang
```

### Passo 3: Configurar Google Drive (para upload - opcional)

1. Acesse: https://console.cloud.google.com/
2. Crie um novo projeto
3. Ative a API do Google Drive
4. Crie credenciais OAuth 2.0
5. Baixe o arquivo JSON de credenciais
6. Renomeie para `credentials.json` e coloque na pasta do projeto

## 📖 Uso

### Comando Básico

```bash
python pipeline_mvp.py --pdf "Sapiens.pdf"
```

### Opções Avançadas

```bash
# Usar voz específica
python pipeline_mvp.py --pdf "livro.pdf" --voz camila

# Não fazer upload (apenas gerar áudios localmente)
python pipeline_mvp.py --pdf "livro.pdf" --no-upload

# Desabilitar OCR automático
python pipeline_mvp.py --pdf "livro.pdf" --no-ocr

# Especificar pasta de saída
python pipeline_mvp.py --pdf "livro.pdf" --output "meus_audiobooks/"

# Modo verbose (mais logs)
python pipeline_mvp.py --pdf "livro.pdf" --verbose

# Retomar processamento interrompido
python pipeline_mvp.py --pdf "livro.pdf" --resume
```

### Vozes Disponíveis

- `francisca` - Feminina, jovem, natural **(padrão)**
- `camila` - Feminina, madura, profissional
- `antonio` - Masculino, claro
- `thalita` - Feminina, suave

## 🎙️ Configurar Alexa

Após a conversão, um arquivo `README_MyPod.txt` será gerado com instruções detalhadas.

**Resumo:**

1. **Instalar skill MyPod**:
   - App Alexa → Skills → Buscar "My Pod" → Ativar

2. **Acessar MyPod**:
   - https://mypodapp.com
   - Fazer login com conta Amazon

3. **Criar playlist**:
   - Adicionar os links dos capítulos (gerados automaticamente)

4. **Usar com Alexa**:
   ```
   "Alexa, abre My Pod"
   "Alexa, toca [Nome do Livro]"
   "Alexa, pausa"
   "Alexa, próximo"
   "Alexa, voltar 30 segundos"
   ```

## 📂 Estrutura do Projeto

```
pdf2audiobook/
├── pipeline_mvp.py         # Orquestrador principal (execute este)
├── pdf_processor.py        # Processamento de PDFs
├── tts_engine.py          # Conversão texto → áudio
├── cloud_uploader.py      # Upload Google Drive
├── config.py              # Configurações
├── utils.py               # Funções auxiliares
├── requirements.txt       # Dependências
├── audiobooks/            # Audiobooks gerados (criado automaticamente)
├── temp/                  # Arquivos temporários
└── .checkpoints/          # Checkpoints para retomar
```

## ⚙️ Configuração

Edite `config.py` para personalizar:

- Vozes TTS
- Qualidade de áudio (bitrate, sample rate)
- Configurações de OCR
- Número de threads paralelas
- Retry e timeouts
- Google Drive
- E mais...

## 🔧 Troubleshooting

### "Tesseract not found"
- Instale o Tesseract (veja Instalação)
- Ou desabilite OCR: `--no-ocr`

### "Google credentials not found"
- Coloque `credentials.json` na pasta do projeto
- Ou desabilite upload: `--no-upload`

### "Edge-TTS timeout"
- Verifique conexão com internet
- O sistema tentará 3x automaticamente
- Em último caso, usará fallback local (pyttsx3)

### Processamento interrompido
- Use `--resume` para retomar de onde parou
- Checkpoints são salvos automaticamente

## 💡 Dicas

- **PDFs escaneados**: O sistema detecta e aplica OCR automaticamente
- **Capítulos longos**: São divididos automaticamente em partes menores
- **Processamento paralelo**: 3 capítulos são processados simultaneamente
- **Qualidade vs Tamanho**: Edite `AUDIO_CONFIG['bitrate']` em `config.py`
  - 64kbps = boa qualidade, economiza espaço (padrão)
  - 128kbps = alta qualidade, mais espaço

## 📊 Estimativas

- **Tempo de conversão**: ~30-60 minutos para livro de 200 páginas
- **Tamanho final**: ~50-100 MB para livro de 200 páginas (64kbps)
- **Custo**: R$ 0,00 (tudo gratuito!)

## 🎯 Casos de Uso

- ✅ Livros acadêmicos (PDFs de artigos, teses)
- ✅ Documentos técnicos (manuais, guias)
- ✅ Livros digitais (ePub → PDF → Audiobook)
- ✅ Qualquer texto em português ou inglês

## 📝 Licença

Este projeto foi criado para fins de acessibilidade.

## 🤝 Contribuindo

Este é um projeto MVP focado em funcionalidade. Melhorias são bem-vindas!

## 🔗 Links Úteis

- Edge-TTS: https://github.com/rany2/edge-tts
- MyPod (Alexa): https://mypodapp.com
- Google Drive API: https://developers.google.com/drive
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract

---

**Desenvolvido com ❤️ para promover acessibilidade**
