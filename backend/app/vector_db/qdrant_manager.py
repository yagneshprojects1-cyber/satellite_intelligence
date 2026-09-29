import threading
import uuid
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams,
    Filter, FieldCondition, MatchValue
)

# Local (embedded) Qdrant locks the storage folder to a single client.
# Health checks, pipeline status, search, and indexing must share one instance.
_CLIENTS = {}
_CLIENTS_LOCK = threading.Lock()


def get_qdrant_client(storage_path="qdrant_storage"):
    """Return a process-wide Qdrant client for the given local storage path."""
    key = str(Path(storage_path).resolve())
    with _CLIENTS_LOCK:
        client = _CLIENTS.get(key)
        if client is None:
            client = QdrantClient(path=key)
            _CLIENTS[key] = client
        return client


class QdrantManager:
    def __init__(self, storage_path="qdrant_storage", collection_name="satellite_tiles"):
        self.storage_path = Path(storage_path)
        self.collection_name = collection_name
        self.client = get_qdrant_client(self.storage_path)
        
    def setup_collection(self, dimension=1024):
        if not self.client.collection_exists(self.collection_name):
            from qdrant_client.models import VectorParams, Distance
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
            # Note: Payload indexes are not supported in local Qdrant, only in server mode
            # We'll skip payload index creation for local deployment
            print(f"Created collection '{self.collection_name}' with dimension {dimension} and COSINE distance.")
        else:
            print(f"Collection '{self.collection_name}' already exists.")

    def search_similar(self, query_vector, top_k=5, filter_conditions=None):
        query_filter = None
        if filter_conditions:
            must_conditions = []
            for k, v in filter_conditions.items():
                must_conditions.append(FieldCondition(key=k, match=MatchValue(value=v)))
            query_filter = Filter(must=must_conditions)
            
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k
        )
        return results

    def _generate_deterministic_uuid(self, tile_id):
        # Qdrant accepts UUIDs or integers as Point IDs.
        return str(uuid.uuid5(uuid.NAMESPACE_OID, tile_id))

    def point_exists(self, point_id):
        records = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
            with_payload=False,
            with_vectors=False
        )
        return len(records) > 0

    def get_collection_info(self):
        if not self.client.collection_exists(self.collection_name):
            return None
        return self.client.get_collection(self.collection_name)
