"""
Chat endpoints using enhanced LangChain capabilities
Conversational RAG and document summarization
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import logging
import uuid

from api.dependencies import get_current_user
from services.chat_service import ChatService, DocumentSummarizer
from models.schemas import UserResponse
from utils.response import success_response
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
router = APIRouter()

class ConversationRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None

class ConversationResponse(BaseModel):
    response: str
    sources: List[str]
    context_chunks: int
    conversation_id: Optional[str]

class SummaryResponse(BaseModel):
    document_id: str
    summary: str
    total_chunks: int
    total_length: int

@router.post("/conversation", response_model=ConversationResponse)
async def conversational_chat(
    request: ConversationRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Enhanced conversational chat with memory and context
    Uses LangChain for conversation management
    """
    try:
        chat_service = ChatService()
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        result = await chat_service.get_conversational_response(
            query=request.query,
            user_id=current_user.id,
            conversation_id=conversation_id
        )
        
        return success_response(data=result)
        
    except AppException as e:
        logger.error(f"Conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected conversation error: {e}")
        raise HTTPException(status_code=500, detail="Conversation failed")

@router.post("/summarize/{document_id}", response_model=SummaryResponse)
async def summarize_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Summarize a document using LangChain
    Provides intelligent document overview
    """
    try:
        summarizer = DocumentSummarizer()
        
        result = await summarizer.summarize_document(document_id)
        
        return success_response(data=result)
        
    except AppException as e:
        logger.error(f"Summarization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected summarization error: {e}")
        raise HTTPException(status_code=500, detail="Summarization failed")

@router.get("/conversations")
async def get_conversations(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 10
):
    """
    Get user's conversation history
    """
    try:
        from models.supabase_client import supabase_client
        
        response = supabase_client.supabase.table('search_logs').select(
            'conversation_id, query, response, created_at'
        ).eq('user_id', current_user.id).order('created_at', desc=True).limit(limit).execute()
        
        # Group by conversation_id
        conversations = {}
        for log in response.data:
            conv_id = log['conversation_id']
            if conv_id not in conversations:
                conversations[conv_id] = {
                    'conversation_id': conv_id,
                    'last_message': log['query'],
                    'last_updated': log['created_at'],
                    'message_count': 0
                }
            conversations[conv_id]['message_count'] += 1
        
        return success_response(data={
            'conversations': list(conversations.values()),
            'total': len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")

@router.get("/conversations/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get specific conversation history
    """
    try:
        from models.supabase_client import supabase_client
        
        response = supabase_client.supabase.table('search_logs').select('*').eq(
            'conversation_id', conversation_id
        ).eq('user_id', current_user.id).order('created_at').execute()
        
        return success_response(data={
            'conversation_id': conversation_id,
            'messages': response.data,
            'total_messages': len(response.data)
        })
        
    except Exception as e:
        logger.error(f"Get conversation history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation history")