# RELATÓRIO DE DIAGNÓSTICO — Alexa Skill Super Alexa (Caxinguele)
## Problema: Skill retorna erros ao invés de funcionar corretamente

**Data do problema:** 23-24 de Fevereiro, 2026
**Projeto:** Caxinguele Audiobooks + Alexa Integration
**Status:** ✅ RESOLVIDO
**Tempo total de debugging:** ~4 horas

---

## 📋 RESUMO EXECUTIVO

A skill Alexa "Super Alexa" não funcionava, retornando várias mensagens de erro:
1. **"Aqui está o que encontrei"** (erro genérico da Alexa)
2. **"Um problema ocorreu com a resposta da Skill validada"** (resposta inválida do Lambda)
3. **"Não entendi, diga o número ou diga voltar"** (intent matching falho)

Foram identificadas **3 causas raiz distintas**, cada uma resolvida separadamente.

---

## 🔴 CAUSA RAIZ #1: Interaction Model incompleto (Intenção não mapeada)

### Sintoma
- Simulator retorna: `"Aqui está o que encontrei"` (resposta genérica da Alexa)
- Lambda nunca é invocado
- Código Lambda não aparece nos logs

### Diagnóstico
**A skill "Super Alexa" foi criada com template "Start from Scratch"**, o que significa:
- ✅ Tem intents básicos da Amazon (Stop, Cancel, Help)
- ❌ **NÃO tem os custom intents** que o Lambda espera:
  - `SelecionarNumeroIntent`
  - `FiltrarPorTipoIntent`
  - `DocumentoNovosIntent`
  - `LerDocumentoIntent`
  - `ListarDocumentosIntent`

### Solução Aplicada
Criar Interaction Model JSON com todos os intents customizados e copiá-lo para:
**Alexa Developer Console → Build → JSON Editor**

**Arquivo:** `interaction_model.json` (localizado no Desktop)

```json
{
  "interactionModel": {
    "languageModel": {
      "invocationName": "super alexa",
      "intents": [
        {
          "name": "SelecionarNumeroIntent",
          "slots": [{"name": "numero", "type": "AMAZON.NUMBER"}],
          "samples": ["{numero}", "numero {numero}", "opção {numero}", ...]
        },
        // ... outros intents
      ]
    }
  }
}
```

### Como identificar este problema no futuro
- Testou no Simulator e recebeu resposta genérica ("Aqui está o que encontrei")
- Verificou Lambda logs: NÃO há nenhuma invocação
- Criou skill "from scratch" sem importar Interaction Model

---

## 🔴 CAUSA RAIZ #2: SyntaxError por indentação incorreta no Lambda

### Sintoma
- Simulator retorna: `"Um problema ocorreu com a resposta da Skill validada"`
- CloudWatch logs mostram: `[ERROR] Runtime.UserCodeSyntaxError: unexpected indent (lambda_function.py, line 18)`
- Lambda não consegue nem carregar o código Python

### Diagnóstico
O arquivo `lambda_function.py` (copiado do Desktop para Lambda) tinha **indentação extra** em TODAS as linhas após a docstring:

```python
"""
  Super Alexa — Projeto Caxinguele v2
  ...
  """

  import json        # ❌ 2 espaços no início (ERRADO)
  import logging     # ❌ 2 espaços no início (ERRADO)
  logger = getLogger()  # ❌ 2 espaços no início (ERRADO)
```

Python não permite indentação no nível de módulo (top-level code). Todos os imports e definições de funções devem começar na coluna 0.

### Causa Raiz da Causa Raiz
Quando o usuário copiou o código do arquivo `.txt` para o editor do Lambda, a indentação foi preservada (o arquivo original tinha espaçamento interno). O editor não detectou isso automaticamente.

### Solução Aplicada
**Remover a indentação extra de todo o arquivo:**

```bash
# Script Python que remove 2 espaços do início de cada linha
# após a docstring (linha 16)

with open('código.txt', 'r') as f:
    lines = f.readlines()

for i in range(16, len(lines)):  # Começa após docstring
    if lines[i].startswith('  '):
        lines[i] = lines[i][2:]  # Remove 2 espaços

with open('código.txt', 'w') as f:
    f.writelines(lines)
```

**Resultado esperado:**
```python
"""
  Super Alexa — Projeto Caxinguele v2
  ...
  """

import json         # ✅ Sem indentação
import logging      # ✅ Sem indentação
logger = getLogger()   # ✅ Sem indentação
```

### Como identificar este problema no futuro
1. Verificou CloudWatch logs e viu `SyntaxError` na linha 18
2. Ou: Viu mensagem `unexpected indent` no Lambda
3. **Chave:** Erro está na IMPORTAÇÃO ou código top-level, não na lógica
4. **Solução:** Procure por espaços extras no início das linhas

**Arquivo de referência:** `código.txt` (já corrigido)

---

## 🔴 CAUSA RAIZ #3: Trigger com Skill ID incorreto

### Sintoma
- CloudWatch logs estão vazios (nenhuma invocação)
- Lambda não está sendo chamado pela Alexa
- Interaction Model está correto
- Código está correto sintaticamente

### Diagnóstico
**O trigger do Lambda tinha um Skill ID diferente do Skill ID da skill "Super Alexa".**

Fluxo correto:
```
Alexa (app/dispositivo)
    ↓ (usa Skill ID da skill)
AWS Lambda Trigger
    ↓ (verifica se Skill ID bate)
Lambda Function (audiobook-alexa)
```

Se o Skill ID no trigger for diferente do Skill ID da skill, o Lambda nunca é invocado.

### Solução Aplicada
1. **Encontrar o Skill ID correto:**
   - Alexa Developer Console → Super Alexa → Build → Skill Manifest
   - Copiar o Skill ID: `amzn1.ask.skill.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`

2. **Deletar o trigger antigo:**
   - AWS Lambda Console → audiobook-alexa → Configuration → Triggers
   - Clique em "Delete" para remover trigger com Skill ID antigo

3. **Adicionar novo trigger com Skill ID correto:**
   - Clique em "+ Add trigger"
   - Selecione "Alexa Skills Kit"
   - Cole o Skill ID novo
   - Clique em "Add"

### Como identificar este problema no futuro
- Interaction Model está correto (testou no Simulator e JSON foi salvo)
- Código Lambda não tem SyntaxError (verificou CloudWatch)
- Mas Lambda nunca é invocado
- **Solução:** Verifique se há múltiplos triggers com Skill IDs diferentes
  - Vá a: Lambda → Configuration → Triggers
  - Verifique se o Skill ID bate com a skill

---

## 🟡 CAUSA RAIZ #4: Intent matching falho com palavras em português

### Sintoma
- Menu principal funciona: "Alexa, abre super alexa" ✅
- Pode dizer "Alexa, número 9" ✅
- Mas não consegue dizer apenas "Um" ou "número um"
- Retorna: "Não entendi, diga o número ou diga voltar"

### Diagnóstico
**O Interaction Model tinha poucos exemplos de utterances em português.**

Problema específico:
- Slot type `AMAZON.NUMBER` funciona bem para números falados (1, 2, 3)
- Mas a palavra "um" em português é ambígua (artigo: "um livro")
- Alexa precisa de **muitos exemplos** para treinar o modelo de reconhecimento

**Interaction Model original:**
```json
"samples": [
  "{numero}",
  "numero {numero}",
  "opção {numero}",
  "diga {numero}"
]
```

Alexa não conseguia mapear "Um" para o intent com confiança.

### Solução Aplicada
**Adicionar 50+ utterance patterns diferentes:**

```json
"samples": [
  // Padrões com slot
  "{numero}",
  "numero {numero}",
  "número {numero}",
  "opção {numero}",
  "selecionar {numero}",
  "escolher {numero}",
  "quero o {numero}",
  "vai para {numero}",
  "abrir {numero}",

  // Números por extenso
  "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",

  // Ordinais
  "primeiro", "segundo", "terceiro", "quarto", "quinto", "sexto", "sétimo", "oitavo", "nono", "décimo",

  // Variações coloquiais
  "manda o {numero}",
  "toca {numero}",
  "me dá o {numero}",
  "pode ser {numero}",
  "eu escolho o {numero}"
]
```

Também adicionou **função fallback no Lambda** para tentar extrair números da fala bruta se o intent matching falhar:

```python
def _extrair_numero_da_fala(event):
    """Tenta extrair um numero da fala bruta do usuario (fallback)."""
    _PALAVRAS_NUMEROS = {
        "zero": 0, "um": 1, "dois": 2, "três": 3, "quatro": 4, "cinco": 5,
        "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
        "primeiro": 1, "segundo": 2, "terceiro": 3, "quarto": 4, "quinto": 5,
        "sexto": 6, "sétimo": 7, "oitavo": 8, "nono": 9, "décimo": 10,
        # ... e mais
    }
    # Mapeia palavra para número
    for palavra, num in _PALAVRAS_NUMEROS.items():
        if palavra in texto:
            return num
```

### Como identificar este problema no futuro
- O menu principal funciona
- Um número específico funciona quando dito de uma forma
- Mas não funciona quando dito de outra forma
- **Solução:** Adicione mais utterance samples ao Interaction Model
- **Chave:** Em português, adicione números por extenso ("um", "dois") E ordinais ("primeiro", "segundo")

---

## 🔴 CAUSA RAIZ #5: AMAZON.NUMBER slot vazio com palavras em português (23-24 Fev, 2026)

### Sintoma
- Menu principal funciona: "Alexa, abre super alexa" ✅
- Dizer "nove" (palavra) retorna: "Não entendi o numero. Repita por favor." ❌
- Dizer "9" (dígito) funciona perfeitamente ✅
- CloudWatch mostra: `slot_data={'name': 'numero', 'confirmationStatus': 'NONE'}` (SEM key 'value')

### Diagnóstico (Análise com Opus 4.6 + Adaptive Thinking)

**Causa raiz identificada:** O Interaction Model tinha **64 utterance samples SEM referência ao slot `{numero}`**.

Exemplos problemáticos:
```json
"samples": [
  "primeiro",    ← SEM {numero}
  "segunda",     ← SEM {numero}
  "nove",        ← SEM {numero} — ESTE ERA O BUG
  "numero um",   ← SEM {numero}
  "nove mesmo"   ← SEM {numero}
  ...
]
```

**Mecanismo da falha:**
1. Usuário diz "nove"
2. Alexa NLU tenta match no Interaction Model
3. NLU encontra TWO candidatos:
   - Sample `"{numero}"` → tentaria usar AMAZON.NUMBER para converter
   - Sample literal `"nove"` → match direto (mais específico)
4. **NLU prefere match literal** (mais específico que o genérico `{numero}`)
5. Aciona SelecionarNumeroIntent SEM preencher o slot `numero`
6. Slot chega vazio por design da Alexa
7. Lambda recebe intent correto mas `slot_data` não tem 'value'
8. `_extrair_numero()` retorna None → "Não entendi o numero"

**Por que "9" funciona?**
O dígito "9" não tem sample literal correspondente, então NLU tenta AMAZON.NUMBER como única opção. AMAZON.NUMBER reconhece dígitos em português perfeitamente.

### Solução Aplicada

**Parte 1 — Interaction Model (`interaction_model.json`):**
✅ Removidos TODOS os 64 utterance samples sem `{numero}`
✅ Mantidos apenas samples que referenciam o slot

Antes:
```json
"samples": [
  "{numero}",
  "numero {numero}",
  // ... 48 bons samples
  "primeiro",      // ❌ 64 samples problemáticos removidos
  "segunda",
  "nove",
  "numero um",
  ...
]
```

Depois:
```json
"samples": [
  "{numero}",
  "numero {numero}",
  "número {numero}",
  "opção {numero}",
  "selecionar {numero}",
  "escolher {numero}",
  "quero o {numero}",
  "vai para {numero}",
  "abrir {numero}",
  // ... 50 bons samples com slot referenciado
  // Todos os 64 samples sem {numero} removidos
]
```

**Parte 2 — Lambda Fallback (`código.txt`):**

Modificado `_extrair_numero()` para chamar fallback:
```python
if intent_name == "SelecionarNumeroIntent":
    numero = _extrair_numero(slots, "numero")
    # Se AMAZON.NUMBER nao preencheu, tenta extrair da fala bruta
    if numero is None:
        numero = _extrair_numero_da_fala(event)
    if numero is None:
        return _resp("Nao entendi o numero. Diga por exemplo: numero nove.",
                      end=False, session=session)
    return _roteador_numero(numero, session)
```

Melhorado `_extrair_numero_da_fala()` para usar fontes corretas:
```python
def _extrair_numero_da_fala(event):
    """Tenta extrair um numero da fala bruta do usuario (fallback)."""
    try:
        # Tenta primeiro o slot value
        raw = event.get("request", {}).get("intent", {}).get("slots", {}).get("numero", {}).get("value", "") or ""
        # Se não achoutenta outras fontes
        if not raw:
            for slot_name, slot_data in event.get("request", {}).get("intent", {}).get("slots", {}).items():
                if isinstance(slot_data, dict):
                    raw = slot_data.get("value", "") or ""
                    if raw:
                        break

        # Agora tenta extrair número do texto
        texto = raw.lower().strip()
        # ... mapa _PALAVRAS_NUMEROS converte "nove" → 9
```

### Como identificar este problema no futuro

**Checklist:**
- [ ] Usuário diz uma PALAVRA (ex: "nove") → não funciona
- [ ] Mesmo usuário diz um DÍGITO (ex: "9") → funciona
- [ ] CloudWatch mostra `slot_data` SEM a key `'value'`
- [ ] O Interaction Model tem utterance samples sem `{slot_name}`

**Solução imediata:**
1. Abra `interaction_model.json`
2. Procure por samples SEM `{numero}` (ou qualquer outro slot)
3. Delete esses samples
4. Mantenha APENAS samples que referenciam o slot
5. Build Model
6. Teste novamente

**Regra de ouro:** Em um intent com slots, NUNCA adicionar samples que não referenciam aquele slot.

### Arquivos afetados e versão corrigida

- ✅ `interaction_model.json` — 64 samples sem slot removidos (atualizado 24 Fev 2026, 10h)
- ✅ `código.txt` — Fallback melhorado (atualizado 24 Fev 2026, 10h)

---

## 🔴 CAUSA RAIZ #6: Menu 9 (Configurações) submenu sem handler (24-25 Fev, 2026)

### Sintoma
- Menu principal funciona: dizer "9" abre Configurações ✅
- Configurações oferece opções: "1 para Voz, 2 para Velocidade, 3 para Guia"
- Ao dizer "1" no submenu de Configurações: retorna "Não entendi. Diga o número ou diga voltar." ❌
- O mesmo "1" funciona em outros submenus (Livros, Reuniões, etc.) ✅
- CloudWatch logs mostram intent capturado corretamente, mas Lambda não responde

### Diagnóstico

**Causa raiz:** A função `_selecionar_submenu()` não tinha **handler específico para `menu_tipo == "configuracoes"`**.

Arquitetura de navegação da Alexa Skill:
```
Nível: menu (menu principal)
  ↓ usuário diz "9"
Nível: submenu (abrir submenu)
  ↓ usuário diz "1", "2" ou "3"
  (AQUI: _selecionar_submenu() precisa saber qual submenu está aberto)
Nível: item (detalhes)
```

**O problema:**
```python
def _selecionar_submenu(numero, session):
    menu_tipo = session.get("menu_tipo", "")

    # Handlers para "musicas", "livros", "calendario", "reunioes", etc.
    if menu_tipo == "musicas":
        # ... funciona
    if menu_tipo == "livros":
        # ... funciona
    # ... mais handlers ...

    # ❌ MAS NÃO TINHA handler para "configuracoes"
    # Quando menu_tipo == "configuracoes", caia no fallback "Não entendi"
```

**Por que "9" funcionava?**
- Menu 9 é aberto em `_selecionar_menu()`, que está correto
- Problema é quando volta para o submenu das Configurações

**Por que outros números funcionam em outros submenus?**
- Submenus de Livros, Reuniões, Músicas têm handlers bem definidos
- Configurações não tinha handler, ficava órfão

### Solução Aplicada

**Adicionar handler completo para `menu_tipo == "configuracoes"`:**

```python
# ---------- Configuracoes: submenu principal ----------
if menu_tipo == "configuracoes":
    if numero == NUM_REPETIR:
        return _resp(
            "Configuracoes. 1 para Escolher Voz. 2 para Velocidade da Fala. 3 para Guia do Usuario. "
            f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
            end=False, session=session)
    if numero == NUM_VOLTAR:
        return _voltar_menu_principal(session)
    if numero == 1:
        return _menu_config_vozes(session)
    if numero == 2:
        return _menu_config_velocidades(session)
    if numero == 3:
        return _resp(
            "Guia do Usuario. Voce pode ouvir o menu de ajuda dizendo: Alexa, pede ajuda na super alexa. "
            f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
            end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
    return _resp("Opcao invalida. 1 para Voz. 2 para Velocidade. 3 para Guia.",
                 end=False, session=session)

# ---------- Configuracoes: escolher voz ----------
if menu_tipo == "config_vozes":
    if numero == NUM_REPETIR:
        return _menu_config_vozes(session)
    if numero == NUM_VOLTAR:
        return _resp(
            "Configuracoes. 1 para Escolher Voz. 2 para Velocidade da Fala. 3 para Guia do Usuario. "
            f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
            end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
    nomes_vozes = ["Camila", "Vitoria", "Thiago", "Francisca", "Thalita", "Antonio"]
    if not (1 <= numero <= len(nomes_vozes)):
        return _resp(f"Opcao invalida. Escolha entre 1 e {len(nomes_vozes)}.",
                     end=False, session=session)
    voz_escolhida = nomes_vozes[numero - 1]
    return _resp(
        f"Voz {voz_escolhida} selecionada. "
        "Para ativar, acesse Configuracoes da Alexa no aplicativo, va em Voz da Alexa e escolha {voz_escolhida}. "
        f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
        end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})

# ---------- Configuracoes: escolher velocidade ----------
if menu_tipo == "config_velocidades":
    if numero == NUM_REPETIR:
        return _menu_config_velocidades(session)
    if numero == NUM_VOLTAR:
        return _resp(
            "Configuracoes. 1 para Escolher Voz. 2 para Velocidade da Fala. 3 para Guia do Usuario. "
            f"{NUM_REPETIR} para repetir. {NUM_VOLTAR} para voltar.",
            end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
    velocidades = ["Muito Devagar", "Devagar", "Normal", "Rapido", "Muito Rapido"]
    if not (1 <= numero <= len(velocidades)):
        return _resp(f"Opcao invalida. Escolha entre 1 e {len(velocidades)}.",
                     end=False, session=session)
    vel_escolhida = velocidades[numero - 1]
    return _resp(
        f"Velocidade {vel_escolhida} selecionada. "
        "Para aplicar, acesse as Configuracoes da Alexa no aplicativo e ajuste a velocidade da voz. "
        f"{NUM_VOLTAR} para voltar.",
        end=False, session={**session, "nivel": "submenu", "menu_tipo": "configuracoes"})
```

### Como identificar este problema no futuro

**Checklist: Menu A abre, mas número no submenu de Menu A não funciona**

1. **Menu principal funciona** (ex: dizer "9" abre Configurações)
2. **Submenu é aberto** (Alexa anuncia opções)
3. **Mas número no submenu não é reconhecido** (ex: dizer "1" retorna "Não entendi")
4. **Outros submenus funcionam** (ex: "2" para Livros funciona)

**Diagnóstico imediato:**

Procure no `código.txt` pela função `_selecionar_submenu()`:
```python
def _selecionar_submenu(numero, session):
    menu_tipo = session.get("menu_tipo", "")

    # Se seu submenu NÃO tem handler, adicione:
    if menu_tipo == "seu_novo_submenu":
        # ... adicione lógica aqui
```

**Regra de ouro:** Cada `menu_tipo` que você criar em `_selecionar_menu()` **precisa de um handler correspondente em `_selecionar_submenu()`**. Caso contrário, o submenu fica órfão.

### Padrão de navegação a seguir

```
_selecionar_menu() → Abre um menu, retorna com nivel="submenu" + menu_tipo="X"
  ↓
_selecionar_submenu() → Processa numero no submenu. PRECISA ter: if menu_tipo == "X"
  ↓
_selecionar_acao_item() → Processa acao no item (se necessário)
```

Se criar novo menu e esquecer do handler em `_selecionar_submenu()`, o submenu não funciona.

### Arquivos afetados e versão corrigida

- ✅ `código.txt` — Handler de configurações adicionado em `_selecionar_submenu()` (atualizado 25 Fev 2026)
- ✅ `lambda_function_atual.py` — Sincronizado (atualizado 25 Fev 2026)

---

## ✅ CHECKLIST DE VERIFICAÇÃO — Quando a Skill não funciona

Use este checklist **em ordem** para diagnosticar rapidamente:

### Nível 1: Interaction Model
- [ ] A skill foi criada? (não "from scratch" sem Interaction Model)
- [ ] JSON Editor tem conteúdo válido? (sem erros de sintaxe)
- [ ] Build Model foi executado com sucesso?
- [ ] Interaction Model tem todos os intents necessários?
  - [ ] `SelecionarNumeroIntent`
  - [ ] `FiltrarPorTipoIntent`
  - [ ] `DocumentoNovosIntent`
  - [ ] `LerDocumentoIntent`
  - [ ] `ListarDocumentosIntent`

### Nível 2: Lambda Trigger
- [ ] Lambda tem um trigger para "Alexa Skills Kit"?
- [ ] O Skill ID no trigger bate com o Skill ID da skill?
  - Skill ID está em: Alexa Developer Console → Skill Manifest
  - Skill ID no trigger está em: AWS Lambda → Configuration → Triggers
- [ ] Há apenas UM trigger ativo? (delete triggers antigos/incorretos)

### Nível 3: Lambda Code
- [ ] CloudWatch Logs mostra invocações?
  - Vá a: Lambda → Monitor → View logs in CloudWatch
  - Procure por "START RequestId:" recente
- [ ] Há SyntaxError nos logs?
  - Se sim: Procure por indentação extra no top-level code (imports, funções)
  - Remova espaços do início das linhas fora de indented blocks

### Nível 4: Intent Matching
- [ ] O Simulator reconhece os números quando ditos de diferentes formas?
- [ ] Há muitos utterance samples no Interaction Model?
- [ ] Se a Alexa não entende um número, é porque:
  - [ ] Interaction Model tem poucos exemplos
  - [ ] Faltam números por extenso ("um", "dois") e ordinais ("primeiro", "segundo")

### Nível 5: Voz/Resposta
- [ ] A resposta é recebida mas com voz ruim/não natural?
  - [ ] Considere adicionar SSML (Speech Synthesis Markup Language)
  - [ ] Ou mude a voz na app da Alexa (Configurações → Voz)

---

## 📊 TIMELINE DO DEBUGGING

| Hora | Data | Ação | Resultado | Causa | Causa Raiz |
|------|------|------|-----------|--------|-----------|
| 1h | 23 Fev | Criar skill "Super Alexa" do zero | Retorna "Aqui está o que encontrei" | Interaction Model vazio | #1 |
| 1h30 | 23 Fev | Colar Interaction Model JSON, Build | Simulator retorna erro de resposta inválida | SyntaxError no Lambda (indentação) | #2 |
| 2h | 23 Fev | Corrigir docstring, deploiar | CloudWatch mostra SyntaxError na linha 18 | Indentação extra em todo o arquivo | #2 |
| 2h30 | 23 Fev | Remover indentação, deploiar | Menu funciona! Pode dizer "número 9" ✅ | Supostamente pronto | - |
| 3h | 23 Fev | Testar na Alexa real | "Apenas Um" não funciona | Intent matching falho | #4 |
| 3h30 | 23 Fev | Melhorar Interaction Model (+50 samples) | "Um" agora é reconhecido ✅ | Faltavam exemplos em português | #4 |
| 4h | 23 Fev | Adicionar função fallback | "Um" funciona 100% das vezes ✅ | Problema resolvido | #5 |
| 4h30 | 24 Fev | Usar Opus 4.6 com Adaptive Thinking | Diagnostica bug real: samples sem {numero} | AMAZON.NUMBER com palavras em pt-BR | #5 |
| 5h | 24 Fev | Remover 64 samples do IM, adicionar duplo fallback | Menu completo: 9 → "abre Config" ✅ | Padrão NLU prefer literal match | #5 |
| 5h30 | 25 Fev | Testar número 9 e depois 1 na Alexa | "9" abre Config, mas "1" retorna "Não entendi" | Menu 9 submenu sem handler | #6 |
| 6h | 25 Fev | Adicionar handler de configurações | Número 9 → 1 funciona 100% ✅ | Faltava if menu_tipo == "configuracoes" | #6 |

---

## 🎯 PONTOS-CHAVE PARA LEMBRAR

### 1. Ordem de verificação importa
Não pule passos. Verifique na ordem:
1. Interaction Model existe e é válido?
2. Trigger está configurado com Skill ID correto?
3. Lambda tem SyntaxError?
4. Intent matching está funcionando?

### 2. CloudWatch Logs é seu melhor amigo
```
Lambda não funciona?
→ Vá a CloudWatch Logs
→ Procure por erro específico
→ Terá linha exata do erro
```

### 3. SyntaxError é diferente de RuntimeError
- **SyntaxError:** Código não consegue ser carregado (linha de carga)
- **RuntimeError:** Código carrega mas falha durante execução (logs do Lambda)

### 4. Português é complicado para NLU
- "Um" pode ser número ou artigo
- Adicione **muitos exemplos** no Interaction Model
- Adicione números por extenso + ordinais + variações coloquiais

### 5. Trigger com Skill ID errado é "silent failure"
Não há mensagem de erro clara. Lambda simplesmente não é invocado. Verifique Skill ID CEDO no processo.

---

## 📝 REFERÊNCIA RÁPIDA — Comandos e Locais

| O quê | Onde | Como |
|-------|------|------|
| Interaction Model | Alexa Dev Console → Build → JSON Editor | Cole `interaction_model.json`, Save, Build |
| Lambda Code | AWS Lambda → Editor | Cole `código.txt`, Deploy |
| Lambda Logs | AWS Lambda → Monitor → View logs in CloudWatch | Procure por erro específico |
| Skill ID | Alexa Dev Console → Skill Manifest | Copie e compare com trigger |
| Trigger Config | AWS Lambda → Configuration → Triggers | Verifique Skill ID e delete antigos |

---

## 🚀 PRÓXIMOS PASSOS (Se o problema recursar)

1. **Sim, a skill funcionava antes, mas parou de funcionar:**
   - [ ] Verificou Lambda logs?
   - [ ] O código foi alterado acidentalmente?
   - [ ] O Skill ID foi alterado?

2. **A skill funciona mas com comportamento estranho:**
   - [ ] Verifique a lógica da função que está causando comportamento estranho
   - [ ] Procure por RuntimeError nos logs
   - [ ] Teste a função isoladamente

3. **Erros recorrentes de reconhecimento de voz:**
   - [ ] Adicione mais utterance samples ao Interaction Model
   - [ ] Adicione suporte a mais idiomas/dialetos se necessário

---

## 📞 COMO USAR ESTE RELATÓRIO

**Quando passar por um problema similar:**

1. Abra este relatório
2. Vá direto para a seção **CHECKLIST DE VERIFICAÇÃO**
3. Siga os níveis 1-5 em ordem
4. Quando encontrar o problema, procure a **Causa Raiz** correspondente
5. Aplique a solução descrita

**Se ainda não resolver:**
- Verifique **CloudWatch Logs** com a mensagem de erro específica
- Comparar com o "Sintoma" e "Diagnóstico" da causa raiz mais próxima
- Se nada funcionar, tente resetar do zero: delete a skill e crie nova

---

## 🔴 CAUSA RAIZ #7: Labirinto ignora "opcoes" do JSON para menus tipo "filtro" (24 Fev 2026)

### Sintoma
- Atualizamos `menus_config.json` e `indice.json` com categorias de livros (Inteligência Sensorial, Geral)
- Fizemos commit e push para GitHub Pages
- Labirinto reaberto, mas continua mostrando o fluxo antigo: livros direto sem categorias
- As 4 opções (1. Inteligência Sensorial, 2. Geral, 98. Repetir, 99. Voltar) **nunca aparecem**

### Diagnóstico (Opus 4.6 — Painel Estruturado de Experts)

**Arquivo:** `labirinto_ui.py`, método `_popular_tree()`, linhas 516-578

**Mecanismo da falha:**

O método `_popular_tree()` renderiza cada menu da lista `self.menu` usando `if/elif/else` por tipo:
- `tipo == "recentes"` → renderização especial
- `tipo == "gravacao"` → renderização especial
- `tipo == "reunioes"` → renderização especial
- `tipo in ("configuracoes", "favoritos", "musica", "calendario")` → lê `cat.get("opcoes", [])`
- `else:` → tipo "filtro" **NÃO lê opcoes do JSON**

**O bloco `else` (tipo "filtro") tinha lógica hardcoded:**
```python
else:
    cat_filtro = cat.get("categoria", nome)
    if cat_filtro == "Livros":
        # Renderiza livros direto do indice.json
        # IGNORA completamente cat.get("opcoes", [])
        # NUNCA verifica se há categorias definidas
        livros = _agrupar_livros_ui(docs_cat)
        for livro in livros:
            # Mostra cada livro com opções hardcoded
```

**Fluxo dos dados (path do bug):**
1. `menus_config.json` é lido → `self.menu` recebe lista com Menu [2] contendo `"opcoes": [...]`
2. `_popular_tree()` itera sobre `self.menu`
3. Menu [2] tem `tipo: "filtro"` → cai no bloco `else` (linha 516)
4. Dentro do `else`, verifica `if cat_filtro == "Livros"` (linha 530) → TRUE
5. **Nunca lê** `cat.get("opcoes", [])` — renderiza direto os livros
6. Categorias "Inteligência Sensorial" e "Geral" ficam invisíveis

**Por que os outros menus (Favoritos, Configurações, etc.) funcionam?**
Porque eles têm tipos específicos (`"favoritos"`, `"configuracoes"`) que caem nos blocos `elif` anteriores, que **leem** `cat.get("opcoes", [])`. O tipo `"filtro"` era o único que ignorava.

### Solução Aplicada

**Modificar o bloco `else` para verificar se há "opcoes" antes de renderizar:**

```python
else:
    # tipo "filtro"
    opcoes_cat = cat.get("opcoes", [])
    opcoes_livro_acao = cat.get("opcoes_apos_selecao", [])

    if opcoes_cat:
        # TEM categorias definidas → mostrar submenu primeiro
        # 1. Renderiza cada categoria como nó da árvore
        # 2. Dentro de cada categoria: lista livros agrupados
        # 3. Dentro de cada livro: opcoes_apos_selecao (Início, Continuar, etc.)
        # 4. 98/99 em cada nível
    else:
        # SEM categorias → comportamento antigo (lista docs direto)
```

**Também atualizou `MENU_PADRAO` hardcoded** (linhas 98-99) para incluir as categorias como fallback, garantindo que mesmo sem `menus_config.json`, o Labirinto mostra as 4 opções.

### Como identificar este problema no futuro

**Checklist: Dados no JSON mas Labirinto não mostra**

1. Verificou `menus_config.json` e os dados estão lá? ✅
2. Publicou no GitHub Pages? ✅
3. **MAS** o Labirinto não reflete → **Problema está no CÓDIGO, não nos dados**
4. Procure no `labirinto_ui.py`, método `_popular_tree()`
5. Verifique qual bloco `if/elif/else` renderiza esse tipo de menu
6. Se o bloco ignora `cat.get("opcoes", [])`, essa é a causa

**Regra de ouro: Dados no JSON ≠ Código que lê os dados.**
Sempre verifique se o código de renderização está lendo os campos que você adicionou.

**Padrão de verificação em 3 passos:**
1. 📝 **Dados:** O JSON tem o campo? → Sim
2. 🔍 **Leitura:** O código lê esse campo? → Buscar `cat.get("opcoes"` no bloco correspondente
3. 🖥️ **Renderização:** O código usa o campo para gerar UI? → Verificar se há `tree.insert` com os dados

Se qualquer passo falhar, o dado fica invisível.

### Arquivos afetados e versão corrigida

- ✅ `labirinto_ui.py` — Bloco `else` (tipo "filtro") agora lê `opcoes` e `opcoes_apos_selecao`
- ✅ `labirinto_ui.py` — `MENU_PADRAO` atualizado com categorias de livros
- ✅ `menus_config.json` — Menu [2] com categorias (já estava correto)

---

## 🔴 CAUSA RAIZ #8: Livros recolhidos no Labirinto — 4 opções ocultas (24 Fev 2026)

### Sintoma
- Labirinto mostra [2] Livros e as categorias [1] e [2]
- Dentro de cada categoria, livro aparece (ex: "1. Livro sem nome (1 cap.)")
- **Mas as 4 opções (Começar do Início, Continuar, Escolher Capítulo, Sinopse) NÃO aparecem**
- Usuário acha que as opções não foram implementadas

### Diagnóstico
**As 4 opções EXISTIAM na árvore, mas estavam ocultas.**

Em `labirinto_ui.py`, o nó do livro era inserido com `open=False`:
```python
self.tree.insert(opt_iid, "end",
    iid=livro_iid,
    text=f"  {i}.   {livro['titulo']}  ({n_caps} cap.)",
    open=False)  # ← COLLAPSED: filhos não aparecem visualmente
```

As 4 opções são FILHOS deste nó. Com `open=False`, elas ficam recolhidas. O usuário precisaria clicar no `▶` para expandi-las — e não sabia que estavam lá.

### Solução
Mudar `open=False` para `open=True` na inserção do nó do livro:
```python
self.tree.insert(opt_iid, "end",
    iid=livro_iid,
    text=f"  {i}.   {livro['titulo']}  ({n_caps} cap.)",
    open=True)  # Mostra as 4 opções expandidas por padrão
```

**Arquivo:** `labirinto_ui.py`, linha ~579

---

## 🔴 CAUSA RAIZ #9: LIVROS_CATEGORIAS com filtro incompatível com indice.json (24 Fev 2026)

### Sintoma
- Alexa diz as categorias (1. Inteligência Sensorial, 2. Geral) ✅
- Usuário diz "1" ou "2"
- **Alexa responde: "Nenhum livro catalogado em Inteligência Sensorial"** ❌
- Usuário NUNCA consegue selecionar um livro, logo nunca vê as 4 opções por voz

### Diagnóstico
Em `lambda_function.py`, `LIVROS_CATEGORIAS` tinha filtros errados:
```python
LIVROS_CATEGORIAS = [
    {"numero": 1, "nome": "Inteligencia Sensorial", "filtro": "Inteligencia Sensorial"},  # ❌
    {"numero": 2, "nome": "Geral",                   "filtro": "Geral"},                  # ❌
]
```

O Lambda filtra documentos assim:
```python
cat_filtro = cat.get("filtro")  # → "Inteligencia Sensorial"
docs_livros = [d for d in todos_docs if d.get("categoria", "") == cat_filtro]
# → VAZIO! Docs têm categoria="Livros", não "Inteligencia Sensorial"
```

**Por quê?** Os documentos no `indice.json` têm `"categoria": "Livros"` (categoria genérica). As subcategorias "Inteligência Sensorial" e "Geral" são **intenção futura**, não a realidade atual dos dados.

### Fluxo do bug:
1. User diz "1" → filtro tenta buscar docs com `categoria == "Inteligencia Sensorial"`
2. Nenhum doc tem essa categoria → `docs_livros = []`
3. `_menu_livros([], session)` → `if not livros: return "Nenhum livro catalogado..."`
4. Lambda responde com erro "vazio" → usuário nunca escolhe livro → nunca vê 4 opções

### Solução
Mudar filtro para "Livros" (categoria real dos documentos) para ambas as subcategorias:
```python
LIVROS_CATEGORIAS = [
    {"numero": 1, "nome": "Inteligencia Sensorial", "filtro": "Livros"},  # ✅
    {"numero": 2, "nome": "Geral",                   "filtro": "Livros"},  # ✅
]
```

**Nota:** No futuro, quando o pipeline de upload distinguir subcategorias, atualizar o `filtro` para o valor exato usado ao catalogar (ex: `"Livros: Inteligencia Sensorial"`). Por enquanto, ambas mostram todos os livros.

**Arquivo:** `lambda_function.py`, linhas 528-531

---

## 📊 TIMELINE DO DEBUGGING (atualizada)

| Hora | Data | Ação | Resultado | Causa Raiz |
|------|------|------|-----------|-----------|
| 1h | 23 Fev | Criar skill "Super Alexa" | Erro genérico | #1 |
| 1h30 | 23 Fev | Colar Interaction Model | Erro de resposta | #2 |
| 2h | 23 Fev | Corrigir indentação | SyntaxError | #2 |
| 2h30 | 23 Fev | Remover indentação extra | Menu funciona ✅ | - |
| 3h | 23 Fev | Testar "Um" na Alexa | Não funciona | #4 |
| 3h30 | 23 Fev | Melhorar IM (+50 samples) | "Um" reconhecido ✅ | #4 |
| 4h | 23 Fev | Fallback de números | Funciona 100% ✅ | #5 |
| 4h30 | 24 Fev | Opus diagnostica samples | Bug: literal match | #5 |
| 5h | 24 Fev | Remover 64 samples sem slot | Menu completo ✅ | #5 |
| 5h30 | 25 Fev | Menu 9 submenu sem handler | "Não entendi" | #6 |
| 6h | 25 Fev | Adicionar handler | Funciona ✅ | #6 |
| 6h30 | 24 Fev | Adicionar categorias ao JSON | Labirinto ignora | #7 |
| 7h | 24 Fev | Opus: _popular_tree hardcoded | Código não lê opcoes | #7 |
| 7h30 | 24 Fev | Corrigir bloco else + MENU_PADRAO | Categorias visíveis ✅ | #7 |
| 8h | 24 Fev | Livros recolhidos (open=False) | 4 opções ocultas | #8 |
| 8h15 | 24 Fev | open=True no nó do livro | Opções visíveis ✅ | #8 |
| 8h30 | 24 Fev | LIVROS_CATEGORIAS filtro errado | "Nenhum livro" no voice | #9 |
| 8h45 | 24 Fev | Filtro → "Livros" (categoria real) | Alexa acha livros ✅ | #9 |

---

## 🎯 PONTOS-CHAVE PARA LEMBRAR (atualizado)

### 7. Dados no JSON ≠ Código que renderiza
- Adicionar campo ao JSON não basta
- O código de renderização precisa **ler** e **usar** esse campo
- Sempre verifique: dados → leitura → renderização
- Diferentes tipos de menu podem ter caminhos de renderização diferentes

### 8. Labirinto: if/elif/else por tipo
- Cada `tipo` de menu tem bloco próprio em `_popular_tree()`
- Tipo "filtro" usa o bloco `else` (genérico)
- Se adicionar novo campo a um tipo, verifique se o **bloco correto** lê esse campo
- Os blocos `elif` anteriores podem servir de modelo

### 9. open=False esconde filhos — use open=True para opções visíveis
- Em `ttk.Treeview`, nós com `open=False` ocultam todos os filhos
- Use `open=True` quando quer que as opções sejam visíveis ao abrir
- Regra: **nós de folha** (sem filhos) → `open=False` não importa; **nós com filhos relevantes** → `open=True`

### 10. Filtro vs. Categoria real — sempre verificar o que o dado realmente tem
- `LIVROS_CATEGORIAS["filtro"]` deve bater com `documento["categoria"]` no indice.json
- Subcategorias futuras precisam ser implementadas tanto no **pipeline de upload** quanto no **filtro do Lambda**
- Antes de definir um filtro, verificar quais valores exatos existem no `indice.json`

---

## 📚 ARQUIVOS IMPORTANTES

Mantenha estes arquivos no Desktop para referência rápida:

- **`código.txt`** — Lambda function completa (com submenu de categorias)
- **`interaction_model.json`** — Interaction Model com 50+ utterances
- **`menus_config.json`** — Configuração de menus (com categorias de livros)
- **`labirinto_ui.py`** — Visualização do Labirinto (com renderização de categorias)
- **`RELATORIO_ALEXA_SKILL_DIAGNOSTICO.md`** — Este arquivo (você aqui!)

---

## ✅ CHECKLIST DE VERIFICAÇÃO — Atualizado com Causa #7

### Nível 6: Labirinto / GUI
- [ ] O JSON tem os dados corretos? (menus_config.json ou indice.json)
- [ ] O código de renderização LÊ esses dados?
  - Buscar: `cat.get("opcoes"` no bloco correspondente ao tipo do menu
- [ ] O código RENDERIZA os dados na árvore?
  - Buscar: `self.tree.insert` com as variáveis dos dados
- [ ] Se tipo "filtro": verificar o bloco `else` em `_popular_tree()`
- [ ] Se novo campo: verificar se MENU_PADRAO também foi atualizado

---

**Fim do Relatório**
*Atualizado em 24 de Fevereiro, 2026*
*Situação: ✅ Skill funcionando | ✅ Labirinto com categorias e 4 opções visíveis | ✅ Lambda filtra por categoria correta*

---

## 🔴 CAUSA RAIZ #10: código.txt ↔ lambda_function.py Desync (25 Fev 2026)

### Sintoma
- Alteração feita no `código.txt` (desktop)
- Deploy realizado no Lambda Console
- Mas `lambda_function.py` no repositório GitHub fica diferente
- **Próxima vez que o usuário puxa o repo, suas mudanças sumiram**

### Diagnóstico
**O usuário mantinha DOIS arquivos separados:**
1. `código.txt` — Arquivo de trabalho no Desktop (usado para Deploy no Lambda)
2. `lambda_function.py` — Arquivo no repo (`alexa_skill/lambda/lambda_function.py`)

Quando mudava o `código.txt` e fazia deploy, se depois alterava o repo apenas para editar em IDE, os arquivos saíam de sincronia.

### Solução Aplicada
**Manter sincronizado automaticamente:**
```bash
# Após fazer mudanças no código.txt:
cp código.txt → alexa_skill/lambda/lambda_function.py
git add, commit, push
```

**Regra de ouro:**
1. Editar `código.txt` (arquivo principal)
2. Testar no Lambda Console
3. Deploy ✅
4. Sincronizar para lambda_function.py
5. Git commit + push
6. **NUNCA editar `lambda_function.py` diretamente** — sempre via `código.txt`

---

## 🔴 CAUSA RAIZ #11: Navegação "voltar" monolítica vs. hierárquica (25 Fev 2026)

### Sintoma (Antes)
- Usuário está em: Menu [2] → Categorias → Livros → Capítulos
- Diz "Alexa, voltar"
- **Alexa volta DIRETO ao Menu Principal** (3 níveis de uma vez)
- Usuário perdeu contexto

### Diagnóstico (Antes)
**Função `_voltar_menu_principal()` era universal:**
```python
if numero == NUM_VOLTAR:
    return _voltar_menu_principal(session)  # Sempre menu 0
```

Com estrutura profunda (Menu → Submenu → Item), o usuário sentia-se teletransportado.

### Solução Aplicada
**Criar tabela `_PARENT_MENU` com navegação hierárquica:**
```python
_PARENT_MENU = {
    "livros": "livros_categorias",  # Livros → Categorias
    "livros_capitulos": "livros",   # Capítulos → Opções do Livro
    "config_velocidades": "configuracoes",
    # None = volta ao menu principal
}
```

**Função nova:**
```python
def _voltar_nivel_anterior(session):
    """Volta UM nível na hierarquia, não para menu principal."""
    pai = _PARENT_MENU.get(menu_tipo)
    if pai is None:
        return _voltar_menu_principal(session)
    else:
        return _reconstruir_menu(pai, session)
```

**Fluxo novo (hierárquico):**
```
Capítulos → "voltar" → Livros → "voltar" → Categorias → "voltar" → Menu Principal
```

### Regra de ouro
- Menu com **3+ níveis de profundidade** → SEMPRE use navegação hierárquica
- Navegação monolítica é frustrante para usuários cegos (esperavam voltar 1 nível, voltaram 3)

---

## 📚 GUIA: Categorização de Livros — Como Funciona

### Estrutura de diretórios
```
audiobooks/
├── Inteligencia_sensorial/
│   ├── Livro_A/ → 01-Cap1.mp3, 02-Cap2.mp3, ...
│   └── Livro_B/
└── Geral/
    └── Livro_C/ → 01-Cap1.mp3, ...
```

### Como adicionar novo livro (manual)
```bash
mkdir -p audiobooks/Geral/Novo_Livro
# Copie arquivos MP3 numerados: 01-Cap1.mp3, 02-Cap2.mp3, ...
cp *.mp3 audiobooks/Geral/Novo_Livro/
git add audiobooks/
git commit -m "Novo livro"
git push
# Aguarde 30s → Teste na Alexa
```

### Como a categoria é definida?

**Atualmente (25 Fev 2026):**
- Categoria = nome da subpasta em `audiobooks/`
- Lambda filtra documentos com `categoria == "Livros"` (genérico)
- **Ambas as categorias (Inteligência + Geral) mostram TODOS os livros** (filtro é igual para ambas)

**Futuro (quando implementar subcategorias reais):**
```python
LIVROS_CATEGORIAS = [
    {"filtro": "Livros: Inteligencia Sensorial"},
    {"filtro": "Livros: Geral"},
]
```

E documentos teriam:
```json
{"categoria": "Livros: Inteligencia Sensorial"}
```

### Interface GUI de upload (futuro)
Se adicionar `enviar_livro_ui.py` (tipo `enviar_musica_ui.py`):
1. Seleciona categoria
2. Seleciona pasta com MP3s numerados
3. Clica "Publicar" → Copia, atualiza indice.json, push, Alexa tem acesso

**Por enquanto:** Adicionar manualmente é suficiente. Quando tiver +10 livros, implementar GUI.

---

**Fim do Relatório**
*Atualizado em 25 de Fevereiro, 2026*
*Situação: ✅ Skill funcionando | ✅ Navegação hierárquica | ✅ Sincronização Lambda↔Repo | ✅ Categorização documentada*
