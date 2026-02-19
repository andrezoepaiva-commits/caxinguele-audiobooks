"""
Script de diagnóstico: testar extração de texto do PDF
Verifica se o texto extraído está correto e não vazio
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

# ===== TESTE 1: Carregar módulos =====
print("\n" + "="*60)
print("TESTE 1: Verificar dependências")
print("="*60)

try:
    from pdf_processor import processar_pdf
    from config import VOZES_PT_BR, VOZ_PADRAO
    print("✅ Módulos carregados com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

# ===== TESTE 2: Processar PDF =====
print("\n" + "="*60)
print("TESTE 2: Processar TESTE_AUDIOBOOK.pdf")
print("="*60)

pdf_path = Path("TESTE_AUDIOBOOK.pdf")

if not pdf_path.exists():
    print(f"❌ Arquivo não encontrado: {pdf_path}")
    sys.exit(1)

print(f"📄 Arquivo: {pdf_path}")
print(f"📊 Tamanho: {pdf_path.stat().st_size / 1024:.1f} KB")

try:
    livro = processar_pdf(pdf_path)
    print(f"\n✅ PDF processado com sucesso!")
    print(f"📚 Livro: {livro.titulo}")
    print(f"📖 Capítulos detectados: {len(livro.capitulos)}")

except Exception as e:
    print(f"❌ Erro ao processar PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== TESTE 3: Verificar cada capítulo =====
print("\n" + "="*60)
print("TESTE 3: Analisar conteúdo de cada capítulo")
print("="*60)

for cap in livro.capitulos:
    tamanho_texto = len(cap.texto)
    num_palavras = cap.palavras

    print(f"\n📌 Capítulo {cap.numero}: {cap.titulo}")
    print(f"   Caracteres: {tamanho_texto}")
    print(f"   Palavras: {num_palavras}")

    # Mostra primeiros caracteres do texto
    preview = cap.texto[:100].replace('\n', ' ')
    print(f"   Preview: {preview}...")

    # Verifica se o texto é válido
    if tamanho_texto < 100:
        print(f"   ⚠️  AVISO: Texto muito curto!")
    elif num_palavras < 10:
        print(f"   ⚠️  AVISO: Menos de 10 palavras!")
    else:
        print(f"   ✅ Texto parece OK")

# ===== TESTE 4: Testar TTS com cada capítulo =====
print("\n" + "="*60)
print("TESTE 4: Testar TTS com primeiro capítulo")
print("="*60)

if not livro.capitulos:
    print("❌ Nenhum capítulo extraído!")
    sys.exit(1)

cap_teste = livro.capitulos[0]

print(f"\n📌 Testando capítulo: {cap_teste.titulo}")
print(f"   Texto ({cap_teste.palavras} palavras): {cap_teste.texto[:50]}...")

try:
    from tts_engine import converter_texto_para_audio
    from utils import normalizar_nome_arquivo

    arquivo_teste = Path(f"teste_cap_{cap_teste.numero}.mp3")

    print(f"\n⏳ Convertendo para áudio...")
    sucesso = converter_texto_para_audio(
        cap_teste.texto,
        arquivo_teste,
        voz=VOZES_PT_BR[VOZ_PADRAO]
    )

    if sucesso and arquivo_teste.exists():
        tamanho_kb = arquivo_teste.stat().st_size / 1024
        print(f"✅ Áudio gerado com sucesso!")
        print(f"   Arquivo: {arquivo_teste.name}")
        print(f"   Tamanho: {tamanho_kb:.1f} KB")

        # Limpar arquivo de teste
        arquivo_teste.unlink()

    else:
        print(f"❌ Falha ao gerar áudio")
        if arquivo_teste.exists():
            tamanho_kb = arquivo_teste.stat().st_size / 1024
            print(f"   Arquivo criado mas vazio: {tamanho_kb:.1f} KB")
            arquivo_teste.unlink()

except Exception as e:
    print(f"❌ Erro durante TTS: {e}")
    import traceback
    traceback.print_exc()

# ===== RESUMO =====
print("\n" + "="*60)
print("RESUMO")
print("="*60)

print(f"""
Total de capítulos: {len(livro.capitulos)}
Total de palavras: {sum(cap.palavras for cap in livro.capitulos)}

Se todos os testes passaram:
  ✅ A extração de PDF está OK
  ✅ O TTS está funcionando
  → O problema pode estar na integração com a GUI

Se um capítulo tem texto muito curto:
  ⚠️  Pode haver problema na detecção de capítulos
  → Verifique se a estrutura do PDF está correta

Se o TTS falhou:
  ❌ Mesmo com texto válido, pode haver problema de configuração
  → Execute novamente: python testar_tts_direto.py
""")

print("\n✅ Diagnóstico concluído!")
