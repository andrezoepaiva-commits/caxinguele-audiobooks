"""
Cria demos de vozes PT-PT (Portugal)
"""

from pathlib import Path
from tts_engine import converter_texto_para_audio

TEXTO_DEMO = """
Olá! Meu nome é {nome_voz}.
Este é um sistema que converte PDFs em audiobooks acessíveis pela Alexa.
Foi criado especialmente para pessoas cegas terem autonomia para ouvir qualquer livro por voz.
O sistema é cem por cento gratuito e funciona com comandos de voz.
Você pode pausar, avançar, voltar, e a Alexa sempre lembra onde você parou.
Esta é uma demonstração da minha voz, com sotaque de Portugal.
Ouça todas as vozes e escolha a que mais te agrada!
"""

pasta_demos = Path("demos_vozes")

# Vozes PT-PT (Portugal)
vozes_portugal = {
    "duarte": ("pt-PT-DuarteNeural", "Duarte - Masculino Portugal"),
    "raquel": ("pt-PT-RaquelNeural", "Raquel - Feminina Portugal"),
}

print("=" * 60)
print("CRIANDO DEMOS DE VOZES DE PORTUGAL")
print("=" * 60)
print()

for nome_curto, (nome_edge, descricao) in vozes_portugal.items():
    print(f"Criando: {descricao}")

    texto = TEXTO_DEMO.format(nome_voz=descricao)
    arquivo_saida = pasta_demos / f"demo_{nome_curto}_portugal.mp3"

    sucesso = converter_texto_para_audio(
        texto=texto,
        arquivo_saida=arquivo_saida,
        voz=nome_edge,
        max_tentativas=3
    )

    if sucesso:
        tamanho = arquivo_saida.stat().st_size / 1024
        print(f"  [OK] {arquivo_saida.name} ({tamanho:.0f} KB)")
    else:
        print(f"  [ERRO] Falhou")
    print()

print("=" * 60)
print("CONCLUIDO!")
print("=" * 60)
