# ✅ Checklist de Testes Visuais — Fase 1D

## Como usar este checklist
1. Abra um terminal
2. Execute: `python audiobook_gui.py`
3. Siga cada teste abaixo
4. Marque com ✅ quando passou

---

## 📋 TESTE 5 — GUI Principal + Labirinto

**Comando:** `python audiobook_gui.py`

- [ ] Janela abre sem erro
- [ ] Botão "Labirinto de Números" existe
- [ ] Clica "Labirinto" → janela nova abre
- [ ] Labirinto mostra título "LABIRINTO DE NÚMEROS DA ALEXA"
- [ ] Preview mostra: "Você tem 9 opções. 0 para Organizações Mentais, 1 para Últimas Atualizações..."
- [ ] Treeview mostra 9 menus:
  - [ ] [0] Organizações Mentais
  - [ ] [1] Últimas Atualizações
  - [ ] [2] Livros
  - [ ] [3] Favoritos Importantes
  - [ ] [4] Música
  - [ ] [5] Calendário e Compromissos
  - [ ] [8] Reuniões Caxinguelê (com 4 submenus expandidos)
  - [ ] [9] Configurações
  - [ ] [10] Organizações da Mente em Listas
- [ ] Botões existem: Renomear, Subir, Descer, + Submenu, Remover, SALVAR E PUBLICAR
- [ ] Botões funcionam: Atualizar, Renomear (seleciona item, clica, dialog abre)

---

## 📋 TESTE 5B — Menu [3] Favoritos

**Na janela do Labirinto:**
1. Duplo-clique em `[3] Favoritos Importantes`
2. Nova janela abre: "Favoritos Importantes — Menu 3"

- [ ] Janela abre sem erro
- [ ] Listbox à esquerda mostra 4 categorias:
  - [ ] Salvos para Escutar Mais Tarde  (2)
  - [ ] Notícias e Artigos Favoritados  (2)
  - [ ] Emails Favoritados  (1)
  - [ ] Documentos Importantes  (1)
- [ ] Clica em "Salvos para Escutar Mais Tarde" → treeview mostra 2 itens à direita
- [ ] Treeview mostra colunas: "Favoritado em" e "Título"
- [ ] Seleciona um item + clica "Remover dos Favoritos" → pede confirmação
- [ ] Após remover → contadores atualizam: (1) em vez de (2)

---

## 📋 TESTE 5C — Menu [5] Calendário

**Na janela do Labirinto:**
1. Duplo-clique em `[5] Calendário e Compromissos`
2. Nova janela abre: "Calendário e Compromissos — Menu 5"

- [ ] Janela abre sem erro
- [ ] Treeview mostra 4 compromissos com colunas: Data, Hora, Compromisso, Descrição
- [ ] **Cores funcionam:**
  - [ ] Hoje (22/02) = amarelo
  - [ ] Amanhã (23/02) = verde
  - [ ] Próxima semana = verde
  - [ ] Passado = cinza (não há)

**Teste de criação:**
- [ ] Botão "+ Novo Compromisso" funciona
- [ ] Dialog abre com campos: Título, Data, Hora, Descrição
- [ ] Preenche exemplo: "Café com amigo", "24/02/2026", "10:30", "Na padaria"
- [ ] Clica "Confirmar" → item aparece na tabela
- [ ] Botão "Editar" funciona (duplo-clique ou seleciona + Editar)
- [ ] Dialog de edição mostra dados antigos
- [ ] Muda um campo e confirma → tabela atualiza
- [ ] Botão "Remover" funciona com confirmação

---

## 📋 TESTE 5D — Menu [10] Listas Mentais

**Na janela do Labirinto:**
1. Duplo-clique em `[10] Organizações da Mente em Listas`
2. Nova janela abre: "Organizações da Mente em Listas — Menu 10"

- [ ] Janela abre sem erro
- [ ] Treeview mostra 3 listas:
  - [ ] Compras (4 itens)
  - [ ] Lembretes Médicos (3 itens)
  - [ ] Ideias e Projetos (2 itens)

**Teste de lista:**
- [ ] Seleciona "Compras" + clica "Listar Itens" → expand a lista
- [ ] Mostra 4 itens: "Leite integral", "Pão de forma", "Ovos (dúzia)", "Banana"
- [ ] Clica item + "Editar Item" → dialog para editar conteúdo
- [ ] Clica item + "Remover Item" → pede confirmação, remove
- [ ] Botão "Renomear Lista" funciona → muda "Compras" para outro nome
- [ ] Botão "Remover Lista" funciona → pede confirmação com "X itens"

---

## 📋 TESTE 5E — Menu [0] Gravação Mental

**Na janela do Labirinto:**
1. Duplo-clique em `[0] Organizações Mentais`
2. Nova janela abre: "Menu 0 — Organizações Mentais"

- [ ] Janela abre sem erro
- [ ] Text area mostra exemplo pré-preenchido
- [ ] Botão "Classificar" funciona
- [ ] Mostra resultado: "Total: X itens" com categorias classificadas
- [ ] Botão "Confirmar e Salvar" funciona
- [ ] Após salvar, fecha automático e status mostra "Salvo!"
- [ ] **Verificar se itens foram para Menu [10]:**
  - [ ] Volta para o Labirinto
  - [ ] Duplo-clique em Menu [10]
  - [ ] Verifica se novos itens apareceram na lista "Compras" ou outra

---

## 📋 TESTE 6 — Menu [1] Últimas Atualizações

**Na janela do Labirinto:**
1. Clique simples em `[1] Últimas Atualizações` (sem duplo-clique)
2. Deve exibir preview: "automático — tudo não visto"

- [ ] Menu [1] está expandido mostrando subtítulo
- [ ] Status bar mostra: "N items não vistos"

---

## 📋 TESTE LABIRINTO — Estrutura

**Testes de edição de estrutura no Labirinto:**

1. **Renomear Menu:**
   - [ ] Seleciona `[5] Calendário e Compromissos`
   - [ ] Clica "Renomear"
   - [ ] Dialog abre com nome atual
   - [ ] Muda para "Agenda Pessoal"
   - [ ] Clica OK → tabela atualiza com novo nome
   - [ ] Fecha Labirinto e reabre → **nome persistiu** ✓

2. **Adicionar Submenu:**
   - [ ] Seleciona `[5]` (Calendário)
   - [ ] Clica "+ Submenu"
   - [ ] Dialog pede nome
   - [ ] Digita "Aniversários"
   - [ ] Clica OK → aparece em Menu [5]
   - [ ] Fecha e reabre → **submenu persistiu** ✓

3. **Remover Submenu:**
   - [ ] Expande `[5]`
   - [ ] Seleciona o submenu recém-criado "Aniversários"
   - [ ] Clica "Remover"
   - [ ] Pede confirmação
   - [ ] Confirma → desaparece
   - [ ] Fecha e reabre → **remoção persistiu** ✓

---

## 📊 Resumo de Status

| Teste | Status | Notas |
|-------|--------|-------|
| 5 — GUI Principal | ⬜ | |
| 5B — Menu [3] Favoritos | ⬜ | |
| 5C — Menu [5] Calendário | ⬜ | |
| 5D — Menu [10] Listas | ⬜ | |
| 5E — Menu [0] Gravação | ⬜ | |
| 6 — Menu [1] Agregador | ⬜ | |
| Labirinto — Estrutura | ⬜ | |

**Preencha com:**
- ✅ = passou
- ❌ = falhou (anote o erro)
- ⏳ = não testado

---

## 📝 Instruções

Se algum teste falhar:
1. Anote o erro exato
2. Me envie a screenshot (se possível)
3. Continue com os outros testes
4. Depois vou corrigir os bugs

**Comando para abrir:**
```bash
python audiobook_gui.py
```

Boa sorte! 🚀
