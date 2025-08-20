"""
Admin Prompt Management Routes
Dinamik prompt yönetimi için admin endpoint'leri
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status

from api.dependencies import require_admin
from services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/prompts/{prompt_type}",
    summary="Get System Prompt",
    description="Aktif sistem promptunu getir"
)
async def get_system_prompt(
    prompt_type: str,
    current_user = Depends(require_admin)
):
    """Get active system prompt"""
    try:
        prompt_content = await prompt_service.get_system_prompt(prompt_type)
        
        return {
            "success": True,
            "prompt_type": prompt_type,
            "prompt_content": prompt_content
        }
        
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt getirilemedi"
        )

@router.put(
    "/prompts/{prompt_type}",
    summary="Update System Prompt",
    description="Sistem promptunu güncelle"
)
async def update_system_prompt(
    prompt_type: str,
    prompt_content: str,
    current_user = Depends(require_admin)
):
    """Update system prompt"""
    try:
        if not prompt_content or not prompt_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt içeriği boş olamaz"
            )
        
        result = await prompt_service.update_system_prompt(
            prompt_type=prompt_type,
            prompt_content=prompt_content.strip(),
            user_id=str(current_user.get("user_id"))
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "prompt_id": result.get("prompt_id")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt güncellenirken hata oluştu"
        )

@router.get(
    "/prompts/{prompt_type}/history",
    summary="Get Prompt History",
    description="Prompt değişiklik geçmişini getir"
)
async def get_prompt_history(
    prompt_type: str,
    limit: Optional[int] = 10,
    current_user = Depends(require_admin)
):
    """Get prompt change history"""
    try:
        result = await prompt_service.get_prompt_history(prompt_type, limit)
        
        if result["success"]:
            return {
                "success": True,
                "prompt_type": prompt_type,
                "history": result["history"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Geçmiş getirilemedi")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt history {prompt_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt geçmişi getirilemedi"
        )

@router.post(
    "/prompts/reload-cache",
    summary="Reload Prompt Cache",
    description="Prompt cache'ini temizle ve yeniden yükle"
)
async def reload_prompt_cache(
    current_user = Depends(require_admin)
):
    """Reload prompt cache"""
    try:
        # Cache'i temizle
        prompt_service._clear_cache()
        
        # Ana prompt'ları tekrar yükle
        await prompt_service.get_system_prompt("groq_legal")
        await prompt_service.get_system_prompt("openai_legal")
        
        return {
            "success": True,
            "message": "Prompt cache başarıyla yenilendi"
        }
        
    except Exception as e:
        logger.error(f"Error reloading prompt cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache yenilenirken hata oluştu"
        )