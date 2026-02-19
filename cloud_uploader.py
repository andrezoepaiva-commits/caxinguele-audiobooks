"""
Modulo para upload de audiobooks no Google Drive
Usa OAuth2 com token salvo localmente (autentica uma vez, depois e automatico)
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import GDRIVE_CONFIG, UPLOAD_TIMEOUT
from utils import retry_com_backoff, formatar_tamanho


# Escopo: acesso apenas aos arquivos criados por este app
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Arquivos de credenciais
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


# ==================== AUTENTICACAO ====================

def obter_servico_drive():
    """
    Obtém serviço autenticado via OAuth2 com token salvo.

    - Primeira vez: abre navegador para autorizar
    - Proximas vezes: usa token salvo automaticamente (sem navegador)

    Returns:
        Objeto service do Google Drive API
    """
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"credentials.json nao encontrado em: {CREDENTIALS_FILE}\n"
            "Baixe o arquivo em: Google Cloud Console -> APIs -> Credenciais -> "
            "Seu OAuth 2.0 Client -> Baixar JSON\n"
            "Renomeie para 'credentials.json' e coloque na pasta do projeto."
        )

    creds = None

    # Tenta carregar token salvo
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Se nao tem token ou expirou
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Renova token automaticamente (sem abrir navegador)
            logging.info("Renovando token de acesso...")
            creds.refresh(Request())
        else:
            # Primeira autenticacao: abre navegador UMA VEZ
            logging.info("Primeira autenticacao: abrindo navegador...")
            print()
            print("=" * 60)
            print("AUTORIZACAO NECESSARIA (apenas desta vez!)")
            print("=" * 60)
            print()
            print("1. Uma janela do navegador vai abrir")
            print("2. Faca login com sua conta Google")
            print("3. Se aparecer 'App nao verificado', clique em:")
            print("   'Avancado' -> 'Acessar [nome do app] (nao seguro)'")
            print("4. Clique em 'Permitir'")
            print()
            print("Apos isso, o token sera salvo e voce NUNCA mais")
            print("precisara fazer isso de novo!")
            print("=" * 60)
            print()

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Salva token para proximas execucoes
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        logging.info(f"Token salvo em: {TOKEN_FILE}")

    service = build('drive', 'v3', credentials=creds)
    logging.info("Google Drive autenticado com sucesso")
    return service


# ==================== OPERACOES COM PASTAS ====================

def buscar_pasta(service, nome_pasta: str, parent_id: Optional[str] = None) -> Optional[str]:
    """
    Busca pasta pelo nome

    Args:
        service: Servico Google Drive
        nome_pasta: Nome da pasta
        parent_id: ID da pasta pai

    Returns:
        ID da pasta se encontrada, None caso contrario
    """
    try:
        query = f"name='{nome_pasta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            return items[0]['id']

        return None

    except HttpError as e:
        logging.error(f"Erro ao buscar pasta: {e}")
        return None


def criar_pasta(service, nome_pasta: str, parent_id: Optional[str] = None) -> Optional[str]:
    """
    Cria uma pasta no Google Drive

    Args:
        service: Servico Google Drive
        nome_pasta: Nome da pasta
        parent_id: ID da pasta pai

    Returns:
        ID da pasta criada
    """
    try:
        file_metadata = {
            'name': nome_pasta,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_id:
            file_metadata['parents'] = [parent_id]

        pasta = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        pasta_id = pasta.get('id')
        logging.info(f"Pasta criada: {nome_pasta} (ID: {pasta_id})")
        return pasta_id

    except HttpError as e:
        logging.error(f"Erro ao criar pasta: {e}")
        return None


def obter_ou_criar_pasta(service, nome_pasta: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Busca pasta, se nao existir, cria"""

    pasta_id = buscar_pasta(service, nome_pasta, parent_id)

    if pasta_id:
        logging.info(f"Pasta encontrada: {nome_pasta}")
        return pasta_id

    logging.info(f"Criando pasta: {nome_pasta}")
    return criar_pasta(service, nome_pasta, parent_id)


# ==================== UPLOAD DE ARQUIVOS ====================

def arquivo_ja_existe(service, nome_arquivo: str, pasta_id: str) -> Optional[str]:
    """
    Verifica se arquivo ja existe na pasta (evita duplicatas)

    Returns:
        ID do arquivo se existir, None caso contrario
    """
    try:
        query = f"name='{nome_arquivo}' and '{pasta_id}' in parents and trashed=false"

        results = service.files().list(
            q=query,
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])
        if items:
            return items[0]['id']

        return None

    except HttpError:
        return None


def tornar_arquivo_publico(service, arquivo_id: str) -> Optional[str]:
    """
    Torna arquivo publico (qualquer um com link pode acessar)

    Returns:
        URL direta para streaming
    """
    try:
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }

        service.permissions().create(
            fileId=arquivo_id,
            body=permission
        ).execute()

        url_direto = f"https://drive.google.com/uc?export=download&id={arquivo_id}"
        return url_direto

    except HttpError as e:
        logging.error(f"Erro ao tornar arquivo publico: {e}")
        return None


def upload_arquivo(
    service,
    arquivo_local: Path,
    pasta_id: Optional[str] = None,
    tornar_publico: bool = True
) -> Optional[Dict]:
    """
    Faz upload de um arquivo para o Google Drive

    Returns:
        Dict com id, nome, url do arquivo
    """
    arquivo_local = Path(arquivo_local)

    if not arquivo_local.exists():
        logging.error(f"Arquivo nao encontrado: {arquivo_local}")
        return None

    try:
        # Verifica se ja existe (evita duplicatas)
        if pasta_id:
            arquivo_id_existente = arquivo_ja_existe(service, arquivo_local.name, pasta_id)
            if arquivo_id_existente:
                logging.info(f"Arquivo ja existe, pulando: {arquivo_local.name}")
                url_direto = f"https://drive.google.com/uc?export=download&id={arquivo_id_existente}"
                return {
                    'id': arquivo_id_existente,
                    'nome': arquivo_local.name,
                    'url': f"https://drive.google.com/file/d/{arquivo_id_existente}/view",
                    'direct_url': url_direto
                }

        # Metadata
        file_metadata = {'name': arquivo_local.name}
        if pasta_id:
            file_metadata['parents'] = [pasta_id]

        # Upload com resumable (bom para arquivos grandes)
        media = MediaFileUpload(
            str(arquivo_local),
            mimetype='audio/mpeg',
            resumable=True
        )

        tamanho = formatar_tamanho(arquivo_local.stat().st_size)
        logging.info(f"Upload: {arquivo_local.name} ({tamanho})")

        arquivo = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()

        arquivo_id = arquivo.get('id')

        # Torna publico
        url_direto = None
        if tornar_publico:
            url_direto = tornar_arquivo_publico(service, arquivo_id)

        logging.info(f"[OK] Upload concluido: {arquivo_local.name}")

        return {
            'id': arquivo_id,
            'nome': arquivo_local.name,
            'url': arquivo.get('webViewLink'),
            'direct_url': url_direto
        }

    except HttpError as e:
        logging.error(f"Erro no upload de {arquivo_local.name}: {e}")
        return None


# ==================== UPLOAD DO AUDIOBOOK COMPLETO ====================

def upload_audiobook(
    arquivos: List[Path],
    nome_livro: str,
    pasta_raiz_id: str = None,
    criar_pasta_livro: bool = True
) -> List[Dict]:
    """
    Faz upload de audiobook completo (multiplos capitulos)

    Args:
        arquivos: Lista de arquivos MP3
        nome_livro: Nome do livro
        pasta_raiz_id: ID da pasta raiz (se None, busca pelo nome)
        criar_pasta_livro: Se True, cria subpasta para o livro

    Returns:
        Lista de dicts com informacoes dos arquivos
    """
    logging.info(f"Iniciando upload: {nome_livro} ({len(arquivos)} arquivos)")

    service = obter_servico_drive()

    # Obtém pasta raiz
    if not pasta_raiz_id:
        pasta_raiz_nome = GDRIVE_CONFIG['root_folder']
        pasta_raiz_id = buscar_pasta(service, pasta_raiz_nome)

        if not pasta_raiz_id:
            # Cria a pasta raiz automaticamente
            logging.info(f"Criando pasta raiz: {pasta_raiz_nome}")
            pasta_raiz_id = criar_pasta(service, pasta_raiz_nome)
            if not pasta_raiz_id:
                logging.error(f"Nao foi possivel criar pasta raiz: {pasta_raiz_nome}")
                return []

    # Cria pasta do livro
    pasta_livro_id = pasta_raiz_id
    if criar_pasta_livro:
        pasta_livro_id = obter_ou_criar_pasta(service, nome_livro, pasta_raiz_id)
        if not pasta_livro_id:
            return []

    # Upload de cada arquivo
    resultados = []
    from utils import criar_progress_bar

    with criar_progress_bar(len(arquivos), "Upload Drive") as pbar:
        for arquivo in sorted(arquivos):  # Ordenado por nome
            if arquivo and arquivo.exists() and arquivo.stat().st_size > 0:

                def fazer_upload(arq=arquivo):
                    return upload_arquivo(
                        service, arq, pasta_livro_id,
                        tornar_publico=GDRIVE_CONFIG['make_public']
                    )

                resultado = retry_com_backoff(fazer_upload, max_tentativas=3, delay_inicial=5)

                if resultado:
                    resultados.append(resultado)

            pbar.update(1)

    logging.info(f"Upload concluido: {len(resultados)}/{len(arquivos)} arquivos")
    return resultados


# ==================== INSTRUCOES MYPOD ====================

def gerar_instrucoes_mypod(
    resultados_upload: List[Dict],
    nome_livro: str,
    pasta_saida: Path
) -> Path:
    """
    Gera arquivo de instrucoes para configurar MyPod na Alexa
    """
    from config import MYPOD_CONFIG
    arquivo_instrucoes = pasta_saida / MYPOD_CONFIG['instructions_file']

    conteudo = f"""
INSTRUCOES PARA CONFIGURAR ALEXA + MYPOD
==========================================

Audiobook: {nome_livro}
Total de arquivos: {len(resultados_upload)}

------------------------------------------
PASSO 1: INSTALAR SKILL MYPOD NA ALEXA
------------------------------------------

1. No celular, abra o app "Amazon Alexa"
2. Menu -> Skills e Jogos
3. Pesquise: "My Pod"
4. Clique em "Ativar"

------------------------------------------
PASSO 2: ACESSAR SITE DO MYPOD
------------------------------------------

1. Acesse: https://mypodapp.com
2. Faca login com sua conta Amazon

------------------------------------------
PASSO 3: CRIAR PLAYLIST "{nome_livro}"
------------------------------------------

1. Clique em "Create Playlist"
2. Nome: {nome_livro}
3. Adicione cada link abaixo como "Episode"

------------------------------------------
LINKS DOS CAPITULOS (adicionar em ordem)
------------------------------------------

"""

    for i, resultado in enumerate(resultados_upload, 1):
        url = resultado.get('direct_url', resultado.get('url', ''))
        nome = resultado.get('nome', f'Capitulo {i}')
        conteudo += f"{i:02d}. {nome}\n    {url}\n\n"

    conteudo += f"""
------------------------------------------
PASSO 4: COMANDOS DE VOZ NA ALEXA
------------------------------------------

"Alexa, abre My Pod"
"Alexa, toca {nome_livro}"
"Alexa, pausa"
"Alexa, continua"
"Alexa, proximo"
"Alexa, volta 30 segundos"

A Alexa SEMPRE lembra onde voce parou!

==========================================
"""

    with open(arquivo_instrucoes, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    logging.info(f"Instrucoes geradas: {arquivo_instrucoes}")
    return arquivo_instrucoes
