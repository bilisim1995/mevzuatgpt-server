"""
Chat service using LangChain for conversational RAG
Provides context-aware responses using document embeddings
"""

import logging
from typing import List, Dict, Any, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.llms.base import LLM
from langchain.embeddings.base import Embeddings
import openai
from core.config import settings
from models.supabase_client import supabase_client
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class OpenAIWrapper(LLM):
    """OpenAI LLM wrapper for LangChain"""
    
    def __init__(self):
        super().__init__()
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Call OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise AppException("Chat response generation failed", str(e))
    
    @property
    def _llm_type(self) -> str:
        return "openai"

class SupabaseRetriever:
    """Custom retriever for Supabase vector search"""
    
    def __init__(self, k: int = 5):
        self.k = k
    
    async def get_relevant_documents(self, query: str) -> List[Dict]:
        """Retrieve relevant documents from Supabase"""
        try:
            # Generate query embedding
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
                encoding_format="float"
            )
            query_embedding = response.data[0].embedding
            
            # Search in Supabase
            results = await supabase_client.search_embeddings(
                query_text=query,
                limit=self.k,
                similarity_threshold=0.7
            )
            
            return results
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []

class ChatService:
    """Enhanced chat service with LangChain conversation capabilities"""
    
    def __init__(self):
        self.llm = OpenAIWrapper()
        self.retriever = SupabaseRetriever()
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=5  # Keep last 5 exchanges
        )
    
    async def get_conversational_response(
        self, 
        query: str, 
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get conversational response with context"""
        try:
            # Retrieve relevant documents
            relevant_docs = await self.retriever.get_relevant_documents(query)
            
            # Build context from retrieved documents
            context = self._build_context(relevant_docs)
            
            # Get chat history if conversation_id provided
            chat_history = await self._get_chat_history(conversation_id) if conversation_id else []
            
            # Create enhanced prompt with context
            enhanced_prompt = self._create_enhanced_prompt(query, context, chat_history)
            
            # Generate response
            response = self.llm._call(enhanced_prompt)
            
            # Save conversation
            if conversation_id:
                await self._save_conversation_turn(conversation_id, query, response, user_id)
            
            return {
                "response": response,
                "sources": [doc.get('document_title', 'Unknown') for doc in relevant_docs],
                "context_chunks": len(relevant_docs),
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Conversational response failed: {e}")
            raise AppException("Failed to generate conversational response", str(e))
    
    def _build_context(self, documents: List[Dict]) -> str:
        """Build context string from retrieved documents"""
        if not documents:
            return "İlgili belge bulunamadı."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            title = doc.get('document_title', 'Bilinmeyen Belge')
            content = doc.get('content', '')
            context_parts.append(f"Kaynak {i} ({title}):\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _create_enhanced_prompt(self, query: str, context: str, chat_history: List[Dict]) -> str:
        """Create enhanced prompt with context and history"""
        history_text = ""
        if chat_history:
            history_parts = []
            for turn in chat_history[-3:]:  # Last 3 turns
                history_parts.append(f"Kullanıcı: {turn['query']}")
                history_parts.append(f"Asistan: {turn['response']}")
            history_text = "\n".join(history_parts) + "\n\n"
        
        prompt = f"""Sen bir hukuki belge analiz asistanısın. Aşağıdaki bağlam bilgilerini ve sohbet geçmişini kullanarak soruya cevap ver.

{history_text}BAĞLAM BİLGİLERİ:
{context}

SORU: {query}

KURALLAR:
1. Sadece verilen bağlam bilgilerini kullan
2. Eğer cevap bağlamda yoksa, "Bu konuda verilen belgelerde bilgi bulunamadı" de
3. Cevabını kaynaklarla destekle
4. Türkçe ve anlaşılır bir dille yanıtla
5. Sohbet geçmişini dikkate alarak tutarlı cevap ver

CEVAP:"""
        
        return prompt
    
    async def _get_chat_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history from database"""
        try:
            # Get from Supabase search_logs or create conversation table
            response = supabase_client.supabase.table('search_logs').select('*').eq('conversation_id', conversation_id).order('created_at').execute()
            return response.data if response.data else []
        except Exception as e:
            logger.warning(f"Failed to get chat history: {e}")
            return []
    
    async def _save_conversation_turn(self, conversation_id: str, query: str, response: str, user_id: str):
        """Save conversation turn to database"""
        try:
            supabase_client.supabase.table('search_logs').insert({
                'conversation_id': conversation_id,
                'user_id': user_id,
                'query': query,
                'response': response,
                'query_type': 'conversational'
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save conversation: {e}")

class DocumentSummarizer:
    """Document summarization using LangChain"""
    
    def __init__(self):
        self.llm = OpenAIWrapper()
    
    async def summarize_document(self, document_id: str) -> Dict[str, Any]:
        """Summarize a document using its chunks"""
        try:
            # Get all chunks for document
            response = supabase_client.supabase.table('mevzuat_embeddings').select('content, metadata').eq('document_id', document_id).order('chunk_index').execute()
            
            if not response.data:
                raise AppException("Document not found or has no content")
            
            chunks = response.data
            full_text = "\n\n".join([chunk['content'] for chunk in chunks])
            
            # Create summarization prompt
            prompt = f"""Aşağıdaki hukuki belgeyi özetleyin:

{full_text}

ÖZET KURALLARI:
1. Ana konuları ve önemli maddeleri belirtin
2. Kilit hükümları özetleyin
3. Uygulanabilir durumları açıklayın
4. 300-500 kelime arasında özetleyin
5. Türkçe ve anlaşılır dille yazın

ÖZET:"""
            
            summary = self.llm._call(prompt)
            
            return {
                "document_id": document_id,
                "summary": summary,
                "total_chunks": len(chunks),
                "total_length": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Document summarization failed: {e}")
            raise AppException("Failed to summarize document", str(e))