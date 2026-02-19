"""
Cria demos completas e detalhadas apenas com vozes brasileiras
"""

from pathlib import Path
from tts_engine import converter_texto_para_audio

# Texto detalhado explicando o sistema
TEXTO_DEMO_COMPLETO = """
Olá! Meu nome é {nome_voz}.

Este é um sistema especial desenvolvido pelo Andre, especialmente para você.

O sistema se chama PDF para Audiobook, e foi criado para transformar qualquer arquivo PDF em audiobook que você pode ouvir pela Alexa.

Vou explicar passo a passo como funciona e o que você pode fazer:

Primeiro: Como o sistema foi desenvolvido.

O Andre usou tecnologias modernas e gratuitas da Microsoft Azure para criar vozes naturais em português.
O sistema é cem por cento gratuito, não tem custo nenhum para você.
Ele pega um PDF, extrai todo o texto, converte em áudio de alta qualidade, e faz upload automático para o Google Drive.

Segundo: Como você vai usar na Alexa.

Depois que o Andre converter um livro para você, ele vai configurar no aplicativo chamado My Pod.
O My Pod é uma skill gratuita da Alexa que permite ouvir audiobooks pessoais.

Para usar, você vai dizer:
Alexa, abre My Pod.
Depois:
Alexa, toca o nome do livro.

Por exemplo: Alexa, toca Sapiens.

Terceiro: Controles disponíveis por voz.

Você tem controle total usando apenas comandos de voz:

Para pausar, diga: Alexa, pausa.

Para continuar, diga: Alexa, continua.

Para ir ao próximo capítulo, diga: Alexa, próximo.

Para voltar ao capítulo anterior, diga: Alexa, anterior.

Para voltar alguns segundos, diga: Alexa, volta trinta segundos.

Para avançar, diga: Alexa, avança um minuto.

Para aumentar a velocidade, diga: Alexa, aumenta velocidade.

Para diminuir a velocidade, diga: Alexa, diminui velocidade.

Quarto: A Alexa sempre lembra onde você parou.

Esta é uma funcionalidade muito importante: mesmo se você desligar a Alexa, ou ficar dias sem ouvir, quando você voltar, ela retoma exatamente de onde você parou.
Você nunca perde sua posição no livro.

Quinto: Você pode ter vários livros ao mesmo tempo.

O sistema permite ter dezenas de livros diferentes.
Você escolhe qual quer ouvir dizendo o nome.
Cada livro mantém sua posição independente.

Sexto: Escolhendo a voz que você prefere.

O Andre está criando estas demonstrações para você escolher qual voz mais te agrada.
Existem três vozes brasileiras disponíveis: Francisca, que sou eu, feminina e jovem. Antonio, masculina e clara. E Thalita, feminina e suave.

Ouça todas as três demonstrações e escolha uma ou duas que você mais gostar.
Todos os seus livros serão convertidos com a voz que você escolher.

Sétimo: Como pedir novos livros.

Sempre que você quiser ouvir um livro novo, é só pedir ao Andre.
Ele pode converter qualquer PDF: livros, artigos, documentos, apostilas, qualquer coisa em formato PDF.
Em algumas horas, o livro estará pronto para você ouvir na Alexa.

Oitavo: Qualidade e naturalidade.

As vozes que você está ouvindo são criadas por inteligência artificial da Microsoft, chamada Edge TTS.
Elas soam naturais e agradáveis, perfeitas para ouvir por horas sem cansar.

Nono: Autonomia total.

Este sistema foi criado para te dar autonomia completa.
Depois que o Andre configurar pela primeira vez, você usa tudo sozinho, apenas com comandos de voz.
Não precisa mexer em nenhum botão, não precisa de ajuda de ninguém.

Décimo: Resumo e próximos passos.

Este é um sistema poderoso e gratuito que vai te permitir ouvir qualquer livro que você quiser.
O Andre desenvolveu especialmente pensando em você, para que você tenha independência e acesso ao conhecimento.

Agora, escolha qual destas três vozes você mais gostou, e em breve você estará ouvindo seus primeiros livros pela Alexa.

Esta demonstração foi criada com muito carinho pelo Andre.
Aproveite seu novo sistema de audiobooks!
"""

def criar_demos_completas():
    """Cria demos completas apenas com vozes brasileiras"""

    pasta_demos = Path("demos_vozes_completas")
    pasta_demos.mkdir(exist_ok=True)

    print("=" * 70)
    print("CRIANDO DEMOS COMPLETAS - VOZES BRASILEIRAS")
    print("=" * 70)
    print()

    # Apenas vozes brasileiras
    vozes_br = {
        "francisca": ("pt-BR-FranciscaNeural", "Francisca - Feminina Jovem Natural"),
        "antonio": ("pt-BR-AntonioNeural", "Antonio - Masculino Claro"),
        "thalita": ("pt-BR-ThalitaNeural", "Thalita - Feminina Suave"),
    }

    for nome_curto, (nome_edge, descricao) in vozes_br.items():
        print(f"Criando demo completa: {descricao}")
        print(f"  Duração estimada: ~3 minutos")
        print(f"  Conteúdo: Explicação completa do sistema")

        # Personaliza texto com nome da voz
        texto = TEXTO_DEMO_COMPLETO.format(nome_voz=descricao)

        # Nome do arquivo
        arquivo_saida = pasta_demos / f"demo_completa_{nome_curto}.mp3"

        # Converte
        print(f"  Convertendo...")
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
            print(f"  [ERRO] Falha ao criar demo")

        print()

    print("=" * 70)
    print("DEMOS COMPLETAS CRIADAS!")
    print("=" * 70)
    print()
    print(f"Pasta: {pasta_demos.absolute()}")
    print()
    print("Conteúdo de cada demo:")
    print("  1. Apresentação e nome do Andre")
    print("  2. Como o sistema foi desenvolvido")
    print("  3. Como usar na Alexa")
    print("  4. Todos os comandos de voz")
    print("  5. Funcionalidade de memória de posição")
    print("  6. Como ter múltiplos livros")
    print("  7. Como escolher a voz")
    print("  8. Como pedir novos livros")
    print("  9. Qualidade das vozes")
    print(" 10. Autonomia total")
    print()
    print("Próximos passos:")
    print("  1. Escute as 3 demos")
    print("  2. Envie para seu amigo")
    print("  3. Ele escolhe a voz favorita")
    print("  4. Comece a converter livros!")
    print()

if __name__ == '__main__':
    criar_demos_completas()
