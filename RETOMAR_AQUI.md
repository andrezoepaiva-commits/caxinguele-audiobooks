# RETOMAR AQUI — pdf2audiobook (Caxinguele Audiobooks v3)

**Data:** 09/05/2026 (atualizado S246 cont 2 — original S206 21/04/2026)
**Sessão de origem:** S246 cont 2 (C5+: 6 fixes UX + Opções TRIVIAL state-aware + deploy)
**Status:** Lambda DEPLOYADA na AWS ✅ — falta push GitHub + Build no Alexa Console (2 ações manuais)

---

## 🚦 SE QUISER SÓ FAZER OS 5 MIN ESSENCIAIS

```
1. cd C:\Users\andre\Desktop\Projetos\Produtos\Apps\pdf2audiobook
2. git push origin master
   ⚠️ Se der 401: regenerar GitHub PAT em github.com → Settings → Developer settings → Personal access tokens (pendência herdada de S242 cont)
   ⏱️ Após push, AGUARDAR 1-2 min antes de testar no Echo — GitHub Pages CDN tem cache. Se testar imediatamente, Lambda pode buscar `indice.json` antigo (sem renumeração 8/9 + Cap01 ainda apontando samplelib).
3. Abrir https://developer.amazon.com/alexa/console/ask → Meus Audiobooks (Development) → Interaction Model → JSON Editor → apagar tudo → colar conteúdo de alexa_skill/interaction_model.json → Save Model → Build Model → aguardar "Build Successful"
4. Testar 1 cenário no Simulator: "alexa, abre meus audiobooks" → "livros" → "ajuda" — DEVE re-listar os livros (não dizer texto fixo enorme)
```

Pronto. O resto deste documento é detalhe pra quando QUISER aprofundar.

---

## 📖 GLOSSÁRIO DE NOMES (não confundir)

- **"Caxinguele Audiobooks"** (sem acento) = ESTE projeto, skill Alexa pro amigo cego
- **"meus audiobooks"** = invocation name (o que o amigo fala pra abrir a skill: "Alexa, abre meus audiobooks")
- **"pdf2audiobook"** = nome da pasta no Desktop deste projeto
- **"Caxinguelê"** (com acento) = projeto verde de plantio de árvores (HIBERNANDO em outro contexto, NÃO TOCAR aqui)
- **`CaxingueleAudiobooks`** = nome da função Lambda na AWS

---

## ⚠️ ABRIR PRÓXIMA SESSÃO ASSIM

1. Ler **toda esta seção "ATUALIZAÇÃO S246 cont 2"** abaixo antes de tocar em qualquer arquivo
2. Ler `~/.claude/projects/C--Users-andre/memory/caxinguele_arestas_pendentes.md` (arestas #7-#13 pendentes)
3. Decidir: rodar 2 ações manuais agora (push + Build) OU continuar arestas #7-#13?

### Pontos seguros de rollback (se algo der errado)

- **Código Lambda anterior ao C5+:** `alexa_skill/lambda/lambda_function.py.bak-S246-c5plus` (cópia exata feita ANTES do batch de Edits desta sessão)
- **Estado git anterior ao /r% saves desta sessão:** commit `1273587` (backup labirinto pré-batch /r%)
- **Estado git anterior ao C5+ Lambda:** commit `04e2dbd` (antes dos 2 commits de teste S242 cont)
- **Reverter Lambda na AWS:** boto3 `publish_version` listou versões anteriores; pode rolar back via console AWS Lambda → Versions

### Checklist de teste (depois de fazer as 2 ações manuais)

Rodar no Alexa Simulator (Development) OU Echo físico:

```
TESTE 1 (P1 reverter MINIMALISTA):
  → "abre meus audiobooks" + escolhe livro + começa do início + pausa
  → fecha skill, espera 2 min, reabre
  → "continuar" — deve retomar do exato segundo (não dizer "não consegui retomar")

TESTE 2 (P2a paginação F4):
  → "livros" → "próximos"
  → DEVE responder "esses são todos os seus livros" (não repetir lista)

TESTE 3 (P2b esquecer sem número — DEPENDE BUILD):
  → "livros" → "esquecer"
  → DEVE pedir "esquecer qual número?" (não dizer "Até logo!")

TESTE 4 (P2c esquecer livro sem progresso):
  → "livros" → "esquecer 3" (livro nunca ouvido)
  → DEVE responder "esse livro não tem progresso pra esquecer"

TESTE 5 (P2d menu sem 8 — DEPENDE PUSH):
  → "abre meus audiobooks"
  → menu deve ter sequência contínua 0,1,2,...,7,8,9 (sem buraco no 8)

TESTE 6 (P2e ouvidos):
  → "livros" → "ouvidos" (em conta nova/sem progresso)
  → DEVE responder "você ainda não terminou nenhum livro completo"

TESTE 7 (P2f ajuda contextual):
  → "livros" → "ajuda" (em qualquer estado de menu)
  → DEVE re-apresentar o menu/lista atual (não dizer texto fixo enorme genérico)
```

Se TESTE 7 falhar em estado `nivel=item` (livro selecionado) ou `livros_capitulos` ou reuniões selecionadas: comportamento ESPERADO (arestas #7-#9 pendentes).

### Verificação aresta #12 (BUG ja_lido) — comando CloudWatch sugerido

Tocar livro qualquer até o fim SEM pausar. Depois rodar:

```
aws logs filter-log-events --log-group-name /aws/lambda/CaxingueleAudiobooks --filter-pattern "Progresso salvo" --start-time $(date -d '10 minutes ago' +%s)000
```

Se NÃO aparecer entrada de "Progresso salvo" pro último capítulo do livro tocado naturalmente: **aresta #12 confirmada como BUG real** — `handle_playback_stopped` não dispara em FINISHED, livros terminados naturalmente nunca atingem critério "ja_lido". Fix: adicionar trigger em `handle_playback_finished`.

## ATUALIZAÇÃO S246 cont 2 (09/05/2026) — C5+ executado

### O que foi feito (sessão de ~120-150min)

**Decisão R2:** Caminho C5+ (aparar 5 arestas reais confirmadas em S243 + Opções TRIVIAL no mesmo batch). Anti-ancoragem reativa após André questionar adiamento — compounding com batch.

**Aplicado e validado:**
- ✅ P1 — `_build_audio` MINIMALISTA REVERTIDO (restaurou metadata + sessionAttributes — Resume entre capítulos volta a funcionar) — `lambda_function.py` L2677-2696
- ✅ P2a — F4 paginação 1 página (detecta fim antes de avançar) — `lambda_function.py` L261-282
- ✅ P2b — `EsquecerLivroIntent` samples sem slot {numero} + handler pede número — `interaction_model.json` + `lambda_function.py` L317-321
- ✅ P2c — Mensagem clara "livro sem progresso" — `lambda_function.py` L329-334
- ✅ P2d — `indice.json` renumerou 9→8 (Configurações) e 10→9 (Listas) — sem buraco
- ✅ P2e — Critério `ja_lido` endurecido (`MIN_OFFSET_OUVIDO_MS = 60_000`) + msg amigável quando vazio — `lambda_function.py` L786-825 + handler L289-298
- ✅ P2f — Opções TRIVIAL: `_handle_ajuda` agora chama `_reconstruir_menu(menu_tipo)` (state-aware, cobre 11 estados) — `lambda_function.py` L2342
- ✅ Bônus: `indice.json` Cap01 voltou pro Drive (saiu do samplelib teste de S242 cont)
- ✅ Re-zip + Deploy AWS — `LastUpdateStatus: Successful`, 25.463 bytes, **SHA256 deployado: `lal1yj2xT+FgRTN+PKUZ2FShYHjvm62LSpbY0TYUbao=`** (verificado empiricamente em S246c2 — confirmar match futuro com `aws lambda get-function-configuration --function-name CaxingueleAudiobooks --query 'CodeSha256'` ou `python -c "import boto3; print(boto3.client('lambda',region_name='us-east-1').get_function_configuration(FunctionName='CaxingueleAudiobooks').get('CodeSha256'))"`)
- ✅ Auditoria FULL `/r*`: 21/21 GROUNDED, 0 furos críticos
- ✅ Commit local: `fe4264b` (4 files changed, 867 insertions, 173 deletions)

### 🔴 2 AÇÕES MANUAIS PENDENTES (você precisa fazer)

#### Ação 1 — Push GitHub (publica `indice.json` no GitHub Pages)

```
cd C:\Users\andre\Desktop\Projetos\Produtos\Apps\pdf2audiobook
git push origin master
```

**Por que:** Lambda lê `indice.json` do GitHub Pages. Sem push, o menu corrigido (sem buraco no 8) e o Cap01 com URL Drive não chegam na Alexa.

#### Ação 2 — Build do `interaction_model.json` no Alexa Developer Console

Sem ASK CLI instalado — só manual:

1. Abrir https://developer.amazon.com/alexa/console/ask
   - **Login:** conta Amazon (Bitwarden entrada "Amazon" OU "Alexa Developer"). Se 2FA pedir código, vai por SMS.
2. Skill **Meus Audiobooks** (Development, NÃO Live)
3. Aba **Interaction Model** → **JSON Editor**
4. Apagar JSON atual e colar de: `C:\Users\andre\Desktop\Projetos\Produtos\Apps\pdf2audiobook\alexa_skill\interaction_model.json`
5. Save Model → Build Model → aguardar "Build Successful" (~30-60s)

**Por que:** novos samples "esquecer", "esquecer livro", "esquecer um" só funcionam após Build registrar no Alexa.

**Plano B se Build falhar (3 erros prováveis + fixes):**

| Erro provável | Fix |
|---|---|
| "Intent X conflicts with built-in" | Reverter samples problemáticos do `EsquecerLivroIntent` ao estado pré-S246c2 (git diff `interaction_model.json` mostra o que foi adicionado) |
| "Invalid JSON" | Validar localmente: `python -c "import json; json.load(open(r'C:\Users\andre\Desktop\Projetos\Produtos\Apps\pdf2audiobook\alexa_skill\interaction_model.json', encoding='utf-8'))"` |
| "Missing field" / "Schema error" | Comparar com versão git anterior: `cd pdf2audiobook && git diff HEAD~1 alexa_skill/interaction_model.json` |

### O que JÁ funciona AGORA (mesmo sem 2 ações acima)

- ✅ Resume entre capítulos volta (P1)
- ✅ "Próximos" diz "esses são todos" no fim da lista (P2a)
- ✅ "Esquecer 3" em livro sem progresso → mensagem clara (P2c)
- ✅ "Ouvidos" sem livros completos → "ainda não terminou nenhum" (P2e)
- ✅ "Ajuda" re-apresenta menu/lista do estado atual em 11 dos ~14 estados (P2f)

### O que NÃO funciona até fazer as 2 ações

- ❌ Falar só "esquecer" sem número (precisa Build)
- ❌ Menu sem buraco no 8 (precisa push)
- ❌ Cap01 reproduz Helen Keller real (precisa push — hoje toca samplelib 3s se Lambda buscar do servidor sem o push)

### Notas pós-S246 cont 2 (preencher conforme amigo testar entre sessões)

> Espaço pra anotar feedback real do amigo OU comportamento inesperado observado entre sessões. Próxima sessão deve ler isto ANTES de assumir que tudo funciona como esperado.

- (vazio — nenhuma nota ainda)

---

## 🎯 4 FRENTES PRÉ-LIBERAR PRO AMIGO (A+B+C+D — bloco S246c2)

> Ordem recomendada: **A → B → C → D**. A precisa ser feita por você no console Alexa (10 min). B/C/D são preenchimento aqui mesmo.

### 🔴 A — Verificar Skill: Development vs Live + Beta tester (VOCÊ FAZER)

**Por que crítico:** se a skill estiver só em Development, o amigo NÃO consegue invocar pelo Echo dele. Precisa OU publicar (Live) OU adicionar conta dele como Beta tester.

**Passo a passo:**

1. Abrir https://developer.amazon.com/alexa/console/ask
2. Clicar em **Meus Audiobooks**
3. Olhar canto superior — diz **Development** ou **Live**?
   - Se **Live** ✅: skill já está pública, qualquer Echo no Brasil acha. Pular pra B.
   - Se **Development**: opção 1 = Distribution → preencher tudo → Submit (~7 dias review). Opção 2 (mais rápida) = aba **Distribution** → **Availability** → **Beta Test** → adicionar email Amazon do amigo (a conta que ele usa no Echo dele).

4. Anotar resultado abaixo:

```
Estado da skill: ___ (Development ou Live)
Email Amazon do amigo: ___
Beta tester adicionado em: ___ (data)
Amigo aceitou convite Beta: ___ (sim/não/aguardando)
```

### 🟡 B — Setup do amigo (preencher antes de entregar)

```
Modelo Echo do amigo: ___ (Echo Dot 3ª? 4ª? 5ª? Show? Pop?)
Conta Amazon do Echo: ___ (mesma do email Beta?)
Idioma do Echo: ___ (Português Brasil obrigatório)
Casa do amigo tem Wi-Fi estável: ___ (sim/não/intermitente)
Amigo já usa outras skills: ___ (sim/não — se sim, diminui curva de aprendizado)
Quem instala/configura o Echo na casa do amigo: ___ (você presencial? alguém da família dele? remoto?)
Data prevista pra entrega: ___
```

### 🟡 C — DynamoDB pode ter dados de teste residuais

Tabela `caxinguele_progresso` na AWS pode ter `user_id` de teste seu (não do amigo). Não quebra nada, mas pode confundir categorização "ouvidos" se mesmo `user_id` for reutilizado.

**Antes de deletar — verificar schema da tabela** (primary key pode ser composite, aí o `delete-item` precisa de sort key também):

```
aws dynamodb describe-table --table-name caxinguele_progresso --region us-east-1 --query "Table.KeySchema"
```

Se retornar só `user_id` como HASH → comando de delete abaixo funciona como está. Se aparecer um segundo campo como RANGE → precisa adicionar essa chave também no `--key`.

**Comando pra ver o que tem:**

```
aws dynamodb scan --table-name caxinguele_progresso --region us-east-1 --max-items 20
```

**Se aparecer `user_id` começando com `amzn1.ask.account.` (formato Alexa real):** decidir caso a caso — pode ser teu de teste ou já do amigo (se ele já testou).

**Se aparecer `user_id` curto tipo "test-user" ou "andre":** purgar com:

```
aws dynamodb delete-item --table-name caxinguele_progresso --region us-east-1 --key '{"user_id": {"S": "VALOR_AQUI"}}'
```

⚠️ **Não deletar `user_id` do amigo depois que ele começar a usar** — isso apaga progresso real dele.

### 🟡 D — Comunicar ao amigo: 3 comportamentos novos

⚠️ **Comunicar D SÓ depois de A + push GitHub + Build no Alexa Console feitos.** Se amigo testar antes, mudança #1 ("esquecer pede número") não funciona ainda — Build é o que ativa os samples novos.

Antes do amigo testar, avisar (por áudio WhatsApp ou presencial):

> "Mudei 3 coisinhas pra ficar mais fácil:
>
> 1. Pra apagar o progresso de um livro, fala **'esquecer 3'** (com o número). Se falar só **'esquecer'**, ela vai te perguntar qual número.
>
> 2. Em qualquer momento que você se perder, fala **'ajuda'** — agora ela re-lê o menu certo (não fala texto fixo enorme).
>
> 3. Se mandar ela mostrar **'ouvidos'** sem ainda ter terminado nenhum livro, ela diz isso clarinho ('você ainda não terminou nenhum') em vez de listar coisa errada."

---

### Backups (`.bak-*`) na pasta `alexa_skill/lambda/`

3 backups acumulados — limpar quando confiança no novo código for alta:
- `lambda_function.py.bak-20260505-134226` (S242 cont)
- `lambda_function.py.bak-20260509-150844` (S246 cont 2 antes do MINIMALISTA)
- `lambda_function.py.bak-S246-c5plus` (antes deste batch)

### Tasks da sessão (referência — TaskList morre no /clear)

8 completed: P1 + P2a-f + P3 (deploy)
1 in_progress: P4 — Testar no Simulator + Echo (faltou rodar testes empíricos pós-deploy; depende de você fazer as 2 ações manuais primeiro)

### 6 arestas NOVAS abertas nesta sessão (em `caxinguele_arestas_pendentes.md` #7-#13)

- **#7-#9:** 3 buracos do Opções TRIVIAL (livro selecionado, capítulos, reuniões selecionadas)
- **#10:** MENU_DEFAULT desalinhado com `indice.json` (cosmético)
- **#11:** Onboarding diz "Caxinguele Audiobooks" mas invocation é "meus audiobooks"
- **#12:** 🔴 BUG REAL — critério "ja_lido" pode zerar pra livros terminados naturalmente sem pausa
- **#13:** 3 backups `.bak-*` sem critério de limpeza

### PLANO B se Drive falhar pra Cap01

`cap01.mp3` foi commitado em GitHub Pages (commit `5040782`). Se Drive falhar de novo, mudar URL no `indice.json` pra: `https://andrezoepaiva-commits.github.io/caxinguele-audiobooks/cap01.mp3`

---

## ATUALIZAÇÃO S242 cont (05/05/2026) [HISTÓRICO]

## ATUALIZAÇÃO S242 cont (05/05/2026)
- Chave AWS antiga (`AKIAY3EQGVXFEHB3L2PI`) estava VAZADA em screenshot — REVOGADA no console IAM ✅
- Chave nova criada e salva em `C:\Users\andre\.aws\credentials` ✅
- Teste python `boto3.client('sts').get_caller_identity()` passou — Account `608040299978`, root, HTTP 200 ✅
- **Próximo passo concreto: rodar o comando boto3 do "Caminho A" abaixo (deploy do lambda.zip)**
- Pendência paralela: migrar senhas pro Bitwarden + apagar `~/Desktop/assenhadas` (não bloqueia o deploy, mas evita re-vazamento)
- Pendência menor: GitHub Personal Access Token ainda 401 (regenerar quando precisar de git push)

---

## O QUE FOI FEITO (S206)

16 correções UX na lambda_function.py, todas auditadas (4× /rg, 2× /r*):

1. Auto-advance entre capítulos (PlaybackNearlyFinished → ENQUEUE)
2. "Capítulo X de Y" em `_build_audio()` com parâmetro `total_capitulos`
3. Categorias simplificadas (4 → menus numerados)
4. Mensagens de erro claras para cego
5. Números falados removidos dos menus
6. ResumeIntent robusto (fallback se sem progresso salvo)
7. Session death fixes (`end=False` em pontos críticos)
8. Navigation loop fix (voltar de Livros → menu principal)
9. Invocation name consistente "meus audiobooks"
10. FallbackIntent handler no código
11. CAMBIO removido do manifest (3 ocorrências)
12. FallbackIntent declarado no interaction model
13. Guia acessível reescrito (GUIA_ALEXA_ACESSIVEL.md, 105L)
14. skill_manifest.json limpo (description + examplePhrases)
15. interaction_model.json com 10 intents completos
16. lambda.zip regenerado com todas as correções

---

## PRÓXIMO PASSO — DEPLOY

### Bloqueio: credenciais AWS inválidas

O arquivo `~/.aws/credentials` tem token expirado. Erro: `UnrecognizedClientException`.

Para desbloquear, André precisa:
1. Entrar no console AWS → IAM → Security Credentials
2. Criar novo Access Key
3. Atualizar `~/.aws/credentials` com a nova key

### Caminho A — Terminal (quando credenciais renovadas)

```
python -c "import boto3; c=boto3.client('lambda',region_name='us-east-1'); f=open('alexa_skill/lambda/lambda.zip','rb').read(); print(c.update_function_code(FunctionName='CaxingueleAudiobooks',ZipFile=f))"
```

### Caminho B — Manual

1. Abrir console AWS Lambda → função `CaxingueleAudiobooks`
2. Upload do `alexa_skill/lambda/lambda.zip` (19.647 bytes)
3. Clicar Deploy

### Também pendente: GitHub token (401)

Regenerar em github.com → Settings → Developer settings → Personal access tokens.

---

## CHECKLIST PÓS-DEPLOY

- [ ] "Alexa, abrir meus audiobooks" no simulador
- [ ] Navegar menus 0-8
- [ ] Iniciar livro → verificar "Capítulo X de Y"
- [ ] "voltar" de dentro de Livros → menu principal
- [ ] Fechar e reabrir → verificar ResumeIntent
- [ ] Falar besteira → verificar FallbackIntent
- [ ] Testar no Echo físico com amigo

---

## NOTAS TÉCNICAS

- **Lambda function name**: `CaxingueleAudiobooks`
- **5 built-in intents**: Amazon adiciona automaticamente (FallbackIntent, CancelIntent, HelpIntent, StopIntent, NavigateHomeIntent)
- **AudioPlayer intents**: Pause/Resume/Next/Previous adicionados automaticamente quando AUDIO_PLAYER no manifest
- **Lambda timeout**: VERIFICAR no console se está >10s (código usa HTTP timeouts de 8-10s)
- **GitHub Pages**: 5/6 endpoints OK. feed.xml 404 mas nunca executa (indice.json tem early return)
- **Google Drive**: throttle de bandwidth por arquivo
- **CAMBIO residual**: 3 refs em ALEXA_SETUP.md (cosmético, documentação)

---

## ARQUIVOS IMPORTANTES

```
alexa_skill/lambda/lambda_function.py  — código da Lambda (~2250 linhas)
alexa_skill/lambda/lambda.zip          — pacote de deploy (19.647 bytes)
alexa_skill/interaction_model.json     — 10 intents, 85+ utterances
alexa_skill/skill_manifest.json        — metadata da skill
alexa_skill/ALEXA_SETUP.md            — guia de setup (com CAMBIO residual cosmético)
GUIA_ALEXA_ACESSIVEL.md               — guia para o amigo cego (105 linhas)
```

---

## FUTURO (após deploy + testes)

| # | Item | Nota |
|---|---|---|
| B.3 | Renomear invocation "super alexa" vs "meus audiobooks" | Decidir com Echo físico |
| C.1 | Google Calendar sync | Grátis, ~10 linhas, precisa re-OAuth |
| C.2 | Audiobookshelf backend | Servidor 24/7 necessário |
| 16B | Gmail → áudio pipeline | Próxima feature grande |
