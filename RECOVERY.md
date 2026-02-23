# 🔧 RECOVERY.md — Instruções de Setup e Deployment

## Stack Requerido

| Componente | Versão | Status |
|-----------|--------|--------|
| Python | 3.9+ | ✓ Instalado |
| Edge-TTS | 6.1.0+ | ✓ Instalado |
| PyMuPDF | 1.23.0+ | ✓ Instalado |
| Google Drive API | 2.0+ | ✓ Instalado |
| Tkinter | Sistema | ✓ Incluído Python |
| AWS Lambda | Python 3.11 | ⏳ Deploy manual |
| Alexa Developer | Console online | ⏳ Config manual |

## Como Instalar Dependências

```bash
# Instalar requirements base
pip install -r requirements.txt

# Opcionais (se usa MOBI ou OCR)
pip install mobi pytesseract
```

## Como Executar

### 1. Interface Desktop

```bash
python audiobook_gui.py
```

Abre a janela principal. Arraste documentos ou clique para selecionar.

### 2. Testes Rápidos

```bash
# Verifica sistema (dependências, caminho, etc.)
python health_monitor.py

# Testa multi-formato (converte 5 arquivos demo)
python teste_multiformat.py

# Testa vozes TTS
python testar_vozes.py
```

### 3. Pipeline Manual (CLI)

```bash
# Converter um arquivo específico
python pipeline_mvp.py --arquivo documento.pdf --nome "Meu Livro"

# Com upload e RSS
python pipeline_mvp.py --arquivo documento.pdf --nome "Meu Livro" --drive --github
```

## Estado Atual

### O Que Funciona

✓ Conversão multi-formato (9+ formatos)
✓ TTS Edge-TTS (4 vozes pt-BR)
✓ Upload Google Drive (categorizado)
✓ RSS/GitHub Pages (publicação)
✓ GUI Desktop (Tkinter)
✓ Menus Alexa (9 menus, 85 utterances)
✓ Lambda reescrita (state machine, voice editing)
✓ Persistência (menus_config.json, dados_*.json)

### O Que Está Parcial

⏳ Alexa Simulator (requer AWS Account)
⏳ Skill renomear "Super Alexa" (requer console AWS)
⏳ Testes visuais GUI (requer display)

### O Que Falta

- [ ] Deploy lambda_function.py no AWS Console
- [ ] Teste com Alexa real (dispositivo ou simulator)
- [ ] Renomear invocation name para "Super Alexa"
- [ ] README.md pronto ✓ (feito)
- [ ] Google Calendar sync (futura fase)

## Passo a Passo: Deploy Lambda

### 1. AWS Console

1. Vá para AWS Lambda Console
2. Criar Nova Function:
   - Runtime: Python 3.11
   - Handler: lambda_function.lambda_handler
3. Copie o conteúdo de `alexa_skill/lambda/lambda_function.py`
4. Cole na janela do Lambda Code Editor
5. Deploy

### 2. Alexa Developer Console

1. Vá para developer.amazon.com
2. Skill: "Meus Audiobooks"
3. Interaction Model:
   - Cole `alexa_skill/interaction_model.json`
4. Endpoint:
   - Cole o ARN da Lambda (obtido em AWS)
5. Save & Test

### 3. Testar

```
Alexa Simulator:
Input: "abre meus audiobooks"
Output: "Você tem 9 opções. 0 para Organizações Mentais..."
```

### 4. Renomear (Futuro)

Quando quiser mudar para "Super Alexa":
1. Interaction Model → invocationName: "super alexa"
2. Save & Test
3. Lambda: sem mudanças necessárias

## Google Drive Setup (se não feito)

```bash
python configurar_token.py
```

Abre browser, autoriza acesso, salva token em `./token.json`.

## Troubleshooting

**Erro: "ModuleNotFoundError: No module named 'edge_tts'"**
→ pip install edge-tts

**Erro: "Google Drive authentication failed"**
→ Rode configurar_token.py e autorize novamente

**GUI não abre**
→ pip install tkinterdnd2 (drag-drop opcional)

**Lambda timeout**
→ Aumentar timeout no AWS Console (default: 30s, tente 60s)

## Próximas Fases

### Fase 2B: Testes & Refinamento
- Testar viualmente GUI (CHECKLIST_TESTES_GUI.md)
- Deploy lambda_function.py
- Teste com Alexa

### Fase 3: Integrações Futuras
- Google Calendar sync
- Amazon Household (compartilhar com amigo)
- Resumos automáticos para reuniões
- Análise de sentimento em favoritos

---

**Última atualização:** 22 FEV 2026
**Versão:** 2.0 (Fases 1-2A)
**Deploy status:** Pronto para AWS
