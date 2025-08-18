#!/usr/bin/env python3
"""
Elasticsearch Embeddings Cleanup Script
========================================
This script safely clears all document embeddings from Elasticsearch while preserving indices.
Supports both development and production environments with safety checks.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElasticsearchCleaner:
    """Elasticsearch embeddings cleanup utility"""
    
    def __init__(self, elasticsearch_url: str = None, database_url: str = None):
        self.es_url = elasticsearch_url or "https://elastic.mevzuatgpt.org"
        self.db_url = database_url or os.getenv("DATABASE_URL")
        self.es_client: Optional[AsyncElasticsearch] = None
        self.db_conn: Optional[asyncpg.Connection] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Establish connections to Elasticsearch and PostgreSQL"""
        try:
            # Connect to Elasticsearch
            self.es_client = AsyncElasticsearch(
                hosts=[self.es_url],
                verify_certs=False
            )
            
            # Test Elasticsearch connection
            info = await self.es_client.info()
            logger.info(f"Connected to Elasticsearch: {info['version']['number']}")
            
            # Connect to PostgreSQL
            if self.db_url:
                self.db_conn = await asyncpg.connect(self.db_url)
                logger.info("Connected to PostgreSQL database")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close all connections"""
        if self.es_client:
            await self.es_client.close()
        if self.db_conn:
            await self.db_conn.close()
    
    async def get_indices_info(self) -> Dict[str, Any]:
        """Get information about existing indices"""
        try:
            indices = await self.es_client.cat.indices(format='json')
            
            result = {}
            for index in indices:
                index_name = index['index']
                doc_count = int(index['docs.count'] or 0)
                size = index['store.size'] or '0b'
                
                result[index_name] = {
                    'document_count': doc_count,
                    'size': size,
                    'status': index['status']
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get indices info: {e}")
            return {}
    
    async def clear_index(self, index_name: str, batch_size: int = 1000) -> bool:
        """Clear all documents from a specific index"""
        try:
            logger.info(f"Starting cleanup of index: {index_name}")
            
            # Check if index exists
            if not await self.es_client.indices.exists(index=index_name):
                logger.warning(f"Index {index_name} does not exist")
                return False
            
            # Get initial document count
            initial_count = await self.es_client.count(index=index_name)
            initial_docs = initial_count['count']
            
            if initial_docs == 0:
                logger.info(f"Index {index_name} is already empty")
                return True
            
            logger.info(f"Found {initial_docs} documents in {index_name}")
            
            # Delete all documents using delete_by_query
            response = await self.es_client.delete_by_query(
                index=index_name,
                body={
                    "query": {
                        "match_all": {}
                    }
                },
                wait_for_completion=True,
                timeout="5m"
            )
            
            deleted_count = response.get('deleted', 0)
            logger.info(f"Deleted {deleted_count} documents from {index_name}")
            
            # Refresh index to ensure changes are visible
            await self.es_client.indices.refresh(index=index_name)
            
            # Verify deletion
            final_count = await self.es_client.count(index=index_name)
            final_docs = final_count['count']
            
            if final_docs == 0:
                logger.info(f"Successfully cleared index {index_name}")
                return True
            else:
                logger.warning(f"Index {index_name} still has {final_docs} documents")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear index {index_name}: {e}")
            return False
    
    async def clear_all_embeddings(self, confirm: bool = False) -> Dict[str, Any]:
        """Clear all embeddings from all indices"""
        if not confirm:
            logger.error("Clear all embeddings requires explicit confirmation")
            return {"success": False, "error": "Confirmation required"}
        
        try:
            # Get all indices
            indices_info = await self.get_indices_info()
            
            results = {
                "cleared_indices": [],
                "failed_indices": [],
                "total_documents_deleted": 0,
                "total_indices_processed": 0
            }
            
            # Filter out system indices (those starting with .)
            user_indices = [name for name in indices_info.keys() if not name.startswith('.')]
            
            logger.info(f"Found {len(user_indices)} user indices to clear")
            
            for index_name in user_indices:
                initial_docs = indices_info[index_name]['document_count']
                
                success = await self.clear_index(index_name)
                
                if success:
                    results["cleared_indices"].append({
                        "name": index_name,
                        "documents_deleted": initial_docs
                    })
                    results["total_documents_deleted"] += initial_docs
                else:
                    results["failed_indices"].append(index_name)
                
                results["total_indices_processed"] += 1
            
            # Update database sync status if connected
            if self.db_conn:
                await self.update_sync_status(results)
            
            return {
                "success": True,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to clear all embeddings: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_sync_status(self, results: Dict[str, Any]):
        """Update database sync log after clearing embeddings"""
        try:
            # Insert cleanup record into elasticsearch_sync_log
            await self.db_conn.execute('''
                INSERT INTO elasticsearch_sync_log (
                    operation_type,
                    status,
                    details,
                    documents_affected,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5)
            ''', 
            'CLEANUP',
            'completed' if len(results["failed_indices"]) == 0 else 'partial',
            f"Cleared {results['total_documents_deleted']} documents from {len(results['cleared_indices'])} indices",
            results["total_documents_deleted"],
            datetime.now()
            )
            
            logger.info("Updated database sync status")
            
        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")
    
    async def clear_specific_documents(self, document_ids: list, index_name: str = "documents") -> Dict[str, Any]:
        """Clear specific documents by their IDs"""
        try:
            deleted_count = 0
            failed_ids = []
            
            for doc_id in document_ids:
                try:
                    response = await self.es_client.delete(
                        index=index_name,
                        id=doc_id,
                        ignore=[404]
                    )
                    
                    if response.get('result') == 'deleted':
                        deleted_count += 1
                        logger.info(f"Deleted document {doc_id}")
                    else:
                        logger.warning(f"Document {doc_id} not found or already deleted")
                        
                except Exception as e:
                    logger.error(f"Failed to delete document {doc_id}: {e}")
                    failed_ids.append(doc_id)
            
            # Refresh index
            await self.es_client.indices.refresh(index=index_name)
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "failed_ids": failed_ids,
                "total_requested": len(document_ids)
            }
            
        except Exception as e:
            logger.error(f"Failed to clear specific documents: {e}")
            return {"success": False, "error": str(e)}


async def main():
    """Main script execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear Elasticsearch embeddings')
    parser.add_argument('--action', choices=['info', 'clear-all', 'clear-index', 'clear-docs'], 
                       required=True, help='Action to perform')
    parser.add_argument('--index', help='Specific index name (for clear-index)')
    parser.add_argument('--doc-ids', nargs='+', help='Document IDs to delete (for clear-docs)')
    parser.add_argument('--confirm', action='store_true', 
                       help='Confirm destructive operations')
    parser.add_argument('--es-url', default="https://elastic.mevzuatgpt.org",
                       help='Elasticsearch URL')
    
    args = parser.parse_args()
    
    try:
        async with ElasticsearchCleaner(elasticsearch_url=args.es_url) as cleaner:
            
            if args.action == 'info':
                logger.info("Getting Elasticsearch indices information...")
                indices_info = await cleaner.get_indices_info()
                
                print(f"\n{'='*60}")
                print("ELASTICSEARCH INDICES INFORMATION")
                print(f"{'='*60}")
                
                total_docs = 0
                for index_name, info in indices_info.items():
                    if not index_name.startswith('.'):  # Skip system indices
                        doc_count = info['document_count']
                        total_docs += doc_count
                        print(f"Index: {index_name}")
                        print(f"  Documents: {doc_count:,}")
                        print(f"  Size: {info['size']}")
                        print(f"  Status: {info['status']}")
                        print()
                
                print(f"Total user documents: {total_docs:,}")
            
            elif args.action == 'clear-all':
                if not args.confirm:
                    print("\nWARNING: This will delete ALL embeddings from Elasticsearch!")
                    print("Use --confirm flag to proceed")
                    sys.exit(1)
                
                logger.info("Clearing all embeddings from Elasticsearch...")
                result = await cleaner.clear_all_embeddings(confirm=True)
                
                if result["success"]:
                    print(f"\nSUCCESS: Cleared {result['results']['total_documents_deleted']:,} documents")
                    print(f"Cleared indices: {len(result['results']['cleared_indices'])}")
                    if result['results']['failed_indices']:
                        print(f"Failed indices: {result['results']['failed_indices']}")
                else:
                    print(f"FAILED: {result['error']}")
                    sys.exit(1)
            
            elif args.action == 'clear-index':
                if not args.index:
                    print("ERROR: --index parameter required for clear-index")
                    sys.exit(1)
                
                if not args.confirm:
                    print(f"\nWARNING: This will delete all documents from index '{args.index}'!")
                    print("Use --confirm flag to proceed")
                    sys.exit(1)
                
                success = await cleaner.clear_index(args.index)
                if success:
                    print(f"SUCCESS: Cleared index '{args.index}'")
                else:
                    print(f"FAILED: Could not clear index '{args.index}'")
                    sys.exit(1)
            
            elif args.action == 'clear-docs':
                if not args.doc_ids:
                    print("ERROR: --doc-ids parameter required for clear-docs")
                    sys.exit(1)
                
                index_name = args.index or "documents"
                result = await cleaner.clear_specific_documents(args.doc_ids, index_name)
                
                if result["success"]:
                    print(f"SUCCESS: Deleted {result['deleted_count']} out of {result['total_requested']} documents")
                    if result['failed_ids']:
                        print(f"Failed IDs: {result['failed_ids']}")
                else:
                    print(f"FAILED: {result['error']}")
                    sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())