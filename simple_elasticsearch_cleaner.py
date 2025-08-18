#!/usr/bin/env python3
"""
Simple Elasticsearch Embeddings Cleanup Script
===============================================
Elasticsearch'deki embeddings'leri temizleyen basit script.
Mevcut proje elasticsearch configuration'ını kullanır.
"""

import asyncio
import logging
import sys
import json
from datetime import datetime

import httpx
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleElasticsearchCleaner:
    """Simple HTTP-based Elasticsearch cleanup utility"""
    
    def __init__(self, es_url: str = "https://elastic.mevzuatgpt.org", db_url: str = None):
        self.es_url = es_url.rstrip('/')
        self.db_url = db_url
        self.http_client = None
        self.db_conn = None
    
    async def __aenter__(self):
        self.http_client = httpx.AsyncClient(verify=False, timeout=30.0)
        if self.db_url:
            try:
                self.db_conn = await asyncpg.connect(self.db_url)
                logger.info("Connected to PostgreSQL")
            except Exception as e:
                logger.warning(f"Could not connect to PostgreSQL: {e}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()
        if self.db_conn:
            await self.db_conn.close()
    
    async def get_cluster_info(self):
        """Get Elasticsearch cluster information"""
        try:
            response = await self.http_client.get(f"{self.es_url}/")
            if response.status_code == 200:
                info = response.json()
                logger.info(f"Connected to Elasticsearch: {info.get('version', {}).get('number', 'unknown')}")
                return info
            else:
                logger.error(f"Failed to connect: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return None
    
    async def list_indices(self):
        """List all indices with document counts"""
        try:
            response = await self.http_client.get(f"{self.es_url}/_cat/indices?format=json")
            if response.status_code == 200:
                indices = response.json()
                result = {}
                
                for index in indices:
                    index_name = index.get('index', '')
                    # Skip system indices (those starting with .)
                    if not index_name.startswith('.'):
                        result[index_name] = {
                            'document_count': int(index.get('docs.count', 0) or 0),
                            'size': index.get('store.size', '0b'),
                            'status': index.get('status', 'unknown')
                        }
                
                return result
            else:
                logger.error(f"Failed to list indices: HTTP {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Failed to list indices: {e}")
            return {}
    
    async def count_documents(self, index_name: str):
        """Count documents in specific index"""
        try:
            response = await self.http_client.get(f"{self.es_url}/{index_name}/_count")
            if response.status_code == 200:
                result = response.json()
                return result.get('count', 0)
            else:
                logger.error(f"Failed to count documents in {index_name}: HTTP {response.status_code}")
                return 0
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    async def clear_index(self, index_name: str):
        """Clear all documents from an index"""
        try:
            # First check if index exists and get document count
            doc_count = await self.count_documents(index_name)
            if doc_count == 0:
                logger.info(f"Index '{index_name}' is already empty")
                return True
            
            logger.info(f"Clearing {doc_count:,} documents from index '{index_name}'...")
            
            # Delete all documents using delete_by_query
            delete_body = {
                "query": {
                    "match_all": {}
                }
            }
            
            response = await self.http_client.post(
                f"{self.es_url}/{index_name}/_delete_by_query?wait_for_completion=true",
                json=delete_body,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                deleted = result.get('deleted', 0)
                logger.info(f"Successfully deleted {deleted:,} documents from '{index_name}'")
                
                # Refresh the index
                await self.http_client.post(f"{self.es_url}/{index_name}/_refresh")
                
                return True
            else:
                logger.error(f"Failed to clear index '{index_name}': HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear index '{index_name}': {e}")
            return False
    
    async def clear_all_user_indices(self, confirm: bool = False):
        """Clear all user indices (non-system indices)"""
        if not confirm:
            logger.error("Clear all requires explicit confirmation")
            return False
        
        try:
            indices = await self.list_indices()
            if not indices:
                logger.warning("No user indices found")
                return True
            
            total_docs_deleted = 0
            cleared_indices = []
            failed_indices = []
            
            for index_name, info in indices.items():
                doc_count = info['document_count']
                
                if doc_count > 0:
                    success = await self.clear_index(index_name)
                    if success:
                        cleared_indices.append(index_name)
                        total_docs_deleted += doc_count
                    else:
                        failed_indices.append(index_name)
                else:
                    logger.info(f"Skipping empty index '{index_name}'")
                    cleared_indices.append(index_name)
            
            # Log cleanup to database if connected
            if self.db_conn:
                await self.log_cleanup_to_db(total_docs_deleted, cleared_indices, failed_indices)
            
            logger.info(f"Cleanup complete: {total_docs_deleted:,} documents deleted from {len(cleared_indices)} indices")
            
            if failed_indices:
                logger.warning(f"Failed to clear indices: {failed_indices}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear all indices: {e}")
            return False
    
    async def log_cleanup_to_db(self, docs_deleted: int, cleared_indices: list, failed_indices: list):
        """Log cleanup operation to database"""
        try:
            status = 'completed' if not failed_indices else 'partial'
            details = f"Cleared {docs_deleted:,} documents from {len(cleared_indices)} indices"
            
            if failed_indices:
                details += f". Failed indices: {', '.join(failed_indices)}"
            
            await self.db_conn.execute('''
                INSERT INTO elasticsearch_sync_log (
                    operation_type, status, details, documents_affected, created_at
                ) VALUES ($1, $2, $3, $4, $5)
            ''', 'CLEANUP', status, details, docs_deleted, datetime.now())
            
            logger.info("Logged cleanup operation to database")
            
        except Exception as e:
            logger.warning(f"Failed to log to database: {e}")
    
    async def delete_documents_by_ids(self, doc_ids: list, index_name: str = "documents"):
        """Delete specific documents by their IDs"""
        try:
            deleted_count = 0
            failed_ids = []
            
            for doc_id in doc_ids:
                try:
                    response = await self.http_client.delete(f"{self.es_url}/{index_name}/_doc/{doc_id}")
                    
                    if response.status_code in [200, 404]:  # 404 means already deleted
                        deleted_count += 1
                        logger.info(f"Deleted document {doc_id}")
                    else:
                        logger.warning(f"Failed to delete {doc_id}: HTTP {response.status_code}")
                        failed_ids.append(doc_id)
                        
                except Exception as e:
                    logger.error(f"Error deleting document {doc_id}: {e}")
                    failed_ids.append(doc_id)
            
            # Refresh index
            await self.http_client.post(f"{self.es_url}/{index_name}/_refresh")
            
            logger.info(f"Document deletion complete: {deleted_count}/{len(doc_ids)} successful")
            
            return {
                "deleted_count": deleted_count,
                "failed_ids": failed_ids,
                "success": len(failed_ids) == 0
            }
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return {"deleted_count": 0, "failed_ids": doc_ids, "success": False}


async def main():
    """Main script execution"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Simple Elasticsearch embeddings cleanup')
    parser.add_argument('--action', choices=['info', 'clear-all', 'clear-index', 'clear-docs'], 
                       required=True, help='Action to perform')
    parser.add_argument('--index', help='Specific index name')
    parser.add_argument('--doc-ids', nargs='+', help='Document IDs to delete')
    parser.add_argument('--confirm', action='store_true', help='Confirm destructive operations')
    parser.add_argument('--es-url', default="https://elastic.mevzuatgpt.org", help='Elasticsearch URL')
    
    args = parser.parse_args()
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    
    try:
        async with SimpleElasticsearchCleaner(es_url=args.es_url, db_url=db_url) as cleaner:
            
            # Test connection first
            cluster_info = await cleaner.get_cluster_info()
            if not cluster_info:
                logger.error("Could not connect to Elasticsearch")
                sys.exit(1)
            
            if args.action == 'info':
                indices = await cleaner.list_indices()
                
                print(f"\n{'='*60}")
                print("ELASTICSEARCH INDICES INFORMATION")
                print(f"{'='*60}")
                
                total_docs = 0
                for index_name, info in indices.items():
                    doc_count = info['document_count']
                    total_docs += doc_count
                    print(f"Index: {index_name}")
                    print(f"  Documents: {doc_count:,}")
                    print(f"  Size: {info['size']}")
                    print(f"  Status: {info['status']}")
                    print()
                
                print(f"Total documents: {total_docs:,}")
            
            elif args.action == 'clear-all':
                if not args.confirm:
                    print("WARNING: This will delete ALL embeddings!")
                    print("Use --confirm to proceed")
                    sys.exit(1)
                
                success = await cleaner.clear_all_user_indices(confirm=True)
                if success:
                    print("SUCCESS: All indices cleared")
                else:
                    print("FAILED: Some indices could not be cleared")
                    sys.exit(1)
            
            elif args.action == 'clear-index':
                if not args.index:
                    print("ERROR: --index required")
                    sys.exit(1)
                
                if not args.confirm:
                    print(f"WARNING: This will delete all documents from '{args.index}'!")
                    print("Use --confirm to proceed")
                    sys.exit(1)
                
                success = await cleaner.clear_index(args.index)
                if success:
                    print(f"SUCCESS: Index '{args.index}' cleared")
                else:
                    print(f"FAILED: Could not clear index '{args.index}'")
                    sys.exit(1)
            
            elif args.action == 'clear-docs':
                if not args.doc_ids:
                    print("ERROR: --doc-ids required")
                    sys.exit(1)
                
                index_name = args.index or "documents"
                result = await cleaner.delete_documents_by_ids(args.doc_ids, index_name)
                
                if result["success"]:
                    print(f"SUCCESS: Deleted {result['deleted_count']} documents")
                else:
                    print(f"PARTIAL: Deleted {result['deleted_count']}, failed: {len(result['failed_ids'])}")
                    if result['failed_ids']:
                        print(f"Failed IDs: {result['failed_ids']}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())