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

def criar_tabela_dynamodb():
    """Cria tabela DynamoDB para persistência de progresso do audiobook."""

    # Configurar cliente DynamoDB
    try:
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')

        table_name = 'caxinguele_progresso'

        print(f"🔄 Criando tabela '{table_name}' no DynamoDB (us-east-1)...")

        # Criar tabela
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'  # String
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand (sem limites de escrita)
            Tags=[
                {'Key': 'Project', 'Value': 'Caxinguele'},
                {'Key': 'Purpose', 'Value': 'Salvar progresso de audiobooks por usuário'}
            ]
        )

        print(f"✅ Tabela criada com sucesso!")
        print(f"   ARN: {response['TableDescription']['TableArn']}")
        print(f"   Status: {response['TableDescription']['TableStatus']}")

        # Aguardar que a tabela ative
        print(f"\n⏳ Aguardando ativação da tabela (pode levar alguns segundos)...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        print(f"✅ Tabela '{table_name}' está ativa!")
        print(f"\n📝 Próximos passos:")
        print(f"   1. Vá a: AWS Console → Lambda → audiobook-alexa")
        print(f"   2. Clique em 'Configuration' → 'Execution role'")
        print(f"   3. Clique na role e adicione permissão:")
        print(f"      - 'AmazonDynamoDBFullAccess' (OU)")
        print(f"      - Policy customizada: arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess")
        print(f"\n✨ Depois disso, o Lambda conseguirá salvar progresso na tabela!")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Tabela '{table_name}' já existe!")
            print(f"   Você pode deletá-la com: aws dynamodb delete-table --table-name {table_name}")
            return False
        else:
            print(f"❌ Erro ao criar tabela: {e}")
            return False
    except Exception as e:
        print(f"❌ Erro de conexão com AWS: {e}")
        print(f"   Verifique se:")
        print(f"   - AWS CLI está instalado: pip install boto3")
        print(f"   - Credenciais estão configuradas: ~/.aws/credentials")
        return False

if __name__ == '__main__':
    sucesso = criar_tabela_dynamodb()
    sys.exit(0 if sucesso else 1)
