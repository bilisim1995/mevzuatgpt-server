#!/usr/bin/env python3
"""
Clear Elasticsearch embeddings using existing service
"""
import asyncio
import sys
sys.path.append('.')
from services.elasticsearch_service import ElasticsearchService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_elasticsearch():
    """Clear all embeddings from Elasticsearch"""
    es_service = ElasticsearchService()
    
    try:
        # Check current count first
        session = await es_service._get_session()
        
        logger.info("Checking current embedding count...")
        
        async with session.get(f"{es_service.elasticsearch_url}/{es_service.index_name}/_count") as response:
            if response.status == 200:
                count_data = await response.json()
                current_count = count_data.get('count', 0)
                logger.info(f"Current embeddings: {current_count}")
                
                if current_count == 0:
                    logger.info("✅ Elasticsearch already empty")
                    return
                    
                # Delete all documents
                logger.info("Deleting all embeddings...")
                
                delete_query = {
                    "query": {
                        "match_all": {}
                    }
                }
                
                async with session.post(
                    f"{es_service.elasticsearch_url}/{es_service.index_name}/_delete_by_query?conflicts=proceed",
                    json=delete_query
                ) as delete_response:
                    if delete_response.status == 200:
                        delete_data = await delete_response.json()
                        deleted_count = delete_data.get('deleted', 0)
                        logger.info(f"✅ Deleted {deleted_count} embeddings")
                        
                        # Final verification
                        async with session.get(f"{es_service.elasticsearch_url}/{es_service.index_name}/_count") as final_response:
                            if final_response.status == 200:
                                final_data = await final_response.json()
                                final_count = final_data.get('count', 0)
                                logger.info(f"Final count: {final_count}")
                                
                                if final_count == 0:
                                    print("🎉 Elasticsearch successfully cleared!")
                                else:
                                    print(f"⚠️ Still {final_count} documents remaining")
                    else:
                        logger.error(f"Delete failed: HTTP {delete_response.status}")
                        
            elif response.status == 404:
                logger.info("✅ Index does not exist - nothing to clear")
            else:
                logger.error(f"Count request failed: HTTP {response.status}")
                
    except Exception as e:
        logger.error(f"Error clearing Elasticsearch: {e}")
    finally:
        await es_service.close_session()

if __name__ == "__main__":
    asyncio.run(clear_elasticsearch())