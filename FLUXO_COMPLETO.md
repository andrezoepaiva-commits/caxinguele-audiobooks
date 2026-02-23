# 🗺️ Fluxo Completo de Dados — Caxinguele v2

## Visão geral: Como dados fluem entre menus

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  AMIGO CEGO USANDO ALEXA → DADOS SALVOS → LABIRINTO   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Fluxos por Menu

### Menu [0] — Organizações Mentais (Gravação)
```
AMIGO FALA via Alexa
    ↓
gravacao_mental.py: simular_gravacao()
    ├─ Extrai frases
    ├─ Classifica automaticamente (Menu 10)
    └─ Retorna lista de itens + confirmação
    ↓
AMIGO CONFIRMA: "Confirmar" ou direciona item
    ↓
gravacao_mental.py: salvar_itens_nas_listas()
    ├─ Carrega listas_mentais.json
    ├─ Insere itens nas listas corretas
    └─ Salva em listas_mentais.json
    ↓
[10] LISTAS MENTAIS: item aparece na lista
    ↓
[1] ÚLTIMAS ATUALIZAÇÕES: item aparece como "novo"
```

**Arquivo de persistência:** `listas_mentais.json`

---

### Menu [1] — Últimas Atualizações (Agregador)
```
AMIGO PEDE: "Últimas atualizações"
    ↓
labirinto_ui.py: _popular_tree() tipo="recentes"
    ├─ Carrega dados de Menu [2] (livros novos)
    ├─ Carrega dados de Menu [3] (favoritos novos)
    ├─ Carrega dados de Menu [4] (música nova)
    ├─ Carrega dados de Menu [5] (compromissos próximos)
    ├─ Carrega dados de Menu [8] (reuniões)
    └─ Carrega dados de Menu [10] (itens novos em listas)
    ↓
AGREGA: "Você tem 5 atualizações"
    ↓
AMIGO ESCOLHE: "1" (primeiro item)
    ↓
OPÇÕES:
  ├─ [1] Ouvir detalhes
  ├─ [2] Favoritar
  ├─ [3] Próximo item
  └─ [4] Menu principal
    ↓
FAVORITAR → adicionar_favorito(sublista, item)
    ↓
[3] FAVORITOS IMPORTANTES: item aparece na sublista
```

**Arquivo de persistência:** `favoritos.json`, `compromissos.json`, `listas_mentais.json`
**Tipo:** Leitura apenas (sem escrita em Menu 1, só em origem)

---

### Menu [2] — Livros
```
AMIGO PEDE: "Menu dois - Livros"
    ↓
livros_ui.py: carregar_audiobooks()
    ├─ Lê pasta: BASE_DIR / "audiobooks"
    ├─ Filtra: *.mp3
    └─ Retorna: [{titulo, duracao, data, arquivo}]
    ↓
ALEXA: "Você tem 7 livros. [1] Dom Casmurro, [2] Macunaíma..."
    ↓
AMIGO ESCOLHE: "1"
    ↓
ALEXA: "Dom Casmurro. Capítulos: [1] Prólogo, [2] Cap 1..."
    ↓
AMIGO ESCOLHE: "2" (Capítulo 1)
    ↓
REPRODUZ: MP3 com pygame.mixer
    ├─ Toca áudio
    ├─ Salva posição (mm:ss) em ultimo_ouvido.json
    └─ Próxima vez, continua daqui
    ↓
OPÇÕES DURANTE REPRODUÇÃO:
  ├─ Play/Pause
  ├─ Próximo/Anterior capítulo
  ├─ Velocidade (0.8x até 2.0x)
  └─ Voltar
```

**Arquivos de persistência:**
- `audiobooks/` (pasta com MP3s)
- `ultimo_ouvido.json` (posição de cada livro)

---

### Menu [3] — Favoritos Importantes
```
ORIGEM: Amigo favorita items de Menu [1]
    ↓
favoritos_ui.py: adicionar_favorito(sublista, item)
    ├─ Verifica sublista (Salvos, Notícias, Emails, Documentos)
    ├─ Evita duplicatas
    └─ Salva em favoritos.json
    ↓
[3] FAVORITOS: "Você tem 3 favoritos em Salvos para Escutar Mais Tarde"
    ↓
AMIGO PEDE: "Remover"
    ↓
ALEXA: "Qual favorito? [1] Podcast X, [2] Audiobook Y..."
    ↓
AMIGO ESCOLHE: "1"
    ↓
favoritos_ui.py: remover_favorito(sublista, idx)
    ├─ Remove de favoritos.json
    └─ Atualiza contador
```

**Arquivo de persistência:** `favoritos.json`
**Tipo:** Read/Write (amigo pode adicionar via Menu [1], remover aqui)

---

### Menu [4] — Música
```
AMIGO PEDE: "Menu quatro - Música"
    ↓
musica_ui.py: carregar_playlists()
    ├─ Fonte: [DECIDIR] Spotify API / YouTube Music / Arquivos locais
    └─ Retorna: [{nome, artista, duracao, url/arquivo}]
    ↓
ALEXA: "Você tem 3 playlists. [1] Samba, [2] Música Clássica..."
    ↓
AMIGO ESCOLHE: "1" (Samba)
    ↓
ALEXA: "Playlist: Samba. [1] Música A, [2] Música B..."
    ↓
AMIGO ESCOLHE: "1"
    ↓
REPRODUZ: MP3 com pygame.mixer
    ├─ Toca música
    ├─ Próxima/Anterior
    └─ Controles: Play/Pause/Volume
```

**Arquivos de persistência:**
- `musicas.json` (se local) OU Spotify API token
- Aguarda implementação

---

### Menu [5] — Calendário e Compromissos
```
AMIGO PEDE: "Menu cinco - Calendário"
    ↓
calendario_ui.py: carregar_compromissos()
    ├─ Lê compromissos.json
    └─ Ordena por data+hora (próximos primeiro)
    ↓
ALEXA: "Você tem 3 compromissos próximos. [1] Consulta dia 23 às 14h..."
    ↓
AMIGO ESCOLHE: "1"
    ↓
ALEXA: "Consulta médica com Dr. Ferreira. Data: 23/02/2026. Hora: 14h.
         O que quer fazer? [1] Editar, [2] Remover, [3] Próximo"
    ↓
AMIGO ESCOLHE: "1" (Editar)
    ↓
ALEXA: "O que quer editar? [1] Data, [2] Hora, [3] Descrição"
    ↓
AMIGO ESCOLHE: "1"
    ↓
ALEXA: "Nova data? Fale em formato DD/MM/AAAA"
    ↓
AMIGO FALA: "vinte e cinco de fevereiro"
    ↓
calendario_ui.py: salvar_compromissos()
    ├─ Atualiza compromissos.json
    └─ Confirma: "Alterado para 25 de fevereiro"
```

**Arquivo de persistência:** `compromissos.json`
**Tipo:** Read/Write completo (criar, editar, remover)

---

### Menu [8] — Reuniões Caxinguelê
```
AMIGO PEDE: "Menu oito - Reuniões"
    ↓
reunioes_ui.py: carregar_reunioes()
    ├─ Lê reunioes.json
    └─ Retorna: [{data, hora, participantes, resumo, transcricao}]
    ↓
SUBMENU [1] — Próximas reuniões agendadas
    └─ Calendário de reuniões futuras
    ↓
SUBMENU [2] — Resumo da última reunião
    └─ IA gera resumo de última reunião (Google Summarization API)
    ↓
SUBMENU [3] — Íntegra da última reunião
    └─ Transcrição completa (Whisper ou Google Speech-to-Text)
    ↓
SUBMENU [4] — Histórico de reuniões
    └─ Lista todas reuniões passadas (com opção de reproduzir)
```

**Arquivo de persistência:** `reunioes.json`
**Tecnologia:**
- Transcrição: OpenAI Whisper
- Resumo: Google Cloud Summarization API

---

### Menu [9] — Configurações
```
AMIGO PEDE: "Menu nove - Configurações"
    ↓
SUBMENU [1] — Escolher Voz de Hoje
    ├─ Edge-TTS: Thalita, Francisco, Camila, Antônio (PT-BR apenas)
    └─ Salva escolha em config.json
    ↓
SUBMENU [2] — Velocidade da Fala
    ├─ Escala: 0.8x até 2.0x
    └─ Salva em config.json
    ↓
SUBMENU [3] — Guia do Usuário
    └─ Reproduz GUIA_ALEXA_ACESSIVEL.md em áudio
```

**Arquivo de persistência:** `config.json`
**Tipo:** Somente leitura e seleção (não cria dados)

---

### Menu [10] — Organizações da Mente em Listas
```
ORIGEM: Menu [0] (gravação) ou criação manual
    ↓
listas_mentais.py: carregar_listas()
    ├─ Lê listas_mentais.json
    └─ Retorna: {nome_lista: [itens]}
    ↓
ALEXA: "Suas listas: [1] Compras (4 itens), [2] Consultas Médicas (2 itens)..."
    ↓
AMIGO ESCOLHE: "1" (Compras)
    ↓
ALEXA: "Compras: [1] Leite, [2] Pão, [3] Ovos, [4] Banana"
    ↓
AMIGO ESCOLHE: "1" (Leite)
    ↓
ALEXA: "Leite. O que fazer? [1] Ouvir novamente, [2] Editar, [3] Remover, [4] Próximo"
    ↓
AMIGO ESCOLHE: "2" (Editar)
    ↓
ALEXA: "Novo conteúdo? Fale..."
    ↓
AMIGO FALA: "Leite integral meio litro"
    ↓
listas_mentais.py: salvar_listas()
    ├─ Atualiza listas_mentais.json
    └─ Confirma: "Item alterado"
    ↓
OPÇÕES ADICIONAIS:
  ├─ Renomear lista: "Compras" → "Compras da semana"
  ├─ Remover lista: "Tem certeza? 4 itens serão deletados"
  ├─ Adicionar item novo: "Novo item para Compras?"
  └─ Modo de escuta: [1] Resumo, [2] Íntegra, [3] IA elabora, [4] Original
```

**Arquivo de persistência:** `listas_mentais.json`
**Tipo:** Read/Write completo

---

## 🔄 Persistência — Como tudo é salvo

### JSONs Principais
| Arquivo | Menus que usam | O que guarda |
|---------|---|---|
| `favoritos.json` | [1], [3] | 4 sublistas de favoritos |
| `compromissos.json` | [5] | Compromissos do amigo |
| `listas_mentais.json` | [0], [10], [1] | Anotações e listas pessoais |
| `reunioes.json` | [8] | Histórico de reuniões |
| `ultimo_ouvido.json` | [2] | Posição de cada audiobook |
| `config.json` | [9] | Preferências (voz, velocidade) |
| `menus_config.json` | Labirinto GUI | Estrutura dos menus (edições) |

---

## 🛠️ Labirinto GUI — Edições de Estrutura

```
VOCÊ (Desenvolvedor) abre Labirinto GUI
    ↓
labirinto_ui.py: _carregar_dados()
    ├─ Carrega menus_config.json (prioridade)
    ├─ Se não existir, usa indice.json
    └─ Se nada, usa MENU_PADRAO
    ↓
EDITA:
  ├─ Renomear menu: [5] "Calendário" → "Agenda Pessoal"
  ├─ Adicionar submenu: Menu [5] → novo submenu "Aniversários"
  ├─ Remover submenu: Remove "Gerenciar Compromissos"
  └─ Reordenar menus: Sobe Menu [10] para cima de Menu [9]
    ↓
CLICA "SALVAR E PUBLICAR"
    ├─ labirinto_ui.py: _salvar_estrutura()
    │  └─ Salva em menus_config.json (persistência)
    ├─ Salva em indice.json também
    └─ GitHub Pages atualizado
    ↓
PRÓXIMA VEZ QUE ABRE APP:
  └─ Carrega de menus_config.json (suas edições persistem)
```

---

## 📋 Resumo de Responsabilidades por Arquivo

| Arquivo | Função |
|---------|--------|
| `gravacao_mental.py` | Classifica voz em categorias |
| `calendario_ui.py` | Gerencia compromissos (CRUD) |
| `favoritos_ui.py` | Gerencia favoritos (read, remove) |
| `listas_mentais.py` | Gerencia listas (CRUD) |
| `livros_ui.py` | *Não existe* — reproduz audiobooks |
| `musica_ui.py` | *Não existe* — reproduz música |
| `reunioes_ui.py` | *Não existe* — gerencia reuniões |
| `labirinto_ui.py` | Estrutura visual + edição de menus |
| `audiobook_gui.py` | Interface principal |

---

## ✅ Checklist de Dados

Antes de cada teste, verifique:
- [ ] `favoritos.json` existe e tem 6+ itens
- [ ] `compromissos.json` existe e tem 4+ compromissos
- [ ] `listas_mentais.json` existe e tem 3+ listas
- [ ] `menus_config.json` existe com 9 menus
- [ ] `gravacao_mental.py` classifica corretamente
- [ ] Fluxo [0]→[10]→[1] funciona

---

**Última atualização:** 22/02/2026
**Versão:** Caxinguele v2 Fase 1D
