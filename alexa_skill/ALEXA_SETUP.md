# Guia de Instalacao: Custom Skill Alexa — Projeto Caxinguele

## Pre-requisitos (fazer antes)

1. Conta gratuita em: developer.amazon.com (mesmo email da Amazon)
2. Conta gratuita na AWS: aws.amazon.com (free tier suficiente)
3. Amazon Household configurado (ver instrucoes abaixo)

---

## PASSO 1: Configurar Amazon Household

Para gerenciar a Alexa do seu amigo remotamente:

### Voce faz:
```
1. Acesse: amazon.com.br/myh/manage
2. Clique em "Adicionar adulto"
3. Digite o email da conta Amazon do seu amigo
4. Clique "Enviar convite"
```

### Seu amigo faz (guie por telefone, 2 minutos):
```
1. Abrir email "Andre convidou voce para Amazon Household"
2. Clicar "Aceitar convite"
3. Logar com conta Amazon dele
4. Confirmar
```

### Apos aceite — voce controla remotamente:
```
App Alexa > Configuracoes > Amazon Household
> Dispositivo dele aparece no seu app
> Voce instala skills, cria rotinas, configura tudo remotamente
```

---

## PASSO 2: Criar a Lambda Function (AWS)

### 2a. Acessar AWS Lambda
```
1. Acesse: console.aws.amazon.com/lambda
2. Clique "Criar funcao"
3. Escolha "Criar do zero"
4. Nome: CaxingueleAudiobooks
5. Runtime: Python 3.11
6. Arquitetura: x86_64
7. Clique "Criar funcao"
```

### 2b. Fazer upload do codigo
```
1. Na pagina da funcao, va em "Codigo"
2. Clique "Carregar de" > "Arquivo .zip"
3. Compacte a pasta lambda/ em um .zip
4. Faca upload
```

### 2c. Configurar o trigger
```
1. Clique em "Adicionar trigger"
2. Escolha "Alexa Skills Kit"
3. Desabilitar verificacao de ID por enquanto (mais facil para testar)
4. Clique "Adicionar"
```

### 2d. Copiar o ARN da funcao
```
Canto superior direito da pagina Lambda.
Parece com: arn:aws:lambda:us-east-1:123456789:function:CaxingueleAudiobooks
Guarde esse valor — vai precisar no proximo passo.
```

---

## PASSO 3: Criar a Skill no Alexa Developer Console

### 3a. Criar nova skill
```
1. Acesse: developer.amazon.com/alexa/console/ask
2. Clique "Create Skill"
3. Nome: Meus Audiobooks
4. Idioma: Portuguese (BR)
5. Modelo: Custom
6. Hosting: Provision your own
7. Clique "Create Skill"
```

### 3b. Configurar o modelo de interacao
```
1. No menu esquerdo, clique em "JSON Editor"
2. Cole o conteudo do arquivo interaction_model.json
3. Clique "Save Model"
4. Clique "Build Model" (aguarde 1-2 minutos)
```

### 3c. Conectar ao Lambda
```
1. No menu esquerdo, clique em "Endpoint"
2. Escolha "AWS Lambda ARN"
3. Cole o ARN do passo 2d no campo "Default Region"
4. Clique "Save Endpoints"
```

### 3d. Testar a skill
```
1. No menu superior, clique em "Test"
2. Mude "Skill testing is enabled in:" para "Development"
3. No campo de texto, escreva: abre meus audiobooks
4. Verifique a resposta
```

---

## PASSO 4: Instalar na Alexa do seu amigo

Com Amazon Household configurado (Passo 1):
```
App Alexa (no seu celular)
> Menu > Skills e Jogos
> Buscar: Meus Audiobooks
> "Habilitar para uso"
> Na tela, selecione o dispositivo do seu amigo

OU

App Alexa > dispositivo do amigo
> Configuracoes > Skills
> Buscar e instalar "Meus Audiobooks"
```

---

## Fluxo de uso (apos instalacao)

```
Andre converte documento no PC:
  python pipeline_mvp.py --arquivo livro.epub
  -> Sobe para Drive e publica RSS
  -> indice.json atualizado automaticamente

Amigo usa a Alexa:
  "Alexa, abre meus audiobooks"
  Alexa: "Biblioteca pronta. O que deseja? Termine com cambio."
  Amigo: "quais documentos tenho cambio"
  Alexa: "Voce tem 5 documentos: 3 livros, 1 artigo, 1 email. O que deseja?"
  Amigo: "le o livro numero dois cambio"
  Alexa: "Reproduzindo: Sapiens..."
```

---

## Limites do Free Tier AWS

- Lambda: 1 milhao de chamadas/mes GRATIS (suficiente para uso familiar)
- Dados: primeiros 100 GB/mes de saida GRATIS
- Custo real esperado: R$ 0,00 por mes para uso pessoal
