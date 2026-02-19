"""
Script para criar demos de vozes para o amigo escolher
"""

import asyncio
from pathlib import Path
from tts_engine import converter_texto_para_audio
from config import VOZES_PT_BR

# Texto de demonstração (explicação do projeto)
TEXTO_DEMO = """
Olá! Meu nome é {nome_voz}.
Este é um sistema que converte PDFs em audiobooks acessíveis pela Alexa.
Foi criado especialmente para pessoas cegas terem autonomia para ouvir qualquer livro por voz.
O sistema é cem por cento gratuito e funciona com comandos de voz.
Você pode pausar, avançar, voltar, e a Alexa sempre lembra onde você parou.
Esta é uma demonstração da minha voz.
Ouça todas as vozes e escolha a que mais te agrada!
"""

def criar_demos():
    """Cria demos de todas as vozes disponíveis"""

    # Pasta para demos
    pasta_demos = Path("demos_vozes")
    pasta_demos.mkdir(exist_ok=True)

    print("=" * 60)
    print("CRIANDO DEMOS DE VOZES")
    print("=" * 60)
    print()

    vozes_info = {
        "francisca": "Francisca - Feminina Jovem Natural",
        "camila": "Camila - Feminina Madura Profissional",
        "antonio": "Antonio - Masculino Claro",
        "thalita": "Thalita - Feminina Suave",
    }

    # Buscar mais vozes PT-BR disponíveis
    print("[INFO] Buscando vozes adicionais...")
    try:
        from tts_engine import listar_vozes_disponiveis
        vozes_extras = listar_vozes_disponiveis("pt-BR")

        # Adiciona mais algumas vozes interessantes
        for voz in vozes_extras:
            nome = voz['nome']
            if nome not in VOZES_PT_BR.values():
                # Adiciona até 2 vozes extras
                if 'Giovanna' in nome:
                    VOZES_PT_BR['giovanna'] = nome
                    vozes_info['giovanna'] = "Giovanna - Feminina"
                elif 'Humberto' in nome:
                    VOZES_PT_BR['humberto'] = nome
                    vozes_info['humberto'] = "Humberto - Masculino"

                if len(VOZES_PT_BR) >= 6:
                    break
    except:
        pass

    print(f"[INFO] Total de vozes: {len(VOZES_PT_BR)}")
    print()

    # Gera demo para cada voz
    for nome_curto, nome_completo in VOZES_PT_BR.items():
        if nome_curto not in vozes_info:
            continue

        print(f"Criando demo: {vozes_info[nome_curto]}")

        # Prepara texto personalizado
        texto = TEXTO_DEMO.format(nome_voz=vozes_info[nome_curto])

        # Nome do arquivo
        arquivo_saida = pasta_demos / f"demo_{nome_curto}.mp3"

        # Converte
        sucesso = converter_texto_para_audio(
            texto=texto,
            arquivo_saida=arquivo_saida,
            voz=nome_completo,
            max_tentativas=3
        )

        if sucesso:
            tamanho = arquivo_saida.stat().st_size / 1024
            print(f"  [OK] {arquivo_saida.name} ({tamanho:.0f} KB)")
        else:
            print(f"  [ERRO] Falha ao criar demo: {nome_curto}")

        print()

    print("=" * 60)
    print("DEMOS CRIADOS!")
    print("=" * 60)
    print()
    print(f"Pasta: {pasta_demos.absolute()}")
    print()
    print("Proximos passos:")
    print("1. Escute os demos")
    print("2. Envie para seu amigo")
    print("3. Ele escolhe 1-2 vozes favoritas")
    print("4. Use essas vozes para converter livros!")
    print()
    print("Comando sugerido:")
    print('  python pipeline_mvp.py --pdf "livro.pdf" --voz francisca')
    print()

if __name__ == '__main__':
    criar_demos()
