
import argparse
import logging
from typing import Any

import httpx
import uvicorn

from mcp.server.fastmcp import FastMCP

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize FastMCP server for BrasilAPI tools.
# If json_response is set to True, the server will use JSON responses instead of SSE streams
# If stateless_http is set to True, the server uses true stateless mode (new transport per request)
mcp = FastMCP(name="brasilapi", json_response=False, stateless_http=False)

async def busca_informacoes_cep(cep: str) -> dict[str, Any]:
    """Busca informações de endereço a partir de um CEP usando a API BrasilAPI."""

    url = f"https://brasilapi.com.br/api/cep/v1/{cep}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}
        
def formata_informacoes_cep(info: dict[str, Any]) -> str:
    """Formata as informações de endereço obtidas a partir do CEP."""
    if not info:
        return "Não foi possível obter informações para o CEP fornecido."

    return f"""
        CEP: {info.get('cep', 'N/A')}
        Estado: {info.get('state', 'N/A')}
        Cidade: {info.get('city', 'N/A')}
        Bairro: {info.get('neighborhood', 'N/A')}
        Rua: {info.get('street', 'N/A')}
    """

async def busca_feriados_do_ano(ano: int) -> list[dict[str, Any]]:
    """Busca os feriados do ano usando a API BrasilAPI."""

    url = f"https://brasilapi.com.br/api/feriados/v1/{ano}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []
        
def formata_feriados(feriados: list[dict[str, Any]]) -> str:
    """Formata a lista de feriados em uma string legível."""
    if not feriados:
        return "Não foi possível obter os feriados para o ano fornecido."

    formatted_feriados = "\n".join(
        [f"{feriado.get('date', 'N/A')}: {feriado.get('name', 'N/A')} | {feriado.get('type', 'N/A')}" for feriado in feriados]
    )
    return f"Feriados do ano:\n{formatted_feriados}"

@mcp.tool()
async def get_cep_info(cep: str) -> str:
    """Busca informações de endereço a partir de um CEP."""
    info = await busca_informacoes_cep(cep)
    return formata_informacoes_cep(info)

@mcp.tool()
async def get_feriados(ano: int) -> str:
    """Busca os feriados de um ano específico."""
    feriados = await busca_feriados_do_ano(ano)
    return formata_feriados(feriados)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--port", type=int, default=8124, help="Localhost port to listen on for BrasilAPI tools")
    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host="localhost", port=args.port)