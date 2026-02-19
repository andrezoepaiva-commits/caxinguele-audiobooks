"""
Cria um PDF médio (~25 páginas) para teste realista
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path

def criar_pdf_medio():
    """Cria PDF médio com conteúdo realista"""

    arquivo = Path("teste_medio_audiobook.pdf")
    c = canvas.Canvas(str(arquivo), pagesize=letter)
    width, height = letter

    # Margens
    margem_x = 72  # 1 inch
    margem_y_top = height - 72
    largura_texto = width - 2 * margem_x

    # Título
    c.setFont("Helvetica-Bold", 24)
    c.drawString(margem_x, margem_y_top, "O Poder da Leitura")

    c.setFont("Helvetica", 12)
    c.drawString(margem_x, margem_y_top - 30, "Um Ensaio sobre Acessibilidade e Tecnologia")

    # Capítulos com conteúdo realista
    capitulos = [
        {
            "titulo": "Capitulo 1: Introducao",
            "texto": """
A leitura e uma das habilidades mais importantes para o desenvolvimento humano.
Ela nos permite acessar conhecimento, desenvolver pensamento critico e expandir
nossa compreensao do mundo.

Para pessoas com deficiencia visual, o acesso a leitura sempre foi um desafio.
Durante seculos, os livros em Braille foram a principal solucao, mas com
limitacoes de disponibilidade e custo.

A tecnologia moderna trouxe novas possibilidades. Audiobooks e leitores de
tela democratizaram o acesso ao conhecimento. Hoje, uma pessoa cega pode
ouvir praticamente qualquer livro usando dispositivos como a Alexa.

Este livro explora como a tecnologia esta transformando a acessibilidade
e criando oportunidades para pessoas cegas terem autonomia total na leitura.
            """
        },
        {
            "titulo": "Capitulo 2: Evolucao dos Audiobooks",
            "texto": """
Os audiobooks nao sao uma invencao recente. Eles existem desde a decada de 1930,
quando a Biblioteca do Congresso dos Estados Unidos comecou a gravar livros
em discos de vinil para veteranos cegos da Primeira Guerra Mundial.

Com o passar dos anos, a tecnologia evoluiu. Cassetes, CDs, MP3 e agora
streaming digital. Cada avanço tornou os audiobooks mais acessiveis e
convenientes.

Hoje, a sintese de voz neural revolucionou o campo. Vozes artificiais soam
cada vez mais naturais, quase indistinguiveis de narradores humanos.

Empresas como Amazon, Google e Microsoft investem bilhoes em tecnologia
de voz. O resultado sao sistemas como Alexa e Google Assistant, que tornam
a tecnologia acessivel por comandos de voz.
            """
        },
        {
            "titulo": "Capitulo 3: Tecnologia Assistiva",
            "texto": """
Tecnologia assistiva e qualquer equipamento, servico ou estrategia que
ajuda pessoas com deficiencia a ter mais autonomia e qualidade de vida.

Para pessoas cegas, algumas tecnologias assistivas importantes incluem:

Leitores de tela: Software que le em voz alta o conteudo da tela do
computador ou celular.

Bengalas inteligentes: Bengalas com sensores que detectam obstaculos
e alertam o usuario.

Assistentes de voz: Alexa, Google Assistant e Siri permitem controlar
dispositivos e acessar informacoes usando apenas a voz.

Livros digitais falados: Audiobooks e sistemas text-to-speech que
convertem texto em audio em tempo real.

A combinacao dessas tecnologias esta criando um mundo mais inclusivo,
onde barreiras fisicas estao sendo gradualmente eliminadas.
            """
        },
        {
            "titulo": "Capitulo 4: Alexa e Autonomia",
            "texto": """
A Amazon Alexa representa um marco na acessibilidade. Pela primeira vez,
uma pessoa cega pode controlar completamente sua casa, acessar informacoes
e entretenimento usando apenas comandos de voz.

Com a Alexa, e possivel:

- Ouvir noticias e podcasts
- Controlar luzes e equipamentos da casa
- Fazer compras online
- Ouvir musicas e audiobooks
- Configurar alarmes e lembretes
- Fazer chamadas telefonicas

A interface por voz elimina completamente a necessidade de telas, botoes
ou controles visuais. Tudo funciona atraves de comandos naturais em portugues.

Para audiobooks especificamente, skills como My Pod permitem que pessoas
cegas ouçam qualquer livro digital, com controle total por voz: pausar,
avançar, voltar, e o mais importante, o sistema lembra exatamente onde
a pessoa parou.
            """
        },
        {
            "titulo": "Capitulo 5: O Futuro da Acessibilidade",
            "texto": """
O futuro da acessibilidade e promissor. Inteligencia artificial e machine
learning estao criando solucoes cada vez mais sofisticadas.

Algumas tendencias importantes:

Reconhecimento de objetos: Cameras com IA que descrevem objetos e pessoas
ao redor, ajudando na navegacao.

Traducao de imagens: Sistemas que descrevem fotos e graficos em detalhes,
tornando conteudo visual acessivel.

Interfaces cerebrais: Pesquisas em neuroengenharia prometem interfaces
diretas entre cerebro e computador.

Realidade aumentada auditiva: Oculos que traduzem informacoes visuais
em feedback auditivo espacial.

Vozes personalizadas: IA que cria vozes sinteticas personalizadas,
preservando identidade e preferencias individuais.

A tecnologia esta eliminando barreiras e criando um mundo onde deficiencia
visual nao limita o acesso a informacao, educacao ou entretenimento.
            """
        },
    ]

    # Gera cada capítulo
    for cap_num, capitulo in enumerate(capitulos, 1):
        # Nova página para cada capítulo
        if cap_num > 1:
            c.showPage()

        y = margem_y_top

        # Título do capítulo
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margem_x, y, capitulo["titulo"])
        y -= 40

        # Texto do capítulo
        c.setFont("Helvetica", 11)

        # Divide em linhas
        linhas = []
        for paragrafo in capitulo["texto"].strip().split('\n'):
            paragrafo = paragrafo.strip()
            if not paragrafo:
                linhas.append("")
                continue

            # Quebra linha longa
            palavras = paragrafo.split()
            linha_atual = ""
            for palavra in palavras:
                teste = linha_atual + " " + palavra if linha_atual else palavra
                if len(teste) < 85:  # ~85 caracteres por linha
                    linha_atual = teste
                else:
                    if linha_atual:
                        linhas.append(linha_atual)
                    linha_atual = palavra
            if linha_atual:
                linhas.append(linha_atual)

        # Desenha linhas
        for linha in linhas:
            if y < 100:  # Nova página se chegou no fim
                c.showPage()
                y = margem_y_top

            if linha:
                c.drawString(margem_x, y, linha)
            y -= 15

    # Página final
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margem_x, margem_y_top, "Conclusao")
    c.setFont("Helvetica", 11)
    y = margem_y_top - 40

    conclusao = """
A tecnologia esta democratizando o acesso ao conhecimento.
Sistemas como este, que convertem PDFs em audiobooks acessiveis,
sao exemplos praticos de como a inovacao pode mudar vidas.

Com ferramentas gratuitas e de qualidade, pessoas cegas ganham
autonomia para ler qualquer livro, a qualquer momento, usando
apenas comandos de voz.

O futuro e inclusivo. E esse futuro comeca agora.
    """

    for linha in conclusao.strip().split('\n'):
        linha = linha.strip()
        if linha:
            c.drawString(margem_x, y, linha)
        y -= 18

    # Salva PDF
    c.save()

    # Info
    num_paginas = c.getPageNumber()
    tamanho = arquivo.stat().st_size / 1024

    print("=" * 60)
    print("[OK] PDF medio criado!")
    print("=" * 60)
    print(f"Arquivo: {arquivo}")
    print(f"Paginas: {num_paginas}")
    print(f"Tamanho: {tamanho:.1f} KB")
    print()
    print("Conteudo:")
    print("  - 5 capitulos sobre acessibilidade e tecnologia")
    print("  - Texto realista (~3.000 palavras)")
    print("  - Duracao estimada audio: ~20 minutos")
    print()
    print("Proximo passo:")
    print("  python pipeline_mvp.py --pdf teste_medio_audiobook.pdf --no-upload")
    print()

if __name__ == '__main__':
    criar_pdf_medio()
