# Carrega variáveis do arquivo .env mais próximo (pasta do projeto)
def _carregar_env():
    from pathlib import Path
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for pasta in Path(__file__).resolve().parents:
        if (pasta / ".env").exists():
            load_dotenv(pasta / ".env")
            break


_carregar_env()

import os
from langchain_openai import AzureChatOpenAI
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from pymongo import MongoClient


gpt_4_1_mini = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    openai_api_version="2024-08-01-preview",
    deployment_name="gpt-4.1-mini",
    openai_api_type="azure",
    temperature=0,
)

llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    openai_api_version="2024-08-01-preview",
    deployment_name="gpt-4o-mini",
    openai_api_type="azure",
    temperature=0,
)

gpt_4 = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    openai_api_version="2024-08-01-preview",
    deployment_name="gpt-4o",
    openai_api_type="azure",
    temperature=0,
    top_p=0,
)

document_intelligence_client = DocumentIntelligenceClient(
    endpoint=os.getenv("ENDPOINT_AZURE"),
    credential=AzureKeyCredential(os.getenv("KEY_AZURE")),
)


class DBConnector:
    def __init__(self, connection_string: str, database_name: str):
        self.client = MongoClient(connection_string)
        self.database = self.client[database_name]

    def get_db(self):
        return self.database


MONGO = DBConnector(
    "mongodb://localhost:27017", "feedbacks"
).get_db()
