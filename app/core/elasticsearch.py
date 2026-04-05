from elasticsearch import AsyncElasticsearch
from app.core.config import settings

es_client = AsyncElasticsearch(hosts=[settings.elasticsearch_url])

async def get_es_client() -> AsyncElasticsearch:
    return es_client

async def close_es_client() -> None:
    await es_client.close()