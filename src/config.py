from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
ESTADO = RAIZ / "estado"
RESULTADOS = RAIZ / "resultados"
load_dotenv(RAIZ / ".env")

MENSAGEM_MANUAL = (
    "Não foi possível validar esta instrução. Encaminhe o pedido para análise manual. "
    "Nenhuma recomendação desta execução foi liberada."
)
