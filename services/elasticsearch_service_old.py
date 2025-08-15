"""
Elasticsearch Vector Service - Ultra Optimized for MevzuatGPT
Handles 2048-dimensional vectors with int8_hnsw optimization
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from elasticsearch import Elasticsearch, AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from core.config import get_settings

logger = logging.getLogger(__name__)

class ElasticsearchService:
    """Ultra-optimized Elasticsearch service for vector operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.elasticsearch_url = "https://elastic.mevzuatgpt.org"
        self.index_name = "mevzuat_embeddings"
        
        # Sync client for simple operations
        self.client = Elasticsearch([self.elasticsearch_url])
        
        # Async client with v8 compatibility headers
        self.async_client = AsyncElasticsearch(
            [self.elasticsearch_url],
            headers={
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            }
        )
        
        logger.info(f"Elasticsearch service initialized: {self.elasticsearch_url}")
    
    async def create_embedding(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        chunk_index: int = 0,
        page_number: Optional[int] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        source_institution: Optional[str] = None,
        source_document: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a single embedding in Elasticsearch"""
        
        doc = {
            "document_id": document_id,
            "content": content,
            "embedding": embedding,
            "chunk_index": chunk_index,
            "page_number": page_number,
            "line_start": line_start,
            "line_end": line_end,
            "source_institution": source_institution,
            "source_document": source_document,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            response = await self.async_client.index(
                index=self.index_name,
                body=doc
            )
            
            embedding_id = response["_id"]
            logger.info(f"Embedding created: {embedding_id} for document {document_id}")
            return embedding_id
            
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise
    
    async def bulk_create_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> List[str]:
        """Bulk create embeddings for optimal performance"""
        
        actions = []
        for data in embeddings_data:
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
            
            actions.append({
                "_index": self.index_name,
                "_source": doc
            })
        
        try:
            success_count, failed_items = await async_bulk(
                self.async_client,
                actions,
                chunk_size=100,
                request_timeout=60
            )
            
            logger.info(f"Bulk created {success_count} embeddings")
            if failed_items:
                logger.warning(f"Failed to create {len(failed_items)} embeddings")
            
            return [item.get("_id") for item in success_count] if success_count else []
            
        except Exception as e:
            logger.error(f"Error in bulk create: {e}")
            raise
    
    async def similarity_search(
        self,
        query_vector: List[float],
        k: int = 10,
        num_candidates: int = None,
        institution_filter: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Ultra-optimized vector similarity search
        Uses ES 8.19.2 advanced features: int8_hnsw, SIMD, ACORN-1
        """
        
        # Auto-calculate num_candidates for optimal performance
        if num_candidates is None:
            num_candidates = min(k * 20, 2000)  # Ultra high quality
        
        # Build kNN query
        knn_query = {
            "field": "embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": num_candidates
        }
        
        # Build filters
        filters = []
        if institution_filter:
            filters.append({"term": {"source_institution": institution_filter}})
        
        if document_ids:
            filters.append({"terms": {"document_id": document_ids}})
        
        # Add filter to kNN query if needed
        if filters:
            if len(filters) == 1:
                knn_query["filter"] = filters[0]
            else:
                knn_query["filter"] = {"bool": {"must": filters}}
        
        search_body = {
            "knn": knn_query,
            "_source": [
                "document_id", "content", "chunk_index", 
                "page_number", "line_start", "line_end",
                "source_institution", "source_document", "metadata"
            ]
        }
        
        try:
            response = await self.async_client.search(
                index=self.index_name,
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                # Convert ES score to similarity (approximate)
                score = hit["_score"]
                similarity = 1 / (1 + score) if score > 0 else 0
                
                # Apply similarity threshold
                if similarity >= similarity_threshold:
                    result = {
                        "id": hit["_id"],
                        "document_id": hit["_source"]["document_id"],
                        "content": hit["_source"]["content"],
                        "similarity": similarity,
                        "chunk_index": hit["_source"]["chunk_index"],
                        "page_number": hit["_source"]["page_number"],
                        "line_start": hit["_source"]["line_start"],
                        "line_end": hit["_source"]["line_end"],
                        "source_institution": hit["_source"]["source_institution"],
                        "source_document": hit["_source"]["source_document"],
                        "metadata": hit["_source"]["metadata"]
                    }
                    results.append(result)
            
            logger.info(f"Vector search found {len(results)} results above threshold {similarity_threshold}")
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            raise
    
    async def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        k: int = 10,
        institution_filter: Optional[str] = None,
        vector_boost: float = 2.0,
        text_boost: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Advanced hybrid search combining vector and text search"""
        
        search_body = {
            "query": {
                "bool": {
                    "should": [
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
            "knn": {
                "field": "embedding",
                "query_vector": query_vector,
                "k": k,
                "num_candidates": k * 20,
                "boost": vector_boost
            },
            "_source": [
                "document_id", "content", "chunk_index",
                "page_number", "source_institution", "metadata"
            ]
        }
        
        # Add institution filter
        if institution_filter:
            search_body["query"]["bool"]["filter"] = [
                {"term": {"source_institution": institution_filter}}
            ]
        
        try:
            response = await self.async_client.search(
                index=self.index_name,
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "document_id": hit["_source"]["document_id"],
                    "content": hit["_source"]["content"],
                    "score": hit["_score"],
                    "chunk_index": hit["_source"]["chunk_index"],
                    "page_number": hit["_source"]["page_number"],
                    "source_institution": hit["_source"]["source_institution"],
                    "metadata": hit["_source"]["metadata"]
                }
                results.append(result)
            
            logger.info(f"Hybrid search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            raise
    
    async def delete_document_embeddings(self, document_id: str) -> int:
        """Delete all embeddings for a document"""
        
        delete_query = {
            "query": {
                "term": {"document_id": document_id}
            }
        }
        
        try:
            response = await self.async_client.delete_by_query(
                index=self.index_name,
                body=delete_query
            )
            
            deleted_count = response["deleted"]
            logger.info(f"Deleted {deleted_count} embeddings for document {document_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            raise
    
    async def get_embeddings_count(self, document_id: Optional[str] = None) -> int:
        """Get total embeddings count or count for specific document"""
        
        if document_id:
            query = {"term": {"document_id": document_id}}
        else:
            query = {"match_all": {}}
        
        try:
            response = await self.async_client.count(
                index=self.index_name,
                body={"query": query}
            )
            
            return response["count"]
            
        except Exception as e:
            logger.error(f"Error getting embeddings count: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health"""
        
        try:
            # Cluster health
            health = self.client.cluster.health()
            
            # Index stats
            stats = self.client.indices.stats(index=self.index_name)
            
            # Index mapping info
            mapping = self.client.indices.get_mapping(index=self.index_name)
            vector_dims = mapping[self.index_name]["mappings"]["properties"]["embedding"]["dims"]
            
            return {
                "cluster_status": health["status"],
                "cluster_name": health["cluster_name"],
                "elasticsearch_version": health.get("version", {}).get("number", "unknown"),
                "index_name": self.index_name,
                "vector_dimensions": vector_dims,
                "document_count": stats["indices"][self.index_name]["total"]["docs"]["count"],
                "index_size": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "health": "ok"
            }
            
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {
                "health": "error",
                "error": str(e)
            }
    
    async def close(self):
        """Close Elasticsearch connections"""
        try:
            await self.async_client.close()
            self.client.close()
            logger.info("Elasticsearch connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")