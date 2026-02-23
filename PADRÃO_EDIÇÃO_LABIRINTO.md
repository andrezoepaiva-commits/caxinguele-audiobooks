# Padrão de Edição no Labirinto — Interação Dinâmica com Itens

## Arquitetura Geral

```
Navegação Estática (Labirinto GUI)
    ↓
Menu → Submenu → [Lista de Itens Reais] ← Dinâmico
            ↓
        Para cada item:
        [1] Ouvir/Ver conteúdo
        [2] Editar
        [3] Próximo / Voltar
            ↓
        Se escolher [2] Editar:
        [1] Remover item
        [2] Adicionar/Modificar conteúdo
        [3] Voltar
```

---

## Menus com Lógica de Edição (Implementar no Lambda)

### ✅ Menu [1] — Últimas Atualizações
**Estrutura:** Menu 1 → Lista de itens não vistos (livros, artigos, emails, música, etc.)

**Para cada item:**
- [1] Ouvir/ler item
- [2] Editar
  - [1] Remover (não mostrar mais)
  - [2] Favoritar
  - [3] Voltar
- [3] Próximo item / Voltar

---

### ✅ Menu [2] — Livros
**Estrutura:** Menu 2 → Livros publicados → Capítulos do livro

**Para cada livro:**
- [1] Ouvir
- [2] Editar
  - [1] Remover da biblioteca
  - [2] Renomear livro
  - [3] Voltar
- [3] Próximo livro / Voltar

---

### ✅ Menu [3] — Favoritos Importantes
**Estrutura:** Menu 3 → Submenu (Salvos/Artigos/Emails/Docs) → Itens reais

**Para cada favorito:**
- [1] Ouvir/ler
- [2] Editar
  - [1] Remover de favoritos
  - [2] Mover para outra categoria de favoritos
  - [3] Voltar
- [3] Próximo item / Voltar

---

### ✅ Menu [4] — Música
**Estrutura:** Menu 4 → Submenu (Caxinguelê/Capoeira/Playlists) → Músicas reais

**Para cada música:**
- [1] Ouvir
- [2] Editar
  - [1] Remover da playlist
  - [2] Adicionar a outra playlist
  - [3] Voltar
- [3] Próxima música / Voltar

---

### ✅ Menu [5] — Calendário e Compromissos
**Estrutura:** Menu 5 → Submenu (Próximos/Marcar/Gerenciar) → Compromissos reais

**Para cada compromisso:**
- [1] Ouvir detalhes
- [2] Editar
  - [1] Remover compromisso
  - [2] Modificar data/hora/descrição (usuário fala)
  - [3] Voltar
- [3] Próximo compromisso / Voltar

---

### ✅ Menu [8] — Reuniões Caxinguelê
**Estrutura:** Menu 8 → Submenu (Próximas/Resumo/Íntegra/Histórico) → Reuniões reais

**Para cada reunião:**
- [1] Ouvir resumo/íntegra
- [2] Editar
  - [1] Adicionar anotações (usuário fala o que quer adicionar)
  - [2] Remover reunião do histórico
  - [3] Voltar
- [3] Próxima reunião / Voltar

---

### ✅ Menu [10] — Organizações da Mente em Listas
**Estrutura:** Menu 10 → Lista (Compras/Consultas/etc) → Itens reais

**Para cada item na lista:**
- [1] Ouvir resumo/íntegra/elaboração (escolher modo)
- [2] Editar
  - [1] Remover item
  - [2] Modificar conteúdo (usuário fala o que quer mudar)
  - [3] Voltar
- [3] Próximo item / Voltar

---

## Menus SEM Lógica de Edição (Apenas leitura)

### ❌ Menu [0] — Organizações Mentais
- Apenas gravação + classificação automática
- Não há itens para editar após salvos (vão direto para Menu 10/Listas)

### ❌ Menu [9] — Configurações
- Apenas seleção de opções (Voz, Velocidade, Guia)
- Não há itens para editar

---

## Padrão de Interação (Pseudo-código Lambda)

```python
# Fluxo geral para qualquer item com edição

while True:
    item = carregar_item(menu, submenu, numero_item)
    alexa_fala(f"Item {numero_item}: {item.titulo}")

    while True:
        opcao = usuario_diz([
            "1 para ouvir",
            "2 para editar",
            "3 para próximo ou voltar"
        ])

        if opcao == 1:
            alexa_fala_conteudo(item)

        elif opcao == 2:
            while True:
                acao = usuario_diz([
                    "1 para remover",
                    "2 para modificar",
                    "3 para voltar"
                ])

                if acao == 1:
                    remover_item(item)
                    break
                elif acao == 2:
                    novo_conteudo = usuario_dita("O que quer adicionar ou mudar?")
                    modificar_item(item, novo_conteudo)
                    alexa_fala("Modificado com sucesso")
                    break
                elif acao == 3:
                    break

        elif opcao == 3:
            break
```

---

## Status de Implementação

| Menu | Estrutura Labirinto | Itens Dinâmicos | Edição |
|------|-------------------|---|---|
| [0] | ✅ | ❌ | ❌ |
| [1] | ✅ | ❌ | ⏳ |
| [2] | ✅ | ❌ | ⏳ |
| [3] | ✅ | ❌ | ⏳ |
| [4] | ✅ | ❌ | ⏳ |
| [5] | ✅ | ❌ | ⏳ |
| [8] | ✅ | ❌ | ⏳ |
| [9] | ✅ | N/A | N/A |
| [10] | ✅ | ✅ (via listas_mentais.py) | ✅ |

**Próximas etapas:**
- Implementar listagem de itens dinâmicos no Lambda
- Adicionar submenu de edição para cada item
- Integrar com APIs (Google Calendar, Gmail, etc.)
