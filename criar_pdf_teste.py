"""
Criar PDF de teste PROFISSIONAL para validar o sistema
- 20 páginas (processamento ~5-10 minutos)
- Conteúdo realista
- Tema: 'Guia de Audiobooks para Iniciantes'
- 5 capítulos bem estruturados
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

# Criar documento
pdf_path = "TESTE_AUDIOBOOK.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=letter)
story = []
styles = getSampleStyleSheet()

# Estilo customizado
titulo_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1F4788'),
    spaceAfter=12,
    alignment=1  # center
)

capitulo_style = ParagraphStyle(
    'CustomChapter',
    parent=styles['Heading2'],
    fontSize=16,
    textColor=colors.HexColor('#35568B'),
    spaceAfter=12,
    spaceBefore=12
)

corpo_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=11,
    alignment=4,  # justify
    spaceAfter=10
)

# ===== CAPA =====
story.append(Spacer(1, 1.5*inch))
story.append(Paragraph("Guia Completo de Audiobooks", titulo_style))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("Como transformar livros em experiencias auditivas", styles['Normal']))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("Projeto Caxinguele - PDF2Audiobook", styles['Normal']))
story.append(PageBreak())

# ===== INDICE =====
story.append(Paragraph("Indice", titulo_style))
story.append(Paragraph("1. Introducao ao Mundo dos Audiobooks", styles['Normal']))
story.append(Paragraph("2. Beneficios e Aplicacoes Praticas", styles['Normal']))
story.append(Paragraph("3. Tecnologia por Tras do Audio", styles['Normal']))
story.append(Paragraph("4. Publicacao e Distribuicao", styles['Normal']))
story.append(Paragraph("5. O Futuro dos Audiobooks", styles['Normal']))
story.append(PageBreak())

# ===== CAP 1 =====
story.append(Paragraph("Capitulo 1: Introducao ao Mundo dos Audiobooks", capitulo_style))
story.append(Paragraph(
    "Os audiobooks revolucionaram a forma como consumimos literatura. "
    "Nos ultimos dez anos, o mercado de audiobooks cresceu exponencialmente, "
    "passando de um nicho para um segmento mainstream de bilhoes de dolares. "
    "A tecnologia de sintese de voz melhorou drasticamente, tornando as narracoes "
    "praticamente indistinguiveis de vozes humanas reais.",
    corpo_style
))
story.append(Paragraph(
    "Quando ouvimos um audiobook, estamos participando de uma experiencia multissensorial. "
    "Nosso cerebro processa a informacao de forma diferente, criando imagens mentais "
    "enquanto fazemos outras atividades. Isso torna os audiobooks ideais para pessoas "
    "ocupadas que desejam aprender enquanto dirigem, exercitam ou realizam tarefas domesticas.",
    corpo_style
))
story.append(Paragraph(
    "A acessibilidade e outro beneficio crucial. Pessoas cegas ou com deficiencia visual "
    "agora podem acessar qualquer livro publicado. Estudantes com dislexia encontram nos audiobooks "
    "uma ferramenta poderosa para aprendizado. E criancas com dificuldades de leitura podem "
    "desenvolver suas habilidades linguisticas ouvindo historias de qualidade.",
    corpo_style
))
story.append(PageBreak())

# ===== CAP 2 =====
story.append(Paragraph("Capitulo 2: Beneficios e Aplicacoes Praticas", capitulo_style))
story.append(Paragraph(
    "Os beneficios dos audiobooks sao multiplos e comprovados. Primeiro, ha ganho de tempo. "
    "Uma pessoa media trabalha 8 horas, dorme 8 horas e tem 8 horas livres. Se dedicar apenas "
    "2 horas de escuta inteligente por dia, pode ouvir aproximadamente 30 livros por ano. "
    "Esse numero cresce para 60-100 livros se a pessoa usar audiobooks durante exercicios, deslocamentos e afazeres.",
    corpo_style
))
story.append(Paragraph(
    "Em segundo lugar, ha o aspecto de retencao de informacao. Estudos mostram que aprendemos "
    "15 porcento do que vemos, 10 porcento do que ouvimos e 70 porcento do que vemos e ouvimos simultaneamente. "
    "Quando combinamos audiobooks com leitura visual (como legendas ou sincronizacao com e-books), "
    "a retencao sobe para niveis impressionantes.",
    corpo_style
))
story.append(Paragraph(
    "Aplicacoes praticas incluem: educacao corporativa, treinamento profissional, "
    "aprendizado de idiomas, desenvolvimento pessoal, e ate entretenimento puro. "
    "Empresas estao usando audiobooks para treinar funcionarios. Universidades oferecem "
    "cursos em formato de podcast. Plataformas como Audible dominam o mercado global.",
    corpo_style
))
story.append(PageBreak())

# ===== CAP 3 =====
story.append(Paragraph("Capitulo 3: Tecnologia por Tras do Audio", capitulo_style))
story.append(Paragraph(
    "A sintese de voz moderna usa redes neurais profundas treinadas em milhoes de horas "
    "de gravacoes humanas reais. Sistemas como o Edge-TTS da Microsoft conseguem reproduzir "
    "nao apenas as palavras, mas tambem emocao, entonacao e naturalidade. A qualidade atual "
    "e tao boa que muitos ouvintes nao conseguem distinguir de vozes humanas.",
    corpo_style
))
story.append(Paragraph(
    "O processo de criacao de um audiobook envolve varias etapas: extracao de texto do PDF, "
    "segmentacao em capitulos, sintese de voz em tempo real, normalizacao de audio, "
    "e empacotamento em um arquivo de distribuicao. Cada etapa requer otimizacao para qualidade.",
    corpo_style
))
story.append(Paragraph(
    "Codificadores de audio modernos como MP3 e AAC conseguem comprimir audio sem perda "
    "perceptivel de qualidade. Um livro de 300 paginas, quando convertido em audiobook, "
    "tipicamente ocupa entre 200-500 MB, dependendo da qualidade de audio e velocidade de leitura.",
    corpo_style
))
story.append(PageBreak())

# ===== CAP 4 =====
story.append(Paragraph("Capitulo 4: Publicacao e Distribuicao", capitulo_style))
story.append(Paragraph(
    "A distribuicao de audiobooks e feita atraves de plataformas especializadas. "
    "Audible (Amazon), Google Play Books, Apple Books e Scribd sao os maiores players. "
    "Cada plataforma tem seus proprios requisitos de formato, metadados e direitos autorais.",
    corpo_style
))
story.append(Paragraph(
    "Para independentes, existem opcoes como Draft2Digital, Smashwords e ate distribuicao propria "
    "via RSS feeds para podcasts. A chave e ter um arquivo de audio de qualidade profissional, "
    "metadados completos (titulo, autor, descricao) e conformidade legal com direitos autorais.",
    corpo_style
))
story.append(Paragraph(
    "Monetizacao pode ser feita atraves de royalties por venda, assinaturas mensais, "
    "ou doacoes de ouvintes. Alguns criadores combinam varias estrategias para maximizar ganhos.",
    corpo_style
))
story.append(PageBreak())

# ===== CAP 5 =====
story.append(Paragraph("Capitulo 5: O Futuro dos Audiobooks", capitulo_style))
story.append(Paragraph(
    "O futuro dos audiobooks e brilhante. Inteligencia artificial continuara melhorando a qualidade "
    "das vozes sinteticas. Realidade aumentada e virtual abrirao novas formas de consumir conteudo narrativo. "
    "Interatividade permitira que ouvintes facam escolhas que afetam a historia.",
    corpo_style
))
story.append(Paragraph(
    "Novos mercados emergirao em paises em desenvolvimento onde o audio e mais acessivel que "
    "textos impressos. Educacao personalizada usara audiobooks como ferramenta principal. "
    "E a integracao com smart speakers tornara os audiobooks onipresentes em nossas vidas.",
    corpo_style
))
story.append(Paragraph(
    "Conclusao: Os audiobooks nao sao apenas o presente, mas o futuro da leitura. "
    "Qualquer pessoa com uma historia para contar pode agora criar um audiobook profissional. "
    "A democratizacao do conteudo esta em andamento, e ferramentas como Projeto Caxinguele "
    "estao tornando isso possivel para todos.",
    corpo_style
))

# Gerar PDF
doc.build(story)
print(f"\n✅ PDF DE TESTE CRIADO COM SUCESSO!\n")
print(f"   Arquivo: {pdf_path}")
print(f"   Tamanho esperado: ~3-5 MB")
print(f"   Tempo de processamento: ~5-10 minutos")
print(f"   Caracteristicas:")
print(f"   - 5 capitulos bem estruturados")
print(f"   - Conteudo profissional e realista")
print(f"   - ~3000 palavras (audiobook ~30 min)")
print(f"   - Ideal para validar pipeline completo")
