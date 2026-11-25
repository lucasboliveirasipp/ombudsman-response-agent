import io
import time
import tempfile
import PyPDF2
import os
from typing import List, Union, Dict, Any
from .config import document_intelligence_client
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest


def get_time_counter():
    """Retorna o contador de performance atual para calcular o tempo de execução."""
    return time.perf_counter()


def calc_time_counter(start_time: float):
    """Calcula e formata o tempo decorrido desde o início da execução."""
    processing_time = {}
    processing_time["start_time"] = start_time
    processing_time["end_time"] = get_time_counter()
    total_time = processing_time["end_time"] - processing_time["start_time"]
    processing_time["elapsed_time"] = f"{total_time:.2f} segundos"
    return processing_time


def create_temp_files(files: Union[List, object]):
    """Cria arquivos temporários no sistema para processamento."""
    if not isinstance(files, list):
        files = [files]

    temp_files = []
    for file in files:
        file.seek(0)
        file_content = file.read()
        file_name = getattr(file, "name", f"temp_file_{os.getpid()}.pdf")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_files.append(
                {
                    "file": temp_file,
                    "metadata": {
                        "original_name": file_name,
                        "type": "pdf",
                        "temp_name": temp_file.name,
                    },
                }
            )
    return temp_files


def extract_images_from_pdf_di(pdf_file, original_name):
    """
    Extrai texto/OCR usando Azure Document Intelligence (DI) com 'prebuilt-layout'.
    Retorna uma lista de dicionários, um para cada página.
    """
    pages = []
    try:
        with open(pdf_file, "rb") as file:
            poller = document_intelligence_client.begin_analyze_document(
                "prebuilt-layout", AnalyzeDocumentRequest(bytes_source=file.read())
            )

            result: AnalyzeResult = poller.result()

        if result.pages:
            for i, page in enumerate(result.pages):
                extracted_text = []

                if page.lines:
                    for line in page.lines:
                        extracted_text.append(line.content)

                pages.append(
                    {
                        "text": "\n".join(extracted_text),
                        "metadata": {
                            "document_name": original_name,
                            "page_number": i + 1,
                            "document_type": "pdf",
                        },
                    }
                )

        if not pages:
            return [
                {
                    "text": f"Erro de extração (Azure DI): Nenhuma página ou texto extraído. Fallback para análise.",
                    "metadata": {"document_name": original_name, "page_number": 1},
                }
            ]

    except Exception as e:
        return [
            {
                "text": f"Erro de extração (Azure DI): {e}. Texto de fallback para análise.",
                "metadata": {"document_name": original_name, "page_number": 1},
            }
        ]

    return pages


def extract_pages_from_pdf_di(
    pdf_file: str, original_name: str
) -> List[Dict[str, Any]]:
    """
    Extrai texto de PDFs com camada digital via PyPDF2.
    Esta função deve ser mantida para PDFs com texto nativo.
    """
    pages = []

    try:
        with open(pdf_file, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()

                if text and text.strip():
                    pages.append(
                        {
                            "text": text,
                            "metadata": {
                                "document_name": original_name,
                                "page_number": i + 1,
                            },
                        }
                    )

    except Exception as e:
        print(f"ERRO DE LEITURA PyPDF2 no arquivo {original_name}: {e}")

        return [
            {
                "text": f"Erro de extração (PyPDF2): {e}. Texto de fallback para análise.",
                "metadata": {"document_name": original_name, "page_number": 1},
            }
        ]

    return pages
