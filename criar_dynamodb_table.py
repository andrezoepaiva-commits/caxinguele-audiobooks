#!/usr/bin/env python3
"""
Script para criar a tabela DynamoDB 'caxinguele_progresso' no AWS.

INSTRUÇÕES:
1. Configure as credenciais AWS:
   - Configure arquivo ~/.aws/credentials com suas chaves
   - OU use variáveis de ambiente: AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY

2. Execute este script:
   python criar_dynamodb_table.py

3. Depois, dê permissão ao Lambda:
   - AWS Console → Lambda → audiobook-alexa → Configuration → Permissions
   - Clique em execution role → Permissions → Add permission
   - Selecione "AmazonDynamoDBFullAccess" ou crie policy customizada

RESULTADO:
- Tabela 'caxinguele_progresso' com partition key 'user_id' (String)
- Billing Mode: PAY_PER_REQUEST (on-demand, sem custos iniciais)
"""

import boto3
import sys
from botocore.exceptions import ClientError

def criar_tabela(dynamodb, table_name, partition_key='user_id'):
    """Cria uma tabela DynamoDB com partition key String."""
    try:
        print(f"Criando tabela '{table_name}' no DynamoDB (us-east-1)...")
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': partition_key, 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': partition_key, 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
            Tags=[
                {'Key': 'Project', 'Value': 'Caxinguele'},
                {'Key': 'Purpose', 'Value': f'Tabela {table_name}'}
            ]
        )
        print(f"  OK! ARN: {response['TableDescription']['TableArn']}")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"  Tabela '{table_name}' ativa.")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"  Tabela '{table_name}' ja existe. OK.")
            return True
        else:
            print(f"  ERRO ao criar '{table_name}': {e}")
            return False


def criar_tabela_dynamodb():
    """Cria as 2 tabelas DynamoDB do projeto Caxinguele."""

    # Configurar cliente DynamoDB
    try:
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')

        # Tabela 1: progresso (qual capitulo o usuario parou)
        ok1 = criar_tabela(dynamodb, 'caxinguele_progresso')

        # Tabela 2: historico de escuta (tempo ouvido por sessao)
        ok2 = criar_tabela(dynamodb, 'caxinguele_listening_history')

        if ok1 and ok2:
            print(f"\nAs 2 tabelas estao prontas!")
            print(f"\nProximo passo:")
            print(f"  AWS Console > Lambda > CaxingueleAudiobooks > Configuration > Permissions")
            print(f"  Clique na execution role > Add permission > AmazonDynamoDBFullAccess")
            return True
        return False

    except Exception as e:
        print(f"Erro de conexao com AWS: {e}")
        print(f"  Verifique se:")
        print(f"  - boto3 instalado: pip install boto3")
        print(f"  - Credenciais configuradas: ~/.aws/credentials")
        return False

if __name__ == '__main__':
    sucesso = criar_tabela_dynamodb()
    sys.exit(0 if sucesso else 1)
