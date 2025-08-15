"""
Simplified Elasticsearch Service - Direct HTTP Client
Bypasses Python client compatibility issues with v8/v9 headers
"""

import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ElasticsearchService:
    """Simple HTTP-based Elasticsearch client to avoid version compatibility issues"""
    
    def __init__(self):
        self.elasticsearch_url = "https://elastic.mevzuatgpt.org"
        self.index_name = "mevzuat_embeddings"
        self.session = None
        
        logger.info(f"Simple Elasticsearch service initialized: {self.elasticsearch_url}")
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
        return self.session
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.elasticsearch_url}/_cluster/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    
                    # Get document count
                    async with session.get(f"{self.elasticsearch_url}/{self.index_name}/_count") as count_response:
                        count_data = await count_response.json() if count_response.status == 200 else {"count": 0}
                    
                    return {
                        "health": "ok",
                        "cluster_status": health_data.get("status", "unknown"),
                        "cluster_name": health_data.get("cluster_name", "unknown"),
                        "vector_dimensions": 2048,
                        "document_count": count_data.get("count", 0)
                    }
                else:
                    return {"health": "error", "error": f"HTTP {response.status}"}
                    
        except Exception as e:
            return {"health": "error", "error": str(e)}
    
    async def bulk_create_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> List[str]:
        """Bulk create embeddings using HTTP POST"""
        try:
            session = await self._get_session()
            
            # Prepare bulk request body
            bulk_body = []
            for data in embeddings_data:
                # Index action
                bulk_body.append(json.dumps({"index": {"_index": self.index_name}}))
                
                # Document data
                doc = {
                    "document_id": data["document_id"],
                    "content": data["content"],
                    "embedding": data["embedding"],
                    "chunk_index": data.get("chunk_index", 0),
                    "page_number": data.get("page_number"),
                    "line_start": data.get("line_start"),
                    "line_end": data.get("line_end"),
                    "source_institution": data.get("source_institution"),
                    "source_document": data.get("source_document"),
                    "metadata": data.get("metadata", {}),
                    "created_at": datetime.utcnow().isoformat()
                }
                bulk_body.append(json.dumps(doc))
            
            bulk_data = "\n".join(bulk_body) + "\n"
            
            async with session.post(
                f"{self.elasticsearch_url}/_bulk",
                data=bulk_data,
                headers={"Content-Type": "application/x-ndjson"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract document IDs from response
                    embedding_ids = []
                    for item in result.get("items", []):
                        if "index" in item and item["index"].get("_id"):
                            embedding_ids.append(item["index"]["_id"])
                    
                    logger.info(f"Bulk created {len(embedding_ids)} embeddings")
                    return embedding_ids
                else:
                    error_text = await response.text()
                    logger.error(f"Bulk create failed: HTTP {response.status}, {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Bulk create embeddings failed: {e}")
            return []
    
    async def similarity_search(
        self,
        query_vector: List[float],
        k: int = 10,
        institution_filter: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search using HTTP POST"""
        try:
            session = await self._get_session()
            
            # Build Elasticsearch query
            query = {
                "size": k,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_vector}
                        },
                        "min_score": similarity_threshold + 1.0  # Adjust for +1.0 offset
                    }
                },
                "_source": ["document_id", "content", "chunk_index", "page_number", "source_institution", "source_document", "metadata"]
            }
            
            # Add institution filter if provided
            if institution_filter:
                query["query"]["script_score"]["query"] = {
                    "term": {"source_institution": institution_filter}
                }
            
            # Add document IDs filter if provided
            if document_ids:
                if institution_filter:
                    query["query"]["script_score"]["query"] = {
                        "bool": {
                            "must": [
                                {"term": {"source_institution": institution_filter}},
                                {"terms": {"document_id": document_ids}}
                            ]
                        }
                    }
                else:
                    query["query"]["script_score"]["query"] = {
                        "terms": {"document_id": document_ids}
                    }
            
            async with session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_search",
                json=query
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Process search results
                    results = []
                    for hit in result.get("hits", {}).get("hits", []):
                        source = hit["_source"]
                        similarity = hit["_score"] - 1.0  # Remove the +1.0 offset
                        
                        results.append({
                            "id": hit["_id"],
                            "document_id": source["document_id"],
                            "content": source["content"],
                            "chunk_index": source.get("chunk_index", 0),
                            "page_number": source.get("page_number"),
                            "source_institution": source.get("source_institution"),
                            "source_document": source.get("source_document"),
                            "metadata": source.get("metadata", {}),
                            "similarity": similarity
                        })
                    
                    logger.info(f"Similarity search found {len(results)} results")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Similarity search failed: HTTP {response.status}, {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
    
    async def get_embeddings_count(self, document_id: Optional[str] = None) -> int:
        """Get embeddings count using HTTP GET"""
        try:
            session = await self._get_session()
            
            if document_id:
                query = {
                    "query": {
                        "term": {"document_id": document_id}
                    }
                }
                async with session.post(
                    f"{self.elasticsearch_url}/{self.index_name}/_count",
                    json=query
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("count", 0)
            else:
                async with session.get(f"{self.elasticsearch_url}/{self.index_name}/_count") as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("count", 0)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting embeddings count: {e}")
            return 0
    
    async def delete_document_embeddings(self, document_id: str) -> int:
        """Delete all embeddings for a document"""
        try:
            session = await self._get_session()
            
            delete_query = {
                "query": {
                    "term": {"document_id": document_id}
                }
            }
            
            async with session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_delete_by_query",
                json=delete_query
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    deleted = result.get("deleted", 0)
                    logger.info(f"Deleted {deleted} embeddings for document {document_id}")
                    return deleted
                else:
                    error_text = await response.text()
                    logger.error(f"Delete embeddings failed: HTTP {response.status}, {error_text}")
                    return 0
                    
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            return 0
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        k: int = 10,
        institution_filter: Optional[str] = None,
        vector_boost: float = 2.0,
        text_boost: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector and text search"""
        try:
            session = await self._get_session()
            
            # Build hybrid query
            query = {
                "size": k,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": f"({vector_boost} * (cosineSimilarity(params.query_vector, 'embedding') + 1.0))",
                                        "params": {"query_vector": query_vector}
                                    }
                                }
                            },
                            {
                                "match": {
                                    "content": {
                                        "query": query_text,
                                        "boost": text_boost
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["document_id", "content", "chunk_index", "page_number", "source_institution", "source_document", "metadata"]
            }
            
            # Add institution filter
            if institution_filter:
                query["query"]["bool"]["filter"] = [
                    {"term": {"source_institution": institution_filter}}
                ]
            
            async with session.post(
                f"{self.elasticsearch_url}/{self.index_name}/_search",
                json=query
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Process hybrid search results
                    results = []
                    for hit in result.get("hits", {}).get("hits", []):
                        source = hit["_source"]
                        
                        results.append({
                            "id": hit["_id"],
                            "document_id": source["document_id"],
                            "content": source["content"],
                            "chunk_index": source.get("chunk_index", 0),
                            "page_number": source.get("page_number"),
                            "source_institution": source.get("source_institution"),
                            "source_document": source.get("source_document"),
                            "metadata": source.get("metadata", {}),
                            "similarity": hit["_score"] / (vector_boost + text_boost)  # Normalize score
                        })
                    
                    logger.info(f"Hybrid search found {len(results)} results")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Hybrid search failed: HTTP {response.status}, {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []