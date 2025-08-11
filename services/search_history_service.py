"""
Search history service for user query history management
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from models.database import SearchLog
from models.search_history_schemas import SearchHistoryItem, SearchHistoryResponse, SearchHistoryFilters
from core.supabase_client import supabase_client

logger = logging.getLogger(__name__)


class SearchHistoryService:
    """Service for managing user search history"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.supabase = supabase_client.service_client  # Use service client for RLS bypass
    
    async def get_user_search_history(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        filters: Optional[SearchHistoryFilters] = None
    ) -> SearchHistoryResponse:
        """
        Get paginated search history for a user
        
        Args:
            user_id: User's UUID
            page: Page number (1-based)
            limit: Items per page
            filters: Optional filters for search history
            
        Returns:
            Paginated search history response
        """
        try:
            # Build base query
            query_builder = self.supabase.table('search_logs') \
                .select('''
                    id, query, response, sources, reliability_score, 
                    credits_used, institution_filter, results_count, 
                    execution_time, created_at
                ''') \
                .eq('user_id', str(user_id))
            
            # Apply filters
            if filters:
                if filters.institution:
                    query_builder = query_builder.eq('institution_filter', filters.institution)
                
                if filters.date_from:
                    query_builder = query_builder.gte('created_at', filters.date_from.isoformat())
                
                if filters.date_to:
                    query_builder = query_builder.lte('created_at', filters.date_to.isoformat())
                
                if filters.min_reliability is not None:
                    query_builder = query_builder.gte('reliability_score', filters.min_reliability)
                
                if filters.search_query:
                    query_builder = query_builder.ilike('query', f'%{filters.search_query}%')
            
            # Get total count
            count_response = self.supabase.table('search_logs') \
                .select('*', count='exact', head=True) \
                .eq('user_id', str(user_id))
            
            if filters:
                if filters.institution:
                    count_response = count_response.eq('institution_filter', filters.institution)
                if filters.date_from:
                    count_response = count_response.gte('created_at', filters.date_from.isoformat())
                if filters.date_to:
                    count_response = count_response.lte('created_at', filters.date_to.isoformat())
                if filters.min_reliability is not None:
                    count_response = count_response.gte('reliability_score', filters.min_reliability)
                if filters.search_query:
                    count_response = count_response.ilike('query', f'%{filters.search_query}%')
            
            # Execute count query
            count_result = count_response.execute()
            total_count = count_result.count if count_result.count is not None else 0
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query_builder = query_builder \
                .order('created_at', desc=True) \
                .range(offset, offset + limit - 1)
            
            # Execute main query
            result = query_builder.execute()
            
            # Convert to response models
            items = []
            if result.data:
                for row in result.data:
                    items.append(SearchHistoryItem(
                        id=str(row['id']),
                        query=row['query'],
                        response=row.get('response'),
                        sources=row.get('sources'),
                        reliability_score=row.get('reliability_score'),
                        credits_used=row.get('credits_used', 0),
                        institution_filter=row.get('institution_filter'),
                        results_count=row.get('results_count', 0),
                        execution_time=row.get('execution_time'),
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if isinstance(row['created_at'], str) else row['created_at']
                    ))
            
            has_more = total_count > (page * limit)
            
            logger.info(f"Retrieved {len(items)} search history items for user {user_id}")
            
            return SearchHistoryResponse(
                items=items,
                total_count=total_count,
                page=page,
                limit=limit,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(f"Error retrieving search history for user {user_id}: {e}")
            return SearchHistoryResponse(
                items=[],
                total_count=0,
                page=page,
                limit=limit,
                has_more=False
            )
    
    async def get_search_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's search statistics
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dictionary with search statistics
        """
        try:
            # Get basic stats
            stats_response = self.supabase.table('search_logs') \
                .select('id, credits_used, reliability_score, institution_filter, created_at') \
                .eq('user_id', str(user_id)) \
                .execute()
            
            if not stats_response.data:
                return {
                    'total_searches': 0,
                    'total_credits_used': 0,
                    'average_reliability': 0.0,
                    'most_used_institution': None,
                    'searches_this_month': 0,
                    'searches_today': 0
                }
            
            # Calculate statistics
            data = stats_response.data
            total_searches = len(data)
            total_credits = sum(row.get('credits_used', 0) for row in data)
            
            # Average reliability (only for searches with reliability scores)
            reliability_scores = [row['reliability_score'] for row in data if row.get('reliability_score') is not None]
            avg_reliability = sum(reliability_scores) / len(reliability_scores) if reliability_scores else 0.0
            
            # Most used institution
            institutions = [row['institution_filter'] for row in data if row.get('institution_filter')]
            most_used_institution = max(set(institutions), key=institutions.count) if institutions else None
            
            # Time-based counts
            from datetime import timezone
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            searches_today = 0
            searches_this_month = 0
            
            for row in data:
                created_at_str = row['created_at']
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                else:
                    created_at = created_at_str
                
                # Convert to UTC for comparison if needed
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at >= today_start:
                    searches_today += 1
                if created_at >= month_start:
                    searches_this_month += 1
            
            return {
                'total_searches': total_searches,
                'total_credits_used': total_credits,
                'average_reliability': round(avg_reliability, 2),
                'most_used_institution': most_used_institution,
                'searches_this_month': searches_this_month,
                'searches_today': searches_today
            }
            
        except Exception as e:
            logger.error(f"Error getting search statistics for user {user_id}: {e}")
            return {
                'total_searches': 0,
                'total_credits_used': 0,
                'average_reliability': 0.0,
                'most_used_institution': None,
                'searches_this_month': 0,
                'searches_today': 0
            }

    async def log_search_result(
        self,
        user_id: str,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        reliability_score: float,
        credits_used: int,
        institution_filter: Optional[str] = None,
        results_count: int = 0,
        execution_time: Optional[float] = None
    ) -> bool:
        """
        Log a search result to the database
        
        Args:
            user_id: User's UUID
            query: Search query
            response: AI response
            sources: List of source documents
            reliability_score: Reliability score (0.0-1.0)
            credits_used: Credits consumed
            institution_filter: Institution filter used
            results_count: Number of results
            execution_time: Time taken for search
            
        Returns:
            Success status
        """
        try:
            log_data = {
                'user_id': str(user_id),
                'query': query,
                'response': response,
                'sources': sources,
                'reliability_score': reliability_score,
                'credits_used': credits_used,
                'institution_filter': institution_filter,
                'results_count': results_count,
                'execution_time': execution_time
            }
            
            result = self.supabase.table('search_logs').insert(log_data).execute()
            
            if result.data:
                logger.info(f"Logged search result for user {user_id}: '{query[:50]}...'")
                return True
            else:
                logger.error(f"Failed to log search result for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error logging search result for user {user_id}: {e}")
            return False