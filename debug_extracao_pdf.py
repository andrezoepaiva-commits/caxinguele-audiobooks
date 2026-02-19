"""
Debug profundo: analisar cada página do PDF e ver onde está o texto
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import fitz

print("\n" + "="*60)
print("ANÁLISE PROFUNDA: Páginas do PDF")
print("="*60)

pdf_path = Path("TESTE_AUDIOBOOK.pdf")

if not pdf_path.exists():
    print(f"❌ Arquivo não encontrado: {pdf_path}")
    sys.exit(1)

# Abre PDF
pdf_doc = fitz.open(pdf_path)
print(f"\n📄 {pdf_path.name}")
print(f"📊 Total de páginas: {len(pdf_doc)}")

# Analisa cada página
print("\n" + "="*60)
print("CONTEÚDO DE CADA PÁGINA")
print("="*60)

for num_pag in range(len(pdf_doc)):
    pag = pdf_doc[num_pag]
    texto_raw = pag.get_text()
    num_chars = len(texto_raw)
    num_linhas = len(texto_raw.split('\n'))

    print(f"\n[Página {num_pag + 1}/{len(pdf_doc)}]")
    print(f"  Caracteres: {num_chars}")
    print(f"  Linhas: {num_linhas}")

    # Mostra primeiras 200 caracteres
    preview = texto_raw[:200].replace('\n', ' | ')
    print(f"  Preview: {preview}...")

    # Se a página está vazia, avisa
    if num_chars < 50:
        print(f"  ⚠️  PÁGINA VAZIA OU MUITO PEQUENA")

# Agora testa a detecção de capítulos
print("\n" + "="*60)
print("PADRÕES DE DETECÇÃO DE CAPÍTULOS")
print("="*60)

import re

# Padrões que o sistema usa para detectar capítulos
padroes = [
    (r'^Capítulo\s+(\d+|[IVX]+)', 'Capítulo N ou Capítulo I/II/III'),
    (r'^CAPÍTULO\s+(\d+|[IVX]+)', 'CAPÍTULO N (maiúscula)'),
    (r'^\d+\.\s+\w', 'N. Título (numerado)'),
    (r'^Part\w+\s+(\d+|[IVX]+)', 'Part/Parte'),
]

# Coleta todo texto do PDF
texto_completo = ""
for num_pag in range(len(pdf_doc)):
    pag = pdf_doc[num_pag]
    texto_completo += pag.get_text()

# Procura por cada padrão
for padrao, descricao in padroes:
    matches = re.findall(padrao, texto_completo, re.MULTILINE)
    if matches:
        print(f"\n✅ Encontrado padrão: {descricao}")
        print(f"   Matches: {matches}")

# Testa especificamente o padrão usado no código
print("\n" + "="*60)
print("PADRÃO USADO NO pdf_processor.py")
print("="*60)

# Este é o padrão real usado no código
padrao_principal = r'^\d+\.\s+\w'

linhas = texto_completo.split('\n')
capitulos_encontrados = []

for num_linha, linha in enumerate(linhas):
    if re.match(padrao_principal, linha):
        print(f"\n✅ Linha {num_linha}: {linha[:60]}...")
        capitulos_encontrados.append((num_linha, linha))

print(f"\nTotal de capítulos encontrados: {len(capitulos_encontrados)}")

# Mostra intervalo entre capítulos (para entender a extração)
print("\n" + "="*60)
print("INTERVALO DE TEXTO ENTRE CAPÍTULOS")
print("="*60)

for i in range(len(capitulos_encontrados)):
    linha_inicio = capitulos_encontrados[i][0]
    titulo = capitulos_encontrados[i][1]

    # Próximo capítulo (ou fim do arquivo)
    if i < len(capitulos_encontrados) - 1:
        linha_fim = capitulos_encontrados[i + 1][0]
    else:
        linha_fim = len(linhas)

    # Extrai texto entre capítulos
    texto_capitulo = '\n'.join(linhas[linha_inicio:linha_fim])
    num_palavras = len(texto_capitulo.split())

    print(f"\n📌 Capítulo {i + 1}: {titulo[:50]}...")
    print(f"   Linhas: {linha_inicio} até {linha_fim}")
    print(f"   Palavras: {num_palavras}")
    print(f"   Chars: {len(texto_capitulo)}")

    if num_palavras < 50:
        print(f"   ⚠️  MUITO PEQUENO!")
        # Mostra o que está sendo extraído
        print(f"   Conteúdo: {texto_capitulo[:200]}...")

pdf_doc.close()

print("\n" + "="*60)
print("FIM DA ANÁLISE")
print("="*60)
