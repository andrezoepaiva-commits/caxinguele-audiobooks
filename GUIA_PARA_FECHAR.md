# GUIA FINAL — Projeto Caxinguele
## Como fazer seu amigo receber audiobooks na Alexa

---

## COMO FUNCIONA (resumo)

```
Você coloca arquivo no app Caxinguele
         ↓
App processa e gera MP3
         ↓
MP3 sobe para Google Drive (público automaticamente)
         ↓
Índice publicado no GitHub Pages (público)
         ↓
Skill Alexa do amigo lê o índice e toca o áudio
         ↓
Amigo ouve: "Alexa, abre meus audiobooks"
```

**IMPORTANTE: Não precisa de Amazon Household!**
Os audiobooks ficam públicos automaticamente.
O amigo só precisa instalar a Skill Alexa.

---

## O QUE VOCÊ (ANDRÉ) FAZ AGORA

### Passo 1 — Verificar se a Skill está publicada

A Skill precisa estar em modo LIVE (publicado) no Alexa Developer Console,
não apenas em modo de desenvolvimento.

1. Acesse: https://developer.amazon.com/alexa/console/ask
2. Faça login com sua conta Amazon
3. Encontre a Skill "Projeto Caxinguele" (ou nome que deu)
4. Verifique se está em status "Live" ou "Development"
5. Se estiver só em "Development" → o amigo não consegue instalar

### Passo 2 — Habilitar a Skill no device do amigo remotamente

Se a Skill estiver publicada, você consegue ativar no device do amigo:

1. Acesse: alexa.amazon.com.br (site web da Alexa)
2. Vá em "Skills" → "Suas Skills"
3. Procure pela sua Skill
4. Clique "Ativar" no device do amigo (se aparece na sua conta)

### Passo 3 — Ou: pedir para o amigo instalar

Se não conseguir remotamente, passe estas instruções ao amigo:

```
INSTRUÇÕES PARA O AMIGO INSTALAR:

1. Abra o app Alexa no celular
2. Toque em "Mais" (canto inferior direito)
3. Toque em "Skills e jogos"
4. Pesquise por: "Projeto Caxinguele"
5. Toque em "Ativar skill"
6. Pronto!
```

---

## O QUE O AMIGO FAZ (comandos de voz)

Depois de instalar a Skill, o amigo usa assim:

```
"Alexa, abre meus audiobooks"

→ Alexa responde: "Biblioteca pronta. O que deseja?"

→ Amigo diz: "Quais documentos tenho, cambio"

→ Alexa lista os audiobooks disponíveis

→ Amigo diz: "Le o documento número um, cambio"

→ Alexa começa a tocar o audiobook
```

### Regra do CAMBIO
- Comandos longos: termine com "cambio"
- Comandos curtos (Para / Continua / Próximo): sem cambio

---

## COMO VOCÊ MANDA UM ARQUIVO PARA ELE

1. Abra o app Caxinguele (Projeto Caxinguele.bat ou .vbs no Desktop)
2. Arraste o arquivo (PDF, Word, email, etc) ou clique "Abrir Documento"
3. Confirme o nome que vai aparecer na Alexa
4. Em "Enviar para:" selecione "Meu Amigo"
5. Clique "CONVERTER E PUBLICAR"
6. Em poucos minutos o amigo já consegue ouvir!

---

## PROBLEMA PRINCIPAL A RESOLVER

**A Skill está publicada ou só em desenvolvimento?**

Se estiver só em desenvolvimento, o amigo não consegue instalar.
Você precisa submeter para publicação no Alexa Developer Console.

Alternativa: certificar o amigo como "beta tester" no Developer Console,
assim ele instala mesmo sem publicação pública.

---

## PRÓXIMO PASSO IMEDIATO

Acesse: https://developer.amazon.com/alexa/console/ask
Verifique o status da Skill e me avise o que aparece.
