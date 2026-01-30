from typing import Optional

from app.core.settings import settings
from app.services.elasticsearch import ElasticsearchClientError, ElasticsearchService

class DependencyStorage:
    def __init__(self):
        self.elasticsearch_client = ElasticsearchService(url=settings.ELASTICSEARCH_URL, api_key=settings.ELASTICSEARCH_API_KEY)
        self.elasticsearch_client_error = ElasticsearchClientError
    def get_elasticsearch_service(self) -> ElasticsearchService:
        return self.elasticsearch_client
    def get_elasticsearch_client_error(self) -> ElasticsearchClientError:
        return self.elasticsearch_client_error

async def initialize_dependencies():
    global dependency_storage
    dependency_storage = DependencyStorage()

def get_elasticsearch_service() -> ElasticsearchService:
    if not dependency_storage:
        raise RuntimeError("Dependency storage not initialized")
    return dependency_storage.get_elasticsearch_service()

def get_elasticsearch_client_error() -> ElasticsearchClientError:
    if not dependency_storage:
        raise RuntimeError("Dependency storage not initialized")
    return dependency_storage.get_elasticsearch_client_error()