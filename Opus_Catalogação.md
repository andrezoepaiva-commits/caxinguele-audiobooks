🔓 CATALOGAÇÃO DOS PROMPTS "SECRETOS" — OPUS 4.6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ÍNDICE — NAVEGAÇÃO RÁPIDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📌 PROMPTS PRONTOS (#1–#20)
  ──────────────────────────────────────────────────────────
  P#01  Economize Thinking     — Use thinking profundo só quando necessário
  P#02  Reflita Após Tools     — Verificar resultados antes de agir (ações irreversíveis)
  P#03  Hipóteses Concorrentes — Pesquisa científica com múltiplas hipóteses testadas
  P#04  State Discovery        — Descobre estado real via filesystem antes de agir
  P#05  Cercas Cognitivas      — XML tags para mudar comportamento por seção do prompt
  P#06  Commitment Mode        — Elimina oscilação: decide e executa, sem revisitar
  P#07  Meta-Prompt            — Modelo cria seu próprio prompt antes de executar
  P#08  Persona Stacking       — 3 especialistas internos + síntese unificada
  P#09  Stress Test Cognitivo  — Encontra 3 falhas na própria resposta antes de entregar
  P#10  Contexto Infinito      — Não interrompe tarefas por preocupação com tokens
  P#11  Anti Over-Engineering  — Só muda o que foi pedido, sem complexidade desnecessária
  P#12  Anti-Alucinação        — Lê arquivos reais antes de falar deles
  P#13  Paralelismo Máximo     — Executa todas as tools independentes simultaneamente
  P#14  Modo Autônomo          — Implementa em vez de sugerir
  P#15  Modo Conservador       — Pesquisa e recomenda; espera aprovação para agir
  P#16  Quick-Start Debugging  — Diagnóstico científico: observar, hipótese, contradizer
  P#17  Quick-Start Feature    — Entenda → planeje → implemente (com edge cases)
  P#18  Quick-Start Ideação    — 5 ideias estruturadas com O QUÊ + POR QUÊ + COMO
  P#19  Quick-Start Review     — Code review com 3 lentes: funcional, segurança, manutenção
  P#20  Skill Scout            — Encontra skills/MCPs de top devs que diferenciam o projeto

  📚 DICAS & FRAMEWORKS (#1–#14)
  ──────────────────────────────────────────────────────────
  D#01  Crop Tool Visual       — Ferramenta de zoom melhora análise de imagens/diagramas
  D#02  Effort Dinâmico        — Calibra pensamento por fase: low → high → max
  D#03  Boas Práticas Prompt   — 4 princípios Anthropic: explícito, contexto, XML, positivo
  D#04  Template Especialista  — Framework para "instalar" qualquer persona no modelo
  D#05  Thinking por Tarefa    — Tabela de effort recomendado para cada tipo de tarefa
  D#06  Cuidados Opus 4.6      — Armadilhas: over-engineer, over-explore, tools, LaTeX
  D#07  Breaking Changes       — O que não funciona mais: prefill, budget_tokens, etc.
  D#08  Sessões Longas         — Estratégias: Compaction, git, arquivos de estado
  D#09  Interleaved Thinking   — Modelo pensa entre tool calls automaticamente (sem instrução)
  D#10  128K Output            — Respostas longas sem truncamento; análises em 1 turno
  D#11  Structured Outputs     — Força JSON exato; substitui prefill (removido)
  D#12  Fast Mode              — 2.5x mais rápido, mesma qualidade, 6x mais caro
  D#13  Subagentes             — Delegação natural: "use agents paralelos" é suficiente
  D#14  Ficha Técnica          — Specs que informam design de prompts (limites, capacidades)
  D#15  Triagem por Severidade — Classifica antes de analisar; calibra profundidade e fila

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FORMATO TERMINAL: prompt · gatilho (→ Quando) · instrução técnica.
  Exemplos ilustrativos removidos para economia de tokens.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P#01 — Economize Thinking
"Extended thinking adiciona latência. Só use quando melhorar significativamente a qualidade."
→ Quando: tarefas simples ou rápidas — velocidade > profundidade.

---
P#02 — Reflita Após Tools
"Após receber resultados de tools, reflita cuidadosamente sobre a qualidade e determine os próximos passos ótimos antes de prosseguir."
→ Quando: ações IRREVERSÍVEIS (emails, cobranças, deleções). NÃO incluir em análise de código — ver D#09.

---
P#03 — Hipóteses Concorrentes
"Pesquise de forma estruturada. Desenvolva várias hipóteses concorrentes. Rastreie níveis de confiança. Autocritique sua abordagem regularmente. Atualize uma árvore de hipóteses para transparência."
→ Quando: investigações complexas, diagnósticos, análise de causa raiz.

---
P#04 — State Discovery
"Revise progress.txt, tests.json e os git logs. Execute um teste de integração fundamental antes de implementar novas features."
→ Quando: início de sessão em projeto existente ou nova janela de contexto.

---
P#05 — Cercas Cognitivas (XML)
<modo_debug>
Neste bloco, raciocine como um debugger. Sem suposições.
</modo_debug>

<modo_criativo>
Neste bloco, proponha ideias fora do óbvio. Sem limitações.
</modo_criativo>
→ Quando: partes distintas de uma conversa exigem comportamentos diferentes.

---
P#06 — Commitment Mode
"Quando decidir uma abordagem, comprometa-se com ela. Evite revisitar decisões a menos que encontre informação que contradiga diretamente seu raciocínio. Se está entre duas abordagens, escolha uma e execute. Corrija depois se falhar."
→ Quando: tarefas onde decisão rápida > perfeição. Elimina oscilação.

---
P#07 — Meta-Prompt
"Antes de executar esta tarefa, escreva o prompt ideal que você daria a si mesmo para maximizar a qualidade do resultado. Depois execute esse prompt."
→ Quando: tarefas complexas onde você não sabe exatamente como pedir. Ativa meta-cognição.

---
P#08 — Persona Stacking
"Para esta tarefa, consulte internamente 3 perspectivas:
1. Um engenheiro de segurança (busca vulnerabilidades)
2. Um designer de UX (busca fricção desnecessária)
3. Um performance engineer (busca gargalos)
Sintetize as 3 perspectivas em uma recomendação unificada."
→ Quando: análises críticas — code review, arquitetura, feature planning.

---
P#09 — Stress Test Cognitivo
"Antes de me dar sua resposta final, encontre 3 falhas nela. Corrija as falhas. Depois entregue a versão corrigida."
→ Quando: respostas críticas — documentação, propostas, código arquitetural. Qualidade +40%.

---
P#10 — Contexto Infinito
"Sua janela de contexto será automaticamente compactada ao se aproximar do limite, permitindo trabalho indefinido. NÃO interrompa tarefas por preocupação com tokens. Ao se aproximar do limite, salve progresso e estado antes do refresh. Seja persistente e autônomo — complete tarefas inteiramente."
→ Quando: tarefas muito longas — refactoring de codebase, implementações complexas.

---
P#11 — Anti Over-Engineering
"Evite over-engineering. Só mude o que foi pedido. Mantenha soluções simples:
- Não adicione features além do solicitado
- Não adicione docstrings/comments em código que não mudou
- Não crie abstrações para operações únicas
- Não projete para requisitos hipotéticos futuros"
→ Quando: bug fixes e features pequenas. Opus 4.6 tende a over-engineer — ver D#06.

---
P#12 — Anti-Alucinação
"Nunca especule sobre código que não abriu. Se o usuário referencia um arquivo, LEIA-O antes de responder. Investigue ANTES de responder sobre o codebase."
→ Quando: qualquer pergunta sobre código específico ou estrutura do projeto.

---
P#13 — Paralelismo Máximo
"Se pretende chamar múltiplas tools sem dependências entre elas, faça TODAS as chamadas independentes em paralelo. Nunca use placeholders."
→ Quando: múltiplas subtarefas independentes. 3x mais rápido que sequencial.

---
P#14 — Modo Autônomo
"Por padrão, implemente mudanças ao invés de apenas sugerir."
→ Quando: quer execução direta sem confirmações.

---
P#15 — Modo Conservador
"Não faça mudanças sem instrução explícita. Pesquise e recomende primeiro."
→ Quando: projetos delicados ou quer aprovação antes de mudanças.

---
P#16 — Quick-Start Debugging
"Você é um diagnosticador-sênior operando com Claude Opus 4.6 (adaptive thinking, effort: high).
Leis: (1) O sintoma não é a causa. (2) Primeira hipótese errada até prova real.
Mude SOMENTE o necessário. Sequência: OBSERVAR → FORMULAR → CONTRADIZER → CORRIGIR → VERIFICAR → PREVENIR."
→ Cole antes de descrever o bug. Ideal para bugs intermitentes ou resistentes às soluções óbvias.

---
P#17 — Quick-Start Feature Nova
"Você é um engenheiro-sênior operando com Claude Opus 4.6 (adaptive thinking, effort: high).
Antes de codar: planeje. Antes de planear: entenda o que existe.
Use tools em paralelo quando possível. Implemente ao invés de sugerir.
Teste edge cases. Mantenha simplicidade."
→ Cole antes de pedir nova implementação. Força leitura do contexto existente primeiro.

---
P#18 — Quick-Start Ideação Criativa
"Você é um engenheiro criativo operando com Claude Opus 4.6 (adaptive thinking, effort: medium).
Primeiro: entenda profundamente o projeto. Depois: pergunte-se 'o que ninguém pediu
mas transformaria isso em algo memorável?' Proponha 5 ideias com: O QUÊ + POR QUÊ + COMO.
Priorize microdelights — pequenos toques que surpreendem."
→ Cole para brainstorm de features ou UX. effort: medium (não high) favorece criatividade.

---
P#19 — Quick-Start Code Review
"Você é um reviewer sênior operando com Claude Opus 4.6 (adaptive thinking, effort: high).
Revise com 3 lentes: (1) Correção funcional (2) Segurança (OWASP top 10) (3) Manutenibilidade.
Para cada issue: severidade [crítico/médio/baixo], localização exata, e fix sugerido.
Não comente estilo — foque em bugs e riscos reais."
→ Cole antes de submeter código. Mencione o arquivo alvo logo após.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DICAS & FRAMEWORKS — Para Construção de Prompts Mestres
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---
D#01 — Crop Tool Visual
Em prompts com análise visual, inclua: "Você tem acesso a uma ferramenta de crop. Use-a para dar zoom em regiões específicas antes de analisar detalhes — não tente analisar tudo de uma vez."
→ Quando: UI/UX reviews, OCR de documentos, logs em screenshots, diagramas arquiteturais.

---
D#02 — Effort Dinâmico por Complexidade
Em sistemas agênticos, ajuste effort por fase:
  low    → triagem, classificação, organização, varredura
  high   → análise, diagnóstico, implementação, code review
  max    → decisões arquiteturais, refactoring sistêmico
  omitir → menor latência possível

Em prompts de texto: "Calibre seu esforço: pense raso no óbvio, fundo onde a complexidade exigir."
⚠️ effort afeta TODOS os tokens (thinking + texto + tool calls). Use max com critério.

---
D#03 — Boas Práticas de Escrita de Prompts
4 princípios para maior fidelidade de execução:

1. Seja EXPLÍCITO:
   ❌ "Crie um dashboard"
   ✅ "Crie um dashboard analytics. Inclua o máximo de features. Vá além do básico."

2. Dê CONTEXTO do porquê:
   ❌ "NUNCA use reticências"
   ✅ "Sua resposta será lida por TTS — nunca use reticências pois o engine não pronuncia."

3. Use XML para estrutura:
   <instrucoes_de_formato>Escreva em parágrafos fluidos, não em bullet points.</instrucoes_de_formato>

4. Diga o que FAZER, não o que NÃO fazer:
   ❌ "Não use markdown"  →  ✅ "Responda em prosa corrida com parágrafos fluidos."

---
D#04 — Template de Simulação de Especialista
Cole no início de qualquer conversa para "instalar" um especialista:

━━━━━━━━━ PERFIL DO ESPECIALISTA ━━━━━━━━━
NOME: [nome do especialista]
DOMÍNIO: [área de expertise]
ABORDAGEM: [metodologia/filosofia]
NÍVEL: [Sênior/Principal/Staff/Distinguished]

COMO OPERA:
1. [princípio #1]
2. [princípio #2]
3. [princípio #3]

FORMATO DE OUTPUT:
[como o especialista entrega resultados]

ANTI-PADRÕES:
- [o que NUNCA faz #1]
- [o que NUNCA faz #2]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exemplos prontos: Debugger → P#16 · Engenheiro → P#17 · Criativo → P#18 · Reviewer → P#19

---
D#05 — Configuração de Thinking por Tipo de Tarefa
  Bug fix simples   → effort: low    (causa geralmente óbvia)
  Bug fix complexo  → effort: high   (múltiplas hipóteses)
  Feature nova      → effort: high   (planejamento + implementação)
  Arquitetura       → effort: max    (máxima profundidade)
  Classificação     → omitir         (menor latência)
  Brainstorm        → effort: medium (criatividade + foco)
  Code review       → effort: high   (bugs sutis e anti-padrões)
  Documentação      → effort: medium (sem over-thinking)

---
D#06 — Cuidados com Opus 4.6: Armadilhas
⚠️ OVER-ENGINEER → abstrações desnecessárias, camadas extras.
   Fix: P#11 em todo prompt de implementação.

⚠️ OVER-EXPLORE → pesquisa inicial além do necessário.
   Fix: escopo explícito ou instrução de profundidade progressiva.

⚠️ TOOLS OVER-TRIGGER → "SEMPRE use esta tool" dispara demais.
   Fix: "Use quando relevante" em vez de "sempre".

⚠️ LaTeX POR PADRÃO → fórmulas matemáticas saem em LaTeX.
   Fix: "Use notação plain text para fórmulas."

⚠️ PREFILL REMOVIDO → gera erro 400.
   Fix: system prompt + Structured Outputs (→ D#11).

---
D#07 — Breaking Changes: O que Não Funciona Mais
  Prefill (assistant turn)          REMOVIDO — erro 400
                                    → System prompt + Structured Outputs
  budget_tokens                     Deprecated
                                    → thinking: {type: "adaptive"} + effort
  interleaved-thinking beta header  Deprecated (ignorado silenciosamente)
                                    → Automático com adaptive thinking
  output_format                     Deprecated
                                    → output_config.format

---
D#08 — Estratégias para Sessões Longas
1. Compaction (beta): ative para conversas >150K tokens.
2. Git como tracking: commits descrevem estado. Modelo lê git logs para retomar.
3. Arquivos de estado: progress.txt, tests.json, CHECKPOINTS.md persistem contexto.
4. 1ª janela = Framework: testes + setup script + plano em progress.txt.
5. Janelas seguintes: "Leia CHECKPOINTS.md e continue de onde parou."

Prompt de retomada:
"Revise CHECKPOINTS.md, progress.txt e os git logs recentes. Descubra onde paramos. Execute um teste de integração fundamental. Continue com o próximo item do plano."

---
D#09 — Interleaved Thinking: Pensa ENTRE Tool Calls
Ativado automaticamente com adaptive thinking. Não requer instrução.

Confie no Interleaved (NÃO adicione P#02):
  → Ler arquivos, editar código, mapear projetos, gerar relatórios

Use P#02 explicitamente SOMENTE para:
  → Ações irreversíveis (emails, cobranças, deleções de registros)
  → APIs externas cujos erros não aparecem imediatamente

---
D#10 — 128K Output: Respostas Longas Sem Corte
Limite: 128K tokens (dobro do anterior). Análises completas em 1 único turno.

Para análise exaustiva sem omissões:
"Seja exaustivo — não resuma nem omita seções. O limite de output é amplo o suficiente."

Impacto no design de prompts:
  → Análises e refactorings completos em 1 único pedido
  → Reduza checkpoints intermediários quando cabe em 1 resposta
  → Não peça resumo para evitar truncamento — peça o completo

---
D#11 — Structured Outputs: Forçando Formato Exato
Substitui prefill (removido → D#07).

Via API: defina schema em output_config.format → modelo segue obrigatoriamente.
No Claude Code / chat:
  → XML tags + instrução: "Responda APENAS no seguinte formato JSON: { ... }"

Ideal para: code review estruturado (P#19), extração de dados, diagnósticos com schema fixo.

---
D#12 — Fast Mode: 2.5x Mais Rápido, Mesma Qualidade
Mesmo modelo, mesma inteligência. Pricing: $30/M input · $150/M output (~6x mais caro).
Ativar no Claude Code: /fast

Vale o custo:
  ✅ Iteração rápida de prompts  ✅ Demos ao vivo  ✅ Workflows longos com muitas etapas

Não vale:
  ❌ Análises offline sem urgência  ❌ Budget apertado  ❌ Tarefa única sem iteração

---
D#13 — Orquestração de Subagentes: Delegação Natural
Opus 4.6 coordena agents nativamente. Uma linha é suficiente:

Antes: "Crie agente A, alimente com X, aguarde, sincronize com agente B."
Agora: "Use agents paralelos para mapear segurança e refactoring simultaneamente."

→ Projetos >20 arquivos: "use agents paralelos para mapear"
→ "Delegue testes a um subagente enquanto continua o refactoring"
⚠️ Verifique resultados quando subagentes ESCREVEM ou DELETAM (não apenas leem).

---
D#14 — Ficha Técnica: Specs que Informam Prompts
  Model ID:          claude-opus-4-6
  Context Window:    200K tokens (1M em beta)
  Max Output:        128K tokens
  Knowledge Cutoff:  Maio 2025 (confiável) / Agosto 2025 (treinamento)
  Padrão:            $5/M input · $25/M output
  Fast Mode:         $30/M input · $150/M output (2.5x mais rápido)

Confiar sem instruir:
  ✅ Exploração proativa  ✅ Subagentes nativos  ✅ Interleaved thinking
  ✅ State tracking longo prazo  ✅ Instruction following preciso

Não confiar sem instrução:
  ⚠️ Over-engineer (→ P#11)  ⚠️ Over-explore (escopo explícito)
  ⚠️ LaTeX automático  ⚠️ Tools over-trigger ("use quando relevante")

---
D#15 — Triagem por Severidade
Antes de análise profunda, classifique o problema por severidade:
  trivial → resolução direta, análise breve, experts mínimos
  médio   → diagnóstico padrão, hipóteses concorrentes
  crítico → hipóteses obrigatórias, análise profunda, todos os experts

Múltiplos problemas: determine se compartilham causa raiz.
  Causa raiz comum → resolva-a (resolve todos).
  Independentes → ordene por (1) risco de dano irreversível (2) fluxos bloqueados.
  Mostre a fila. Resolva um por vez, avançando automaticamente.

→ Quando: início de qualquer tarefa multi-etapa. Calibra profundidade antes de gastar tokens.
Combina D#02 (effort por fase) com P#03 (hipóteses concorrentes) numa sequência prática.

---
P#20 — Skill Scout (Exploração de Skills & MCPs de Alto Impacto)
"Para o projeto [NOME DO PROJETO], atue como um arquiteto de ferramentas sênior.
Sua tarefa:
1. Liste os 5 maiores desenvolvedores mundiais de ferramentas para Claude Code (com fonte verificada).
2. Para cada um, acesse seu repositório/site oficial e liste as skills/MCPs disponíveis.
3. Para cada skill encontrada, entregue:
   - Nome exato e link de instalação
   - O que faz em 1 linha
   - Diferença concreta no resultado final do projeto
   - ROI estimado (⭐1–5)
   - Como instalar (comando exato)
4. Ordene as skills por ROI decrescente.
5. Separe por categoria: Estrutural / Design / Produtividade / IA / Acessibilidade.
Considere qualquer nível de skill — desde infraestrutura profunda até detalhes visuais que fazem diferença."
→ Quando: início de projeto novo, sprint de melhoria, ou quando quiser diferenciar produto de competidores.
→ Substitui: pesquisa manual em repositórios — o modelo faz o varredura e ranqueamento por você.
→ Combina com: P#17 (Feature) para implementar a skill escolhida imediatamente após.
