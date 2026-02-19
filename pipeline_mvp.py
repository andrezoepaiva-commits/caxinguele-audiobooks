"""
Pipeline MVP - Documento para Audiobook Alexa
Orquestrador principal do sistema

Suporta: PDF, DOCX, EPUB, TXT, HTML, Email, Imagens e mais

Uso:
    python pipeline_mvp.py --arquivo "caminho/para/livro.pdf"
    python pipeline_mvp.py --arquivo "livro.epub" --voz francisca
    python pipeline_mvp.py --arquivo "documento.docx" --no-upload
    python pipeline_mvp.py --pdf "livro.pdf"  (compatibilidade)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Importa módulos do sistema
from config import (
    VOZES_PT_BR, VOZ_PADRAO, OUTPUT_DIR, MESSAGES,
    LOG_CONFIG, ENABLE_CHECKPOINTS, CHECKPOINT_FILE,
    NOTIFY_ON_COMPLETE, MYPOD_CONFIG
)
from utils import (
    setup_logging, validar_pdf, normalizar_nome_arquivo,
    EstimadorTempo, formatar_tempo, salvar_checkpoint,
    carregar_checkpoint, limpar_checkpoint, notificar_conclusao
)
from pdf_processor import processar_pdf, dividir_capitulo_em_chunks
from doc_processor import processar_documento, formato_suportado
from doc_classifier import classificar_documento, TipoDocumento
from tts_engine import processar_capitulos_paralelo, estimar_duracao_audio
from cloud_uploader import upload_audiobook, gerar_instrucoes_mypod


# ==================== ARGUMENTOS CLI ====================

def parse_args():
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description='Converte documentos em audiobook para Alexa',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --arquivo "Sapiens.pdf"
  %(prog)s --arquivo "livro.epub" --voz camila
  %(prog)s --arquivo "documento.docx" --no-upload
  %(prog)s --pdf "livro.pdf"  (compatibilidade)

Formatos suportados:
  PDF, DOCX, RTF, ODT, TXT, MD, EPUB, MOBI,
  EML, MSG, HTML, JPG, PNG (OCR)

Vozes disponíveis:
  francisca - Feminina, jovem, natural (padrão)
  camila    - Feminina, madura, profissional
  antonio   - Masculino, claro
  thalita   - Feminina, suave
        """
    )

    parser.add_argument(
        '--arquivo',
        type=str,
        default=None,
        help='Caminho do documento (qualquer formato suportado)'
    )

    parser.add_argument(
        '--pdf',
        type=str,
        default=None,
        help='Caminho do arquivo PDF (compatibilidade — use --arquivo)'
    )

    parser.add_argument(
        '--voz',
        type=str,
        default='francisca',
        choices=list(VOZES_PT_BR.keys()),
        help='Voz para TTS (padrão: francisca)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Pasta de saída (padrão: audiobooks/)'
    )

    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Não fazer upload para Google Drive'
    )

    parser.add_argument(
        '--no-ocr',
        action='store_true',
        help='Desabilitar OCR automático'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Modo verbose (mais logs)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Retomar processamento do checkpoint'
    )

    args = parser.parse_args()

    # Valida que pelo menos um arquivo foi informado
    if not args.arquivo and not args.pdf:
        parser.error("Informe --arquivo ou --pdf")

    return args


# ==================== PIPELINE PRINCIPAL ====================

def executar_pipeline(args):
    """
    Executa pipeline completo: PDF → Texto → Áudio → Upload

    Args:
        args: Argumentos parseados do CLI

    Returns:
        True se sucesso, False se falhou
    """
    inicio_total = time.time()

    # ──────────────────────────────────────────────────────────
    # ETAPA 0: VERIFICAÇÃO DE CHECKPOINT
    # ──────────────────────────────────────────────────────────

    checkpoint = None
    if args.resume and ENABLE_CHECKPOINTS:
        checkpoint = carregar_checkpoint(CHECKPOINT_FILE)
        if checkpoint:
            logging.info("📦 Checkpoint encontrado! Retomando de onde parou...")
            logging.info(f"   Etapa: {checkpoint.get('etapa_atual', 'desconhecida')}")
            logging.info(f"   Progresso: {checkpoint.get('progresso_percentual', 0)}%")
        else:
            logging.warning("Checkpoint não encontrado, começando do zero")

    # ──────────────────────────────────────────────────────────
    # ETAPA 1: VALIDAÇÃO DO PDF
    # ──────────────────────────────────────────────────────────

    logging.info("=" * 60)
    logging.info("ETAPA 1/5: Validação do Documento")
    logging.info("=" * 60)

    # Suporta --arquivo e --pdf (compatibilidade)
    caminho_arquivo = args.arquivo or args.pdf
    if not caminho_arquivo:
        logging.error("Nenhum arquivo especificado. Use --arquivo ou --pdf")
        return False

    caminho_doc = Path(caminho_arquivo)

    # Valida existência
    if not caminho_doc.exists():
        logging.error(f"Arquivo não encontrado: {caminho_doc}")
        return False

    # Valida formato
    if not formato_suportado(caminho_doc):
        logging.error(f"Formato não suportado: {caminho_doc.suffix}")
        return False

    tamanho_mb = caminho_doc.stat().st_size / (1024 * 1024)
    logging.info(f"Arquivo válido: {caminho_doc.name} ({tamanho_mb:.1f} MB)")

    # ──────────────────────────────────────────────────────────
    # ETAPA 2: PROCESSAMENTO DO DOCUMENTO
    # ──────────────────────────────────────────────────────────

    logging.info("")
    logging.info("=" * 60)
    logging.info("ETAPA 2/5: Processamento do Documento")
    logging.info("=" * 60)

    # Verifica se pode pular (checkpoint)
    livro = None
    classificacao = None  # Resultado da detecção de tipo
    if checkpoint and checkpoint.get('etapa_concluida') >= 2:
        logging.info("Etapa já concluída (checkpoint), pulando...")
        logging.warning("AVISO: --resume não salva objeto Livro no checkpoint")
        logging.warning("       Por segurança, reprocessando do zero...")
        checkpoint = None  # Força reprocessamento

    if not checkpoint or checkpoint.get('etapa_concluida') < 2:
        try:
            # Desabilita OCR se solicitado
            if args.no_ocr:
                from config import PDF_CONFIG
                PDF_CONFIG['auto_ocr'] = False
                logging.info("OCR automático desabilitado")

            # Usa processador multi-formato
            livro = processar_documento(caminho_doc)

            # Classifica tipo do documento
            texto_amostra = ""
            if livro.capitulos:
                texto_amostra = livro.capitulos[0].texto[:2000]
            classificacao = classificar_documento(caminho_doc, texto_amostra, livro.num_paginas)
            logging.info(f"Tipo detectado: {classificacao}")

            # Salva checkpoint
            if ENABLE_CHECKPOINTS:
                salvar_checkpoint(CHECKPOINT_FILE, {
                    'etapa_atual': 'Processamento Documento',
                    'etapa_concluida': 2,
                    'progresso_percentual': 40,
                    'doc_path': str(caminho_doc),
                    'num_capitulos': len(livro.capitulos),
                    'tipo_documento': classificacao.tipo,
                })

        except Exception as e:
            logging.error(f"Erro ao processar documento: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # ETAPA 3: PREPARAÇÃO DOS CAPÍTULOS
    # ──────────────────────────────────────────────────────────

    logging.info("")
    logging.info("=" * 60)
    logging.info("ETAPA 3/5: Preparação dos Capítulos")
    logging.info("=" * 60)

    # Divide capítulos longos em chunks
    capitulos_para_tts = []

    for capitulo in livro.capitulos:
        chunks = dividir_capitulo_em_chunks(capitulo)

        for titulo_chunk, texto_chunk in chunks:
            capitulos_para_tts.append((
                len(capitulos_para_tts) + 1,  # Número sequencial
                titulo_chunk,
                texto_chunk
            ))

    logging.info(f"✅ Total de arquivos de áudio a gerar: {len(capitulos_para_tts)}")

    # Estimativa de duração
    total_palavras = sum(len(texto.split()) for _, _, texto in capitulos_para_tts)
    duracao_estimada = estimar_duracao_audio(total_palavras)
    logging.info(f"📊 Total de palavras: {total_palavras:,}")
    logging.info(f"⏱️  Duração estimada do audiobook: {duracao_estimada}")

    # ──────────────────────────────────────────────────────────
    # ETAPA 4: CONVERSÃO TTS (TEXTO → ÁUDIO)
    # ──────────────────────────────────────────────────────────

    logging.info("")
    logging.info("=" * 60)
    logging.info("ETAPA 4/5: Conversão TTS (Texto → Áudio)")
    logging.info("=" * 60)

    # Define pasta de saída
    if args.output:
        pasta_saida = Path(args.output)
    else:
        # Cria pasta com nome do livro
        nome_normalizado = normalizar_nome_arquivo(livro.titulo)
        pasta_saida = OUTPUT_DIR / nome_normalizado

    pasta_saida.mkdir(parents=True, exist_ok=True)
    logging.info(f"📁 Pasta de saída: {pasta_saida}")

    # Obtém voz
    nome_voz_edge = VOZES_PT_BR[args.voz]
    logging.info(f"🎙️  Voz selecionada: {args.voz} ({nome_voz_edge})")

    # Verifica se pode pular (checkpoint)
    arquivos_audio = []
    if checkpoint and checkpoint.get('etapa_concluida') >= 4:
        logging.info("⏩ Etapa já concluída (checkpoint), pulando...")
        # Carrega lista de arquivos do checkpoint
    else:
        try:
            # Processa capítulos em paralelo
            arquivos_audio = processar_capitulos_paralelo(
                capitulos=capitulos_para_tts,
                pasta_saida=pasta_saida,
                nome_livro=livro.titulo,
                voz=nome_voz_edge,
                usar_fallback=True
            )

            # Verifica quantos falharam
            falhas = sum(1 for a in arquivos_audio if a is None)
            if falhas > 0:
                logging.warning(f"⚠️  {falhas} capítulos falharam na conversão")

                # Decide se continua ou para
                if falhas > len(arquivos_audio) * 0.3:  # Mais de 30% falhou
                    logging.error("❌ Muitas falhas na conversão. Abortando...")
                    return False

            # Remove None da lista
            arquivos_audio = [a for a in arquivos_audio if a is not None]

            # Salva checkpoint
            if ENABLE_CHECKPOINTS:
                salvar_checkpoint(CHECKPOINT_FILE, {
                    'etapa_atual': 'Conversão TTS',
                    'etapa_concluida': 4,
                    'progresso_percentual': 80,
                    'pasta_saida': str(pasta_saida),
                    'num_arquivos': len(arquivos_audio)
                })

        except Exception as e:
            logging.error(f"❌ Erro na conversão TTS: {e}")
            return False

    logging.info(f"✅ {len(arquivos_audio)} arquivos de áudio gerados!")

    # ──────────────────────────────────────────────────────────
    # ETAPA 5: UPLOAD GOOGLE DRIVE (OPCIONAL)
    # ──────────────────────────────────────────────────────────

    if not args.no_upload:
        logging.info("")
        logging.info("=" * 60)
        logging.info("ETAPA 5/5: Upload para Google Drive")
        logging.info("=" * 60)

        # Verifica se Google Drive está configurado
        from config import GDRIVE_CONFIG
        if not GDRIVE_CONFIG['credentials_file'].exists():
            logging.warning("=" * 60)
            logging.warning("Google Drive NAO configurado!")
            logging.warning("=" * 60)
            logging.warning("Opcoes:")
            logging.warning("  1. Configure Google Drive (veja README.md)")
            logging.warning("  2. Use --no-upload para gerar apenas arquivos locais")
            logging.warning("")
            logging.warning("Arquivos locais disponiveis em:")
            logging.warning(f"  {pasta_saida}")
            logging.warning("=" * 60)
        else:
            try:
                # Detecta categoria para organizar no Drive
                categoria_drive = None
                if classificacao:
                    categoria_drive = classificacao.pasta_drive

                resultados_upload = upload_audiobook(
                    arquivos=arquivos_audio,
                    nome_livro=livro.titulo,
                    criar_pasta_livro=True,
                    categoria=categoria_drive
                )

                if not resultados_upload:
                    logging.warning("Upload falhou. Arquivos locais disponíveis em:")
                    logging.warning(f"   {pasta_saida}")
                else:
                    logging.info(f"[OK] {len(resultados_upload)} arquivos enviados para Google Drive")

                    # Gera RSS e publica no GitHub automaticamente
                    try:
                        from rss_generator import gerar_rss_livro
                        from github_uploader import publicar_rss
                        from config import GITHUB_CONFIG

                        logging.info("Gerando RSS e publicando no Spotify...")

                        # Gera imagem de capa se nao existir
                        capa_path = pasta_saida.parent.parent / "capa_podcast.jpg"
                        if not capa_path.exists():
                            capa_path = Path(__file__).parent / "capa_podcast.jpg"

                        # Gera o XML do RSS (com categoria para filtro)
                        arquivo_rss = gerar_rss_livro(
                            resultados_upload,
                            livro.titulo,
                            pasta_saida,
                            categoria=categoria_drive or ""
                        )
                        logging.info(f"[OK] RSS gerado: {arquivo_rss.name}")

                        # Sobe para GitHub (atualiza automaticamente)
                        url_rss = publicar_rss(
                            arquivo_rss,
                            capa_path if capa_path.exists() else None
                        )
                        logging.info(f"[OK] RSS publicado: {url_rss}")
                        logging.info(f"[OK] Amazon Music vai atualizar automaticamente")

                        # Gera indice.json para a Custom Skill Alexa
                        try:
                            from indice_generator import adicionar_ao_indice
                            arquivo_indice = pasta_saida.parent / "indice.json"
                            for resultado in resultados_upload:
                                adicionar_ao_indice(arquivo_indice, {
                                    "titulo": resultado.get("nome", livro.titulo),
                                    "url_audio": resultado.get("direct_url", ""),
                                    "categoria": categoria_drive or "Documentos",
                                    "data": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
                                })
                            logging.info(f"[OK] Indice Alexa atualizado: {arquivo_indice.name}")
                        except Exception as ei:
                            logging.warning(f"Indice: {ei}")

                        logging.info(f"[OK] Diga: 'Alexa, abre meus audiobooks'")

                    except Exception as e:
                        logging.warning(f"RSS/GitHub: {e} - verifique manualmente")

            except Exception as e:
                logging.error(f"❌ Erro no upload: {e}")
                logging.info("Arquivos locais disponíveis em:")
                logging.info(f"   {pasta_saida}")
    else:
        logging.info("")
        logging.info("⏩ Upload desabilitado (--no-upload)")
        logging.info(f"📁 Arquivos disponíveis em: {pasta_saida}")

    # ──────────────────────────────────────────────────────────
    # CONCLUSÃO
    # ──────────────────────────────────────────────────────────

    tempo_total = time.time() - inicio_total
    tempo_formatado = formatar_tempo(tempo_total)

    logging.info("")
    logging.info("=" * 60)
    logging.info("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    logging.info("=" * 60)
    logging.info(f"⏱️  Tempo total: {tempo_formatado}")
    logging.info(f"📚 Livro: {livro.titulo}")
    logging.info(f"🎵 Arquivos gerados: {len(arquivos_audio)}")
    logging.info(f"📁 Localização: {pasta_saida}")

    if not args.no_upload:
        logging.info("")
        logging.info("📋 Próximo passo:")
        logging.info("   1. Abra o arquivo README_MyPod.txt")
        logging.info("   2. Siga as instruções para configurar na Alexa")
        logging.info("   3. Seu amigo já pode usar 100% por voz!")

    # Limpa checkpoint
    if ENABLE_CHECKPOINTS:
        limpar_checkpoint(CHECKPOINT_FILE)

    # Notificação sonora
    if NOTIFY_ON_COMPLETE:
        notificar_conclusao()

    return True


# ==================== FUNCAO PARA GUI ====================

def executar_pipeline_completo(
    caminho_pdf: str,
    nome_livro: str,
    fazer_upload: bool = True,
    publicar_rss: bool = True,
    callback_progresso=None,
    callback_percentual=None
) -> bool:
    """
    Funcao simplificada para a GUI chamar.
    Executa o pipeline completo com callback de progresso.
    Aceita qualquer formato de documento (não apenas PDF).

    Args:
        caminho_pdf: Caminho do documento (nome mantido por compatibilidade)
        nome_livro: Nome do livro/documento
        fazer_upload: Se True, sobe para Google Drive
        publicar_rss: Se True, gera RSS e sobe para GitHub
        callback_progresso: Funcao opcional para reportar progresso

    Returns:
        True se sucesso, False se falhou
    """
    import argparse
    import logging

    # Handler que intercepta logging e manda para a GUI
    class CallbackHandler(logging.Handler):
        def emit(self, record):
            if callback_progresso:
                callback_progresso(self.format(record))

    handler = None
    if callback_progresso:
        handler = CallbackHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(handler)

    # Monta argumentos simulados para o pipeline
    args = argparse.Namespace(
        arquivo=caminho_pdf,  # Aceita qualquer formato agora
        pdf=None,
        voz="thalita",
        output=None,
        no_upload=not fazer_upload,
        no_ocr=False,
        verbose=False,
        resume=False
    )

    import tts_engine as _tts
    _original_processar = _tts.processar_capitulos_paralelo

    def _processar_com_progresso(*a, **kw):
        kw["progress_callback"] = callback_percentual
        return _original_processar(*a, **kw)

    _tts.processar_capitulos_paralelo = _processar_com_progresso

    try:
        return executar_pipeline(args)
    except Exception as e:
        logging.error(f"[ERRO] {e}")
        return False
    finally:
        _tts.processar_capitulos_paralelo = _original_processar
        if handler:
            logging.getLogger().removeHandler(handler)


# ==================== MAIN ====================

def main():
    """Ponto de entrada principal"""

    # Exibe banner
    print(MESSAGES['welcome'])

    # Parse argumentos
    args = parse_args()

    # Configura logging
    nivel = 'DEBUG' if args.verbose else LOG_CONFIG['level']
    setup_logging(
        level=nivel,
        colored=LOG_CONFIG['colored'],
        log_file=LOG_CONFIG['log_file'] if LOG_CONFIG['save_to_file'] else None
    )

    # Log inicial
    arquivo = args.arquivo or args.pdf
    logging.info(f"Projeto Caxinguele v2")
    logging.info(f"Arquivo: {arquivo}")
    logging.info(f"Voz: {args.voz}")
    if args.no_upload:
        logging.info(f"Upload desabilitado")
    if args.resume:
        logging.info(f"Modo resume ativado")

    # Executa pipeline
    try:
        sucesso = executar_pipeline(args)

        if sucesso:
            sys.exit(0)
        else:
            logging.error("❌ Pipeline falhou")
            sys.exit(1)

    except KeyboardInterrupt:
        logging.warning("\n⚠️  Interrompido pelo usuário")
        logging.info("Use --resume para retomar de onde parou")
        sys.exit(130)

    except Exception as e:
        logging.error(f"❌ Erro fatal: {e}")
        logging.exception("Stack trace:")
        sys.exit(1)


if __name__ == '__main__':
    main()
