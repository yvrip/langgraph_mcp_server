

import argparse
import logging
from typing import Any

import httpx
import uvicorn

from mcp.server.fastmcp import FastMCP

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

mcp = FastMCP(name="ferramentas-bcb", json_response=False, stateless_http=False)

async def busca_cotacao_dolar(data_cotacao: str) -> dict[str, Any]:
    """Busca a cotação atual do dólar usando a API do Banco Central.
    
    Args:
        data_cotacao: Data para a qual se deseja obter a cotação, no formato 'MM-DD-YYYY'.

    Returns:
        dict[str, Any]: Dicionário contendo as informações de cotação do dólar.
    """
    url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{data_cotacao}'&$format=json"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}
        
def formata_cotacao_dolar(cotacao: dict[str, Any]) -> str:
    """Formata as informações de cotação do dólar em uma string legível.

    Args:
        cotacao: Dicionário contendo as informações de cotação do dólar.

    Returns:
        str: String formatada com as informações de cotação do dólar.
    """
    if not cotacao or "value" not in cotacao or not cotacao["value"]:
        return "Não foi possível obter a cotação para a data fornecida."

    valor_compra = cotacao["value"][0]["cotacaoCompra"]
    valor_venda = cotacao["value"][0]["cotacaoVenda"]
    data = cotacao["value"][0]["dataHoraCotacao"]
    return f"Cotação do dólar em {data}: R$ {valor_compra:.2f} (compra), R$ {valor_venda:.2f} (venda)"

async def busca_taxa_selic(data_inicial: str, data_final: str) -> list[dict[str, str]]:
    """Busca a taxa SELIC para um período usando a API do Banco Central.

    Args:
        data_inicial: Data inicial do período, no formato 'DD/MM/YYYY'.
        data_final: Data final do período, no formato 'DD/MM/YYYY'.

    Returns:
        list[dict[str, str]]: Lista de dicionários contendo as informações da taxa SELIC.
    """
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados?formato=json&dataInicial={data_inicial}&dataFinal={data_final}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []
        
def formata_taxa_selic(taxa: list[dict[str, str]]) -> str:

    if len(taxa) == 0:
        return "Não foi possível obter a taxa SELIC para o período fornecido."
    
    elif len(taxa) == 1:
        valor = float(taxa[0]["valor"])
        data = taxa[0]["data"]
        return f"Taxa SELIC em {data}: {valor:.2f}%"
    
    else:
        formatted_taxa = "\n".join([f"{item['data']}: {float(item['valor']):.2f}%" for item in taxa])
        return f"Taxa SELIC para o período:\n{formatted_taxa}"
    

@mcp.tool()
async def get_cotacao_dolar(data_cotacao: str) -> str:
    """Busca a cotação do dólar para uma data específica.
    
    Args:
        data_cotacao: Data para a qual se deseja obter a cotação, no formato 'MM-DD-YYYY'.

    Returns:
        str: String formatada com as informações de cotação do dólar.
    """
    cotacao = await busca_cotacao_dolar(data_cotacao)
    return formata_cotacao_dolar(cotacao)

@mcp.tool()
async def get_taxa_selic(data_inicial: str, data_final: str) -> str:
    """Busca a taxa SELIC para um período específico.
    
    Args:
        data_inicial: Data inicial do período, no formato 'DD/MM/YYYY'.
        data_final: Data final do período, no formato 'DD/MM/YYYY'.

    Returns:
        str: String formatada com as informações da taxa SELIC.
    """
    taxa = await busca_taxa_selic(data_inicial, data_final)
    return formata_taxa_selic(taxa)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--port", type=int, default=8125, help="Localhost port to listen on for BrasilAPI tools")
    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host="localhost", port=args.port)