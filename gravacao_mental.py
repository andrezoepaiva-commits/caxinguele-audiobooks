"""
Organizações Mentais — Menu 0 do Super Alexa
Gravação livre de voz, classificação automática por IA, redirecionamento para listas.

Fluxo:
1. Usuário fala livremente (Alexa em silêncio total)
2. Diz "Registrar" ao terminar
3. IA classifica cada trecho e sugere destinos
4. Usuário confirma ou redireciona
5. Itens salvos nas listas corretas (Menu 10)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

ARQUIVO_LISTAS = BASE_DIR / "listas_mentais.json"

# Categorias padrão para classificação automática
CATEGORIAS_PADRAO = [
    "Ideias Caxinguelê",
    "Compras",
    "Consultas Médicas",
    "Lembretes Gerais",
    "Tarefas da Semana",
    "Insights Pessoais",
    "Calendário",       # redireciona para Menu 5
]

# Palavras-chave por categoria (classificação simples offline)
KEYWORDS = {
    "Compras": ["comprar", "compre", "mercado", "precisando", "faltou", "acabou"],
    "Consultas Médicas": ["médico", "consulta", "remédio", "exame", "doutor",
                          "dentista", "endocrinologista", "urologista", "cardiologista"],
    "Calendário": ["amanhã", "hoje", "segunda", "terça", "quarta", "quinta",
                   "sexta", "sábado", "domingo", "semana", "hora", "às "],
    "Ideias Caxinguelê": ["caxinguelê", "projeto", "alexa", "amigo", "skill",
                          "app", "sistema", "funcionalidade", "ideia"],
    "Tarefas da Semana": ["preciso", "fazer", "resolver", "ligar", "enviar",
                          "responder", "pagar", "verificar"],
    "Insights Pessoais": ["percebi", "pensei", "refleti", "senti", "aprendi",
                          "descobri", "interessante"],
}


def carregar_listas() -> dict:
    """Carrega todas as listas salvas"""
    if ARQUIVO_LISTAS.exists():
        try:
            return json.loads(ARQUIVO_LISTAS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _criar_listas_padrao()


def salvar_listas(listas: dict):
    """Salva todas as listas em disco"""
    ARQUIVO_LISTAS.write_text(
        json.dumps(listas, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _criar_listas_padrao() -> dict:
    """Cria estrutura inicial de listas"""
    return {
        cat: [] for cat in CATEGORIAS_PADRAO
    }


def classificar_texto(texto: str) -> str:
    """
    Classifica um trecho de texto na categoria mais provável.
    Usa palavras-chave. Retorna nome da categoria.
    """
    texto_lower = texto.lower()
    pontuacao = {}

    for categoria, palavras in KEYWORDS.items():
        pontos = sum(1 for p in palavras if p in texto_lower)
        if pontos > 0:
            pontuacao[categoria] = pontos

    if not pontuacao:
        return "Lembretes Gerais"   # fallback

    return max(pontuacao, key=pontuacao.get)


def segmentar_fala(texto_completo: str) -> list[dict]:
    """
    Divide uma fala longa em itens individuais.
    Cada item tem: texto + categoria sugerida.

    Estratégia: divide por pontuação ou palavras de transição.
    """
    import re

    # Divide por ponto final, vírgula + "e também", "também", "e mais"
    separadores = r'(?<=[.!?])\s+|(?:,?\s+(?:e também|também queria|além disso|e mais)\s+)'
    partes = re.split(separadores, texto_completo, flags=re.IGNORECASE)

    itens = []
    for parte in partes:
        parte = parte.strip()
        if len(parte) < 10:     # ignora fragmentos muito curtos
            continue
        itens.append({
            "id": str(uuid.uuid4())[:8],
            "texto": parte,
            "categoria_sugerida": classificar_texto(parte),
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "audio_original": None,     # path do .wav quando implementado
            "confirmado": False,
        })

    return itens


def salvar_itens_nas_listas(itens: list[dict]):
    """
    Salva cada item na lista correspondente à sua categoria.
    Cria lista nova se a categoria não existir ainda.
    """
    listas = carregar_listas()

    for item in itens:
        cat = item.get("categoria_sugerida", "Lembretes Gerais")
        if cat not in listas:
            listas[cat] = []       # cria lista nova automaticamente
        listas[cat].insert(0, item)    # insere no início (mais recente primeiro)

    salvar_listas(listas)
    return listas


def redirecionar_item(item_id: str, nova_categoria: str) -> bool:
    """
    Move um item de categoria antes de confirmar.
    Retorna True se encontrou e moveu o item.
    """
    listas = carregar_listas()

    # Procura o item em todas as listas
    for cat, itens in listas.items():
        for i, item in enumerate(itens):
            if item.get("id") == item_id:
                # Remove da categoria atual
                listas[cat].pop(i)
                # Cria destino se não existe
                if nova_categoria not in listas:
                    listas[nova_categoria] = []
                # Adiciona na nova categoria
                item["categoria_sugerida"] = nova_categoria
                listas[nova_categoria].insert(0, item)
                salvar_listas(listas)
                return True

    return False


def gerar_confirmacao_alexa(itens: list[dict]) -> str:
    """
    Gera o texto que a Alexa vai falar para confirmar os itens classificados.
    """
    if not itens:
        return "Não entendi nada. Pode repetir?"

    if len(itens) == 1:
        return (
            f"Recebi 1 item. Classificado como '{itens[0]['categoria_sugerida']}'. "
            "Diga 'Confirmar' para salvar, ou 'Redirecionar' para mudar de lista."
        )

    resumo = ", ".join(
        f"{i+1} para {item['categoria_sugerida']}"
        for i, item in enumerate(itens)
    )
    return (
        f"Recebi {len(itens)} itens. {resumo}. "
        "Diga 'Confirmar' para aceitar tudo, "
        "ou diga o número do item que quer redirecionar."
    )


# ─────────────────────── INTERFACE (Painel de Teste Local) ───────────────────

def simular_gravacao(texto: str) -> dict:
    """
    Simula uma gravação completa para testes locais.
    Retorna o resultado como a Lambda receberia.
    """
    itens = segmentar_fala(texto)
    confirmacao = gerar_confirmacao_alexa(itens)

    return {
        "itens": itens,
        "confirmacao_alexa": confirmacao,
        "total": len(itens),
    }


if __name__ == "__main__":
    # Teste rápido
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    texto_teste = (
        "Preciso comprar um liquidificador novo, o meu quebrou. "
        "Também queria anotar uma ideia para o projeto Caxinguelê: "
        "que tal um sistema onde meu amigo escolhe o jornalista favorito? "
        "Me lembrar que tenho consulta médica na quinta às 15h."
    )

    resultado = simular_gravacao(texto_teste)
    print(f"Total de itens: {resultado['total']}")
    for i, item in enumerate(resultado["itens"], 1):
        print(f"  Item {i}: [{item['categoria_sugerida']}] {item['texto'][:60]}...")
    print(f"\nAlexa diria: {resultado['confirmacao_alexa']}")
