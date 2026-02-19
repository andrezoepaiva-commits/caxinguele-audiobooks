"""
Script para testar vozes disponíveis do Edge-TTS
"""

import asyncio
from tts_engine import listar_vozes_disponiveis
from config import VOZES_PT_BR

print("=" * 60)
print("VOZES CONFIGURADAS NO SISTEMA:")
print("=" * 60)

for nome_curto, nome_completo in VOZES_PT_BR.items():
    print(f"  {nome_curto:12} -> {nome_completo}")

print("\n" + "=" * 60)
print("TESTANDO CONEXAO COM EDGE-TTS...")
print("=" * 60)

try:
    vozes = listar_vozes_disponiveis("pt")
    print(f"\n[OK] Conexao Edge-TTS funcionando!")
    print(f"Total de vozes PT encontradas: {len(vozes)}")
    print("\nPrimeiras 5 vozes:")
    for voz in vozes[:5]:
        print(f"  - {voz['nome']} ({voz['genero']})")
except Exception as e:
    print(f"\n[ERRO] Falha ao conectar Edge-TTS: {e}")
    print("Verifique sua conexao com internet")

print("\n" + "=" * 60)
