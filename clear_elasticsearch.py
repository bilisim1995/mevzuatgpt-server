#!/usr/bin/env python3
"""
Clear all embeddings from Elasticsearch for fresh testing
"""
import asyncio
import logging
from services.elasticsearch_service import ElasticsearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_elasticsearch():
    """Clear all embeddings from Elasticsearch"""
    try:
        # Initialize Elasticsearch service
        es_service = ElasticsearchService()
        
        logger.info("🧹 Connecting to Elasticsearch...")
        
        # Get current document count
        count_response = await es_service.es.count(index="mevzuat_embeddings")
        current_count = count_response['count']
        
        logger.info(f"📊 Current embeddings count: {current_count}")
        
        if current_count == 0:
            logger.info("✅ Elasticsearch already empty")
            return
        
        # Delete all documents
        logger.info("🗑️ Deleting all embeddings...")
        delete_response = await es_service.es.delete_by_query(
            index="mevzuat_embeddings",
            body={
                "query": {
                    "match_all": {}
                }
            }
        )
        
        deleted_count = delete_response['deleted']
        logger.info(f"✅ Deleted {deleted_count} embeddings")
        
        # Verify cleanup
        final_count_response = await es_service.es.count(index="mevzuat_embeddings")
        final_count = final_count_response['count']
        
        logger.info(f"📊 Final count: {final_count}")
        
        if final_count == 0:
            logger.info("🎉 Elasticsearch successfully cleared!")
        else:
            logger.warning(f"⚠️ Still {final_count} documents remaining")
            
    except Exception as e:
        logger.error(f"Failed to clear Elasticsearch: {e}")

if __name__ == "__main__":
    asyncio.run(clear_elasticsearch())