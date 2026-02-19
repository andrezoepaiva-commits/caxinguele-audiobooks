# 🚀 GUIA RÁPIDO - PDF2Audiobook

## Uso Básico (3 passos)

### 1️⃣ Converter um PDF

```bash
python pipeline_mvp.py --pdf "seu_livro.pdf"
```

**O que acontece:**
- ✅ Extrai texto do PDF
- ✅ Detecta capítulos automaticamente
- ✅ Converte para áudio (voz Francisca)
- ✅ Faz upload para Google Drive
- ✅ Gera instruções para MyPod

**Tempo:** ~30-60 min para livro de 200 páginas

---

### 2️⃣ Publicar no GitHub e cadastrar no Amazon Music

Após a conversão e upload no Drive:

```bash
# Publica o XML RSS no GitHub Pages automaticamente
python github_uploader.py
```

Depois acesse **podcasters.amazon.com** (email: andrefmdepaiva@gmail.com) e cadastre o RSS:
```
https://andrezoepaiva-commits.github.io/caxinguele-audiobooks/[nome-do-livro].xml
```

Aguarde até 24h para aparecer no Amazon Music.

---

### 3️⃣ Usar com Alexa (comandos de voz)

```
"Alexa, toca [Nome do Livro] no Amazon Music"
"Alexa, pausa"
"Alexa, próximo episódio"
```

> ⚠️ **Importante:** Usar **Amazon Music**, não Spotify.
> O Spotify não toca podcasts na Alexa.

---

## 🎙️ Trocar Voz

```bash
# Voz feminina jovem (padrão)
python pipeline_mvp.py --pdf "livro.pdf" --voz francisca

# Voz feminina madura
python pipeline_mvp.py --pdf "livro.pdf" --voz camila

# Voz masculina
python pipeline_mvp.py --pdf "livro.pdf" --voz antonio

# Voz feminina suave
python pipeline_mvp.py --pdf "livro.pdf" --voz thalita
```

**Dica:** Teste as vozes com `python testar_vozes.py`

---

## 📁 Não Fazer Upload (apenas gerar áudios localmente)

```bash
python pipeline_mvp.py --pdf "livro.pdf" --no-upload
```

Os arquivos MP3 ficarão em: `audiobooks/[Nome do Livro]/`

---

## 🔄 Retomar Processamento Interrompido

Se o processamento foi interrompido (fechou terminal, deu erro, etc.):

```bash
python pipeline_mvp.py --pdf "livro.pdf" --resume
```

O sistema retoma de onde parou! ✅

---

## 🔍 Modo Verbose (ver mais detalhes)

```bash
python pipeline_mvp.py --pdf "livro.pdf" --verbose
```

Útil para debug ou se algo der errado.

---

## ⚙️ Desabilitar OCR Automático

Se o PDF já tem texto (não é escaneado):

```bash
python pipeline_mvp.py --pdf "livro.pdf" --no-ocr
```

Economiza tempo!

---

## 📂 Especificar Pasta de Saída

```bash
python pipeline_mvp.py --pdf "livro.pdf" --output "meus_audiobooks/"
```

---

## 🧪 Testar o Sistema

### Opção 1: Com PDF de teste

```bash
# Instalar reportlab (se não tiver)
pip install reportlab

# Criar PDF de teste
python exemplo_teste.py

# Testar conversão (sem upload)
python pipeline_mvp.py --pdf exemplo_teste.pdf --no-upload
```

### Opção 2: Com seu próprio PDF

```bash
python pipeline_mvp.py --pdf "seu_pdf.pdf" --no-upload --verbose
```

---

## 📊 Estrutura de Arquivos Gerados

```
audiobooks/
└── Nome_do_Livro/
    ├── Nome_do_Livro - Cap 01 - Titulo.mp3
    ├── Nome_do_Livro - Cap 02 - Titulo.mp3
    ├── ...
    └── README_MyPod.txt (instruções Alexa)
```

---

## ❓ Problemas Comuns

### "PDF not found"
- Verifique o caminho do arquivo
- Use aspas se tiver espaços: `"meu livro.pdf"`

### "Tesseract not found"
- Seu PDF é escaneado e precisa OCR
- **Solução 1:** Instale Tesseract (veja README.md)
- **Solução 2:** Use `--no-ocr` (pode falhar se PDF for imagem)

### "Google credentials not found"
- Você precisa configurar Google Drive
- **Solução 1:** Configure (veja README.md seção Google Drive)
- **Solução 2:** Use `--no-upload` (gera só arquivos locais)

### "Edge-TTS timeout"
- Problema de internet
- O sistema tenta 3x automaticamente
- Em último caso, usa fallback local (qualidade inferior)

### Conversão muito lenta
- Normal! 30-60 min para livro de 200 páginas
- Processamento paralelo (3 capítulos simultâneos)
- Pode deixar rodando e sair

---

## 🎯 Dicas Pro

1. **Teste primeiro sem upload:**
   ```bash
   python pipeline_mvp.py --pdf "livro.pdf" --no-upload
   ```
   Escuta alguns capítulos, se gostar, faz upload depois

2. **Use verbose se der problema:**
   ```bash
   python pipeline_mvp.py --pdf "livro.pdf" --verbose
   ```

3. **PDFs grandes:** Use `--resume` se interromper
   ```bash
   python pipeline_mvp.py --pdf "livro.pdf" --resume
   ```

4. **Organização:** Crie pastas por tema
   ```bash
   python pipeline_mvp.py --pdf "livro.pdf" --output "marketing/"
   python pipeline_mvp.py --pdf "livro2.pdf" --output "tecnico/"
   ```

---

## 💰 Custos

**R$ 0,00 - Tudo gratuito!**

- ✅ Edge-TTS (Azure): Gratuito
- ✅ Google Drive: 15GB grátis
- ✅ Amazon Music Podcasts: Gratuito

---

## 📞 Ajuda

- 📄 Documentação completa: `README.md`
- 🧪 Testar vozes: `python testar_vozes.py`
- 📋 Exemplo teste: `python exemplo_teste.py`

---

**Desenvolvido para promover acessibilidade ❤️**
