"""
Script de diagnóstico: testar Edge-TTS diretamente
Identifica se o problema é de rede, timeout, ou configuração
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import asyncio
import logging
from pathlib import Path
import time

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

# ===== TESTE 1: Importar edge_tts =====
print("\n" + "="*60)
print("TESTE 1: Verificar se edge_tts está instalado")
print("="*60)

try:
    import edge_tts
    print(f"✅ edge_tts importado com sucesso")
    print(f"   Versão: {edge_tts.__version__ if hasattr(edge_tts, '__version__') else 'desconhecida'}")
except ImportError as e:
    print(f"❌ ERRO ao importar edge_tts: {e}")
    print(f"   Instale com: pip install edge-tts")
    sys.exit(1)

# ===== TESTE 2: Listar vozes =====
print("\n" + "="*60)
print("TESTE 2: Listar vozes disponíveis (verificar conectividade)")
print("="*60)

async def listar_vozes():
    try:
        vozes = await edge_tts.list_voices()
        print(f"✅ Conexão OK - {len(vozes)} vozes encontradas")

        # Mostra vozes português
        vozes_pt = [v for v in vozes if v['Locale'].startswith('pt-BR')]
        print(f"\n   Vozes em português brasileiro ({len(vozes_pt)}):")
        for v in vozes_pt:
            print(f"     - {v['ShortName']}: {v['Gender']}")

        return True
    except Exception as e:
        print(f"❌ ERRO ao listar vozes: {e}")
        return False

sucesso_vozes = asyncio.run(listar_vozes())
if not sucesso_vozes:
    print("\n⚠️  Problema de rede ou conectividade detectado!")
    sys.exit(1)

# ===== TESTE 3: Converter texto simples =====
print("\n" + "="*60)
print("TESTE 3: Converter um texto SIMPLES em áudio")
print("="*60)

async def testar_conversao_simples():
    """Testa conversão com texto mínimo"""
    texto = "Olá, este é um teste de texto para fala."
    voz = "pt-BR-FranciscaNeural"
    arquivo = Path("teste_simples.mp3")

    try:
        print(f"\nTexto: '{texto}'")
        print(f"Voz: {voz}")
        print(f"Arquivo: {arquivo}")

        # Remove arquivo antigo se existir
        if arquivo.exists():
            arquivo.unlink()

        # Cria comunicator
        print("\n[Etapa 1] Criando comunicator...")
        communicate = edge_tts.Communicate(texto, voz)
        print(f"  ✅ Comunicator criado")

        # Salva áudio
        print(f"\n[Etapa 2] Gerando áudio (salvando em {arquivo})...")
        inicio = time.time()
        await communicate.save(str(arquivo))
        tempo_decorrido = time.time() - inicio

        print(f"  ✅ Áudio salvo em {tempo_decorrido:.1f}s")

        # Verifica tamanho
        if arquivo.exists():
            tamanho = arquivo.stat().st_size
            print(f"\n[Resultado]")
            print(f"  📁 Arquivo criado: {arquivo.exists()}")
            print(f"  📊 Tamanho: {tamanho} bytes ({tamanho/1024:.1f} KB)")

            if tamanho > 1000:
                print(f"  ✅ SUCESSO - Arquivo válido!")
                return True
            else:
                print(f"  ❌ ERRO - Arquivo vazio/muito pequeno")
                return False
        else:
            print(f"  ❌ ERRO - Arquivo não foi criado!")
            return False

    except Exception as e:
        print(f"  ❌ EXCEÇÃO durante conversão: {e}")
        import traceback
        traceback.print_exc()
        return False

sucesso_simples = asyncio.run(testar_conversao_simples())

# ===== TESTE 4: Testar com ThreadPoolExecutor (como faz o sistema) =====
print("\n" + "="*60)
print("TESTE 4: Converter DENTRO de ThreadPoolExecutor (como usa no sistema)")
print("="*60)

def converter_em_thread():
    """Simula o que tts_engine.py faz: asyncio.run() dentro de uma thread"""

    async def _converter():
        texto = "Teste de conversão dentro de uma thread do executor."
        voz = "pt-BR-FranciscaNeural"
        arquivo = Path("teste_thread.mp3")

        if arquivo.exists():
            arquivo.unlink()

        print(f"  [Thread] Convertendo: {texto[:50]}...")

        try:
            communicate = edge_tts.Communicate(texto, voz)
            await communicate.save(str(arquivo))

            if arquivo.exists():
                tamanho = arquivo.stat().st_size
                print(f"  [Thread] ✅ Arquivo criado: {tamanho} bytes")
                return tamanho > 1000
            else:
                print(f"  [Thread] ❌ Arquivo não criado")
                return False

        except Exception as e:
            print(f"  [Thread] ❌ ERRO: {e}")
            return False

    # Executa asyncio.run() como faz tts_engine.py
    return asyncio.run(_converter())

from concurrent.futures import ThreadPoolExecutor

try:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(converter_em_thread)
        resultado = future.result(timeout=30)

        if resultado:
            print(f"  ✅ SUCESSO - Conversão em thread funcionou!")
        else:
            print(f"  ❌ FALHA - Conversão em thread não funcionou!")

except Exception as e:
    print(f"❌ ERRO ao usar ThreadPoolExecutor: {e}")
    import traceback
    traceback.print_exc()

# ===== RESUMO =====
print("\n" + "="*60)
print("RESUMO DO DIAGNÓSTICO")
print("="*60)

print(f"""
✅ Testes completados!

Se TODOS os testes passaram:
  → O problema NÃO é o Edge-TTS
  → Pode ser: texto vazio, voz inválida, ou erro antes de chamar TTS

Se o TESTE 4 falhou:
  → PROBLEMA IDENTIFICADO: asyncio.run() em ThreadPoolExecutor
  → Solução: usar AsyncioExecutor ao invés de ThreadPoolExecutor

Se o TESTE 3 falhou:
  → PROBLEMA: Edge-TTS não consegue conectar ou converter
  → Verifique: internet, firewall, rate limiting do Azure

Próximo passo:
  1. Verifique os resultados acima
  2. Se há problemas, envie este output para diagnóstico
  3. Depois podemos corrigir o tts_engine.py
""")

# Limpar testes
for f in [Path("teste_simples.mp3"), Path("teste_thread.mp3")]:
    if f.exists():
        f.unlink()

print("\n✅ Script de diagnóstico finalizado!")
