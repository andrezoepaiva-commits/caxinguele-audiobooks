"""
Script para criar um PDF de exemplo para teste rápido
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

def criar_pdf_teste():
    """Cria um PDF simples para teste"""

    arquivo = Path("exemplo_teste.pdf")

    # Cria PDF
    c = canvas.Canvas(str(arquivo), pagesize=letter)

    # Título
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, 700, "Livro de Teste - PDF2Audiobook")

    # Capítulo 1
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 650, "Capitulo 1: Introducao")

    c.setFont("Helvetica", 12)
    texto1 = """
    Este e um livro de teste para o sistema PDF2Audiobook.
    O sistema converte PDFs em audiobooks para Alexa.
    Foi desenvolvido para ajudar pessoas cegas a terem
    autonomia para ouvir qualquer livro por voz.
    """

    y = 600
    for linha in texto1.strip().split('\n'):
        c.drawString(100, y, linha.strip())
        y -= 20

    # Nova página - Capítulo 2
    c.showPage()

    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 700, "Capitulo 2: Como Funciona")

    c.setFont("Helvetica", 12)
    texto2 = """
    O sistema funciona em tres etapas principais:
    Primeiro, extrai o texto do PDF.
    Segundo, converte o texto em audio usando Edge TTS.
    Terceiro, faz upload para o Google Drive.
    Por fim, voce configura no MyPod para usar na Alexa.
    """

    y = 650
    for linha in texto2.strip().split('\n'):
        c.drawString(100, y, linha.strip())
        y -= 20

    # Salva PDF
    c.save()

    print(f"[OK] PDF de teste criado: {arquivo}")
    print(f"     Tamanho: {arquivo.stat().st_size / 1024:.1f} KB")
    print(f"\nPara testar, execute:")
    print(f"  python pipeline_mvp.py --pdf exemplo_teste.pdf --no-upload")

if __name__ == '__main__':
    # Tenta importar reportlab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        criar_pdf_teste()
    except ImportError:
        print("[ERRO] reportlab nao instalado")
        print("Instale com: pip install reportlab")
        print("\nOu use um PDF que voce ja tem para testar!")
