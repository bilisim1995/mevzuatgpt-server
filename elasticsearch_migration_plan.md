# MevzuatGPT Elasticsearch Vector Migration Plan

## Overview
Migration from Supabase pgvector to Elasticsearch for vector search due to persistent platform-level encoding corruption in Supabase pgvector extension.

## Why Elasticsearch?
- **HNSW Performance**: 40x faster indexing, sub-100ms queries
- **Memory Efficiency**: 75% reduction with int8_hnsw quantization  
- **Production Proven**: Used by thousands of companies globally
- **No Encoding Issues**: Reliable vector storage/retrieval
- **1536 Dimension Optimized**: Perfect for text-embedding-3-small

## Implementation Architecture

### 1. Elasticsearch Index Configuration
```json
{
  "mappings": {
    "properties": {
      "document_id": {"type": "keyword"},
      "content": {"type": "text"},
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine",
        "index_options": {
          "type": "int8_hnsw",
          "m": 32,
          "ef_construction": 200
        }
      },
      "chunk_index": {"type": "integer"},
      "page_number": {"type": "integer"},
      "line_start": {"type": "integer"},
      "line_end": {"type": "integer"},
      "source_institution": {"type": "keyword"},
      "source_document": {"type": "keyword"},
      "metadata": {"type": "object"},
      "created_at": {"type": "date"}
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index.max_result_window": 50000
  }
}
```

### 2. Python Integration
```python
from elasticsearch import Elasticsearch
import numpy as np

class ElasticsearchEmbeddingService:
    def __init__(self):
        self.client = Elasticsearch([
            {"host": "localhost", "port": 9200}
        ])
        self.index_name = "mevzuat_embeddings"
    
    async def create_embedding(self, document_id: str, content: str, 
                              embedding: List[float], **metadata):
        doc = {
            "document_id": document_id,
            "content": content,
            "embedding": embedding,
            "chunk_index": metadata.get("chunk_index", 0),
            "page_number": metadata.get("page_number"),
            "line_start": metadata.get("line_start"),
            "line_end": metadata.get("line_end"),
            "source_institution": metadata.get("source_institution"),
            "source_document": metadata.get("source_document"),
            "metadata": metadata,
            "created_at": datetime.utcnow()
        }
        
        response = self.client.index(
            index=self.index_name,
            body=doc
        )
        return response["_id"]
    
    async def similarity_search(self, query_vector: List[float], 
                               k: int = 10, 
                               institution_filter: str = None,
                               threshold: float = 0.7):
        
        # Build query
        knn_query = {
            "field": "embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": k * 10
        }
        
        # Add institution filter
        search_body = {"knn": knn_query}
        if institution_filter:
            search_body["query"] = {
                "bool": {
                    "filter": [
                        {"term": {"source_institution": institution_filter}}
                    ]
                }
            }
        
        response = self.client.search(
            index=self.index_name,
            body=search_body,
            _source=["document_id", "content", "page_number", 
                    "source_document", "metadata"]
        )
        
        # Filter by threshold
        results = []
        for hit in response["hits"]["hits"]:
            score = hit["_score"]
            # Convert Elasticsearch score to similarity (approximate)
            similarity = 1 / (1 + score) if score > 0 else 0
            
            if similarity >= threshold:
                results.append({
                    "document_id": hit["_source"]["document_id"],
                    "content": hit["_source"]["content"],
                    "similarity": similarity,
                    "page_number": hit["_source"]["page_number"],
                    "source_document": hit["_source"]["source_document"],
                    "metadata": hit["_source"]["metadata"]
                })
        
        return results
```

### 3. Migration Strategy

#### Phase 1: Infrastructure Setup (1-2 days)
- **Elasticsearch Installation**: Docker/Cloud deployment
- **Index Creation**: Configure optimal settings for 1536D vectors
- **Performance Tuning**: Memory allocation, JVM settings
- **Testing**: Basic CRUD operations and similarity search

#### Phase 2: Application Integration (2-3 days)
- **Service Layer**: Replace Supabase embedding service
- **Search Service**: Update similarity search logic
- **Query Service**: Integrate new search results
- **Testing**: End-to-end functionality verification

#### Phase 3: Data Migration (1 day)
- **Export**: Current embeddings from Supabase (203 vectors)
- **Transform**: Convert to Elasticsearch format
- **Import**: Bulk insert with proper formatting
- **Validation**: Verify data integrity and search quality

#### Phase 4: Production Deployment (1 day)
- **Configuration**: Production Elasticsearch cluster
- **Monitoring**: Set up logging and alerting
- **Performance**: Load testing and optimization
- **Rollback Plan**: Maintain Supabase as backup during transition

## Expected Performance Improvements

### Memory Usage
- **Current (Supabase)**: ~6KB per vector (corrupted)
- **Elasticsearch int8_hnsw**: ~1.6KB per vector
- **203 vectors**: 325KB vs 1.2MB (75% reduction)

### Query Performance
- **Current**: 0 results (dimension corruption)
- **Elasticsearch**: Sub-100ms response time
- **Scaling**: Efficient handling of millions of vectors

### Search Quality
- **Current**: Broken similarity search
- **Elasticsearch**: High-quality cosine similarity
- **Institution Filtering**: Native support with bool queries

## Implementation Code Changes

### services/embedding_service.py
```python
# Replace Supabase client with Elasticsearch client
from .elasticsearch_embedding_service import ElasticsearchEmbeddingService

class EmbeddingService:
    def __init__(self):
        self.es_service = ElasticsearchEmbeddingService()
    
    async def create_embedding_with_sources(self, ...):
        return await self.es_service.create_embedding(...)
    
    async def search_similar_embeddings(self, ...):
        return await self.es_service.similarity_search(...)
```

### services/search_service.py
```python
# Update search logic for Elasticsearch
async def semantic_search(self, query: str, institution_filter: str = None):
    # Generate query embedding (unchanged)
    query_embedding = await self.openai_service.create_embedding(query)
    
    # Search with Elasticsearch (new)
    results = await self.embedding_service.search_similar_embeddings(
        query_vector=query_embedding,
        k=self.config.search_limit,
        institution_filter=institution_filter,
        threshold=self.config.similarity_threshold
    )
    
    return results
```

## Deployment Configuration

### Docker Compose
```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms2g -Xmx2g
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    
volumes:
  elasticsearch_data:
```

### Production Settings
```json
{
  "index.max_result_window": 50000,
  "index.refresh_interval": "1s",
  "index.number_of_shards": 3,
  "index.number_of_replicas": 1,
  "index.codec": "best_compression"
}
```

## Testing & Validation Plan

### 1. Unit Tests
- Elasticsearch connection and CRUD operations
- Vector similarity search accuracy
- Institution filtering functionality
- Error handling and edge cases

### 2. Integration Tests  
- End-to-end search pipeline
- Performance under load
- Data migration accuracy
- Fallback mechanisms

### 3. Performance Benchmarks
- Query latency measurements
- Memory usage monitoring
- Throughput testing
- Scaling characteristics

## Risk Mitigation

### Data Loss Prevention
- Complete backup of existing embeddings
- Parallel operation during migration
- Rollback procedures documented

### Performance Monitoring
- Query latency alerts
- Memory usage thresholds
- Error rate monitoring
- User satisfaction metrics

### Operational Readiness
- Team training on Elasticsearch operations
- Documentation updates
- Monitoring dashboard setup
- Incident response procedures

## Timeline & Resources

**Total Estimated Time**: 5-7 days
**Resources Required**: 
- 1 Senior Developer (full-time)
- 1 DevOps Engineer (part-time)
- Elasticsearch infrastructure (cloud/on-premise)

**Success Criteria**:
- Vector search functional with 1536 dimensions
- Query response time < 100ms
- Search quality matches or exceeds expectations
- Zero data loss during migration
- Production stability maintained

## Conclusion

Elasticsearch provides a robust, production-proven solution for MevzuatGPT's vector search needs. The migration addresses the fundamental Supabase pgvector encoding corruption while improving performance, reducing memory usage, and providing a scalable foundation for future growth.