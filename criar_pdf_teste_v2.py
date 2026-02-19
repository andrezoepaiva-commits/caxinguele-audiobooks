"""
Criar PDF de teste MELHORADO - com formatação robusta para detecção de capítulos
- Sem capa/índice nas primeiras páginas
- Cada capítulo começa com "CAPÍTULO N:" (fácil de detectar)
- 5 capítulos bem estruturados
- Tempo de processamento: ~5-10 minutos
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    from reportlab.lib import colors
except ImportError:
    print("❌ reportlab não instalado")
    print("   Instale com: pip install reportlab")
    sys.exit(1)

# Conteúdo dos capítulos (texto realista)
capitulos_conteudo = [
    {
        "numero": 1,
        "titulo": "Introdução ao Mundo dos Audiobooks",
        "texto": """Os audiobooks revolucionaram a forma como consumimos literatura. Nos últimos dez anos, o mercado de audiobooks cresceu exponencialmente, passando de um nicho para um segmento mainstream de bilhões de dólares. A tecnologia de síntese de voz melhorou drasticamente, tornando as narrações praticamente indistinguíveis de vozes humanas reais.

Quando ouvimos um audiobook, estamos participando de uma experiência multissensorial. Nosso cérebro processa a informação de forma diferente, criando imagens mentais enquanto fazemos outras atividades. Isso torna os audiobooks ideais para pessoas ocupadas que desejam aprender enquanto dirigem, exercitam ou realizam tarefas domésticas.

A acessibilidade é outro benefício crucial. Pessoas cegas ou com deficiência visual agora podem acessar qualquer livro publicado. Estudantes com dislexia encontram nos audiobooks uma ferramenta poderosa para aprendizado. E crianças com dificuldades de leitura podem desenvolver suas habilidades linguísticas ouvindo histórias de qualidade."""
    },
    {
        "numero": 2,
        "titulo": "Benefícios e Aplicações Práticas",
        "texto": """Os benefícios dos audiobooks são múltiplos e comprovados. Primeiro, há ganho de tempo. Uma pessoa média trabalha 8 horas, dorme 8 horas e tem 8 horas livres. Se dedicar apenas 2 horas de escuta inteligente por dia, pode ouvir aproximadamente 30 livros por ano. Esse número cresce para 60-100 livros se a pessoa usar audiobooks durante exercícios, deslocamentos e afazeres.

Em segundo lugar, há o aspecto de retenção de informação. Estudos mostram que aprendemos 15 por cento do que vemos, 10 por cento do que ouvimos e 70 por cento do que vemos e ouvimos simultaneamente. Quando combinamos audiobooks com leitura visual, a retenção sobe para níveis impressionantes.

Aplicações práticas incluem educação corporativa, treinamento profissional, aprendizado de idiomas, desenvolvimento pessoal, e até entretenimento puro. Empresas estão usando audiobooks para treinar funcionários. Universidades oferecem cursos em formato de podcast. Plataformas como Audible dominam o mercado global."""
    },
    {
        "numero": 3,
        "titulo": "Tecnologia por Trás do Áudio",
        "texto": """A síntese de voz moderna usa redes neurais profundas treinadas em milhões de horas de gravações humanas reais. Sistemas como o Edge-TTS da Microsoft conseguem reproduzir não apenas as palavras, mas também emoção, entonação e naturalidade. A qualidade atual é tão boa que muitos ouvintes não conseguem distinguir de vozes humanas.

O processo de criação de um audiobook envolve várias etapas: extração de texto do PDF, segmentação em capítulos, síntese de voz em tempo real, normalização de áudio, e empacotamento em um arquivo de distribuição. Cada etapa requer otimização para qualidade.

Codificadores de áudio modernos como MP3 e AAC conseguem comprimir áudio sem perda perceptível de qualidade. Um livro de 300 páginas, quando convertido em audiobook, tipicamente ocupa entre 200-500 MB, dependendo da qualidade de áudio e velocidade de leitura."""
    },
    {
        "numero": 4,
        "titulo": "Publicação e Distribuição",
        "texto": """A distribuição de audiobooks é feita através de plataformas especializadas. Audible (Amazon), Google Play Books, Apple Books e Scribd são os maiores players. Cada plataforma tem seus próprios requisitos de formato, metadados e direitos autorais.

Para independentes, existem opções como Draft2Digital, Smashwords e até distribuição própria via RSS feeds para podcasts. A chave é ter um arquivo de áudio de qualidade profissional, metadados completos (título, autor, descrição) e conformidade legal com direitos autorais.

Monetização pode ser feita através de royalties por venda, assinaturas mensais, ou doações de ouvintes. Alguns criadores combinam várias estratégias para maximizar ganhos. A publicação em múltiplas plataformas garante máximo alcance do audiobook."""
    },
    {
        "numero": 5,
        "titulo": "O Futuro dos Audiobooks",
        "texto": """O futuro dos audiobooks é brilhante. Inteligência artificial continuará melhorando a qualidade das vozes sintéticas. Realidade aumentada e virtual abrirão novas formas de consumir conteúdo narrativo. Interatividade permitirá que ouvintes façam escolhas que afetam a história.

Novos mercados emergirão em países em desenvolvimento onde o áudio é mais acessível que textos impressos. Educação personalizada usará audiobooks como ferramenta principal. E a integração com smart speakers tornará os audiobooks onipresentes em nossas vidas.

Conclusão: Os audiobooks não são apenas o presente, mas o futuro da leitura. Qualquer pessoa com uma história para contar pode agora criar um audiobook profissional. A democratização do conteúdo está em andamento, e ferramentas como Projeto Caxinguele estão tornando isso possível para todos."""
    }
]

# Criar documento
pdf_path = "TESTE_AUDIOBOOK.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
story = []
styles = getSampleStyleSheet()

# Estilos customizados
titulo_estilo = ParagraphStyle(
    'TituloCustom',
    parent=styles['Heading1'],
    fontSize=20,
    textColor=colors.HexColor('#1F4788'),
    spaceAfter=18,
    spaceBefore=6,
    alignment=0
)

corpo_estilo = ParagraphStyle(
    'CorpoCustom',
    parent=styles['BodyText'],
    fontSize=11,
    alignment=4,  # Justificado
    spaceAfter=12,
    leading=14
)

# Adicionar cada capítulo
for cap in capitulos_conteudo:
    # Título do capítulo (padrão forte para detecção)
    titulo = f"CAPÍTULO {cap['numero']}: {cap['titulo']}"
    story.append(Paragraph(titulo, titulo_estilo))

    # Corpo do texto
    story.append(Paragraph(cap['texto'], corpo_estilo))

    # Quebra de página
    story.append(PageBreak())

# Gerar PDF
try:
    doc.build(story)
    print(f"\n✅ PDF DE TESTE CRIADO COM SUCESSO!\n")
    print(f"   Arquivo: {pdf_path}")
    print(f"   Tamanho: {len(open(pdf_path, 'rb').read()) / 1024:.1f} KB")
    print(f"\n   ✅ Características:")
    print(f"      - 5 capítulos bem estruturados")
    print(f"      - Padrão: CAPÍTULO N: Título (fácil de detectar)")
    print(f"      - ~3000 palavras (audiobook ~30 min)")
    print(f"      - Ideal para validar pipeline completo")
    print(f"\n   ⏱️  Tempo de processamento esperado: 5-10 minutos\n")

except Exception as e:
    print(f"❌ Erro ao gerar PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
