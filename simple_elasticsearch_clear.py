#!/usr/bin/env python3
"""
Simple Elasticsearch cleanup script
"""
import os
import asyncio
from elasticsearch import AsyncElasticsearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_elasticsearch_simple():
    """Clear Elasticsearch embeddings"""
    try:
        # Create Elasticsearch client
        es_host = "https://elastic.mevzuatgpt.org"
        es = AsyncElasticsearch([es_host])
        
        logger.info(f"Connecting to {es_host}...")
        
        # Check if index exists
        index_exists = await es.indices.exists(index="mevzuat_embeddings")
        
        if not index_exists:
            logger.info("Index 'mevzuat_embeddings' does not exist")
            await es.close()
            return
            
        # Get count
        count_resp = await es.count(index="mevzuat_embeddings")
        count = count_resp['count']
        logger.info(f"Current embeddings: {count}")
        
        if count > 0:
            # Delete all documents
            logger.info("Deleting all embeddings...")
            delete_resp = await es.delete_by_query(
                index="mevzuat_embeddings",
                body={"query": {"match_all": {}}},
                conflicts="proceed"
            )
            
            deleted = delete_resp.get('deleted', 0)
            logger.info(f"Deleted {deleted} embeddings")
        
        # Final verification
        final_count_resp = await es.count(index="mevzuat_embeddings")
        final_count = final_count_resp['count']
        logger.info(f"Final count: {final_count}")
        
        await es.close()
        logger.info("Elasticsearch cleanup completed")
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(clear_elasticsearch_simple())