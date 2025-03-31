import asyncio
import aiohttp
import logging
from cachetools import TTLCache

# Configure o logging para ver as mensagens
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# URL do XML (use a mesma definida na sua API)
XML_URL = "https://redeurbana.com.br/imoveis/publico/97b375b0-05d4-48f5-9aeb-e9a1cae78c90"

# Crie um cache para armazenar o XML, conforme na sua API
xml_cache = TTLCache(maxsize=1, ttl=43200)

async def update_xml_cache():
    try:
        async with aiohttp.ClientSession() as session:
            # Aumentei o timeout para 60 segundos (ajuste se necessário)
            async with session.get(XML_URL, timeout=60) as response:
                response.raise_for_status()
                xml_data = await response.text()
                xml_cache["xml_data"] = xml_data
                logging.info("XML atualizado no cache.")
                return xml_data
    except Exception as e:
        logging.error(f"Erro ao atualizar XML: {e}")
        return None

# Função principal para testar
async def main():
    xml_data = await update_xml_cache()
    if xml_data:
        print("XML obtido com sucesso!")
        print(xml_data[:500])  # Imprime os primeiros 500 caracteres para ver o conteúdo
    else:
        print("Falha ao obter o XML.")

# Executa a função principal
if __name__ == "__main__":
    asyncio.run(main())
