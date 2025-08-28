"""
Admin endpoints for Groq AI configuration and settings management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from api.dependencies import get_current_user_admin
from services.groq_service import GroqService
from utils.response import success_response, error_response
from utils.exceptions import AppException
from models.supabase_client import supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/groq", tags=["Admin-Groq"])

# Pydantic Models for Request/Response
class GroqSettingsResponse(BaseModel):
    """Current Groq configuration settings"""
    default_model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    available_models: List[str]
    creativity_mode: str
    response_style: str
    
    class Config:
        # Ensure all fields are included in response
        fields = {
            "default_model": {"description": "Currently selected default model"}
        }

class GroqSettingsUpdate(BaseModel):
    """Request model for updating Groq settings"""
    default_model: Optional[str] = Field(None, description="Default model to use")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Creativity level (0.0-2.0)")
    max_tokens: Optional[int] = Field(None, ge=100, le=4096, description="Maximum response length")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(None, ge=0.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=0.0, le=2.0, description="Presence penalty")
    creativity_mode: Optional[str] = Field(None, description="Yaratıcılık modu: conservative, balanced, creative, highly_creative")
    response_style: Optional[str] = Field(None, description="Cevap stili: concise, detailed, analytical, conversational")

class CreativityPreset(BaseModel):
    """Predefined creativity presets for easy configuration"""
    name: str
    description: str
    temperature: float
    top_p: float
    frequency_penalty: float
    presence_penalty: float

class ModelInfoResponse(BaseModel):
    """Model information and performance metrics"""
    model_name: str
    description: str
    context_length: int
    performance_tier: str
    best_use_cases: List[str]

# Global settings storage (in production, this would be in database)
current_groq_settings = {
    "default_model": "llama3-70b-8192",
    "temperature": 0.3,
    "max_tokens": 2048,
    "top_p": 0.9,
    "frequency_penalty": 0.5,
    "presence_penalty": 0.6,
    "creativity_mode": "balanced",
    "response_style": "detailed"
}

# Creativity presets
creativity_presets = {
    "conservative": CreativityPreset(
        name="Muhafazakar",
        description="Kesin ve faktüel cevaplar, minimum yaratıcılık",
        temperature=0.1,
        top_p=0.7,
        frequency_penalty=0.3,
        presence_penalty=0.3
    ),
    "balanced": CreativityPreset(
        name="Dengeli",
        description="Faktüel doğruluk ile yaratıcılık arasında denge",
        temperature=0.3,
        top_p=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.6
    ),
    "creative": CreativityPreset(
        name="Yaratıcı",
        description="Daha esnek ve yaratıcı cevaplar",
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0.7,
        presence_penalty=0.8
    ),
    "highly_creative": CreativityPreset(
        name="Çok Yaratıcı",
        description="Maksimum yaratıcılık ve çeşitlilik",
        temperature=1.2,
        top_p=0.98,
        frequency_penalty=1.0,
        presence_penalty=1.0
    )
}

@router.get("/settings")
async def get_groq_settings(
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Mevcut Groq ayarlarını getir (sadece admin)
    
    Returns:
        Mevcut Groq konfigürasyon ayarları
    """
    try:
        groq_service = GroqService()
        available_models = groq_service.get_available_models()
        
        settings_response = GroqSettingsResponse(
            default_model=current_groq_settings["default_model"],
            temperature=current_groq_settings["temperature"],
            max_tokens=current_groq_settings["max_tokens"],
            top_p=current_groq_settings["top_p"],
            frequency_penalty=current_groq_settings["frequency_penalty"],
            presence_penalty=current_groq_settings["presence_penalty"],
            available_models=available_models,
            creativity_mode=current_groq_settings["creativity_mode"],
            response_style=current_groq_settings["response_style"]
        )
        
        # Debug logging
        logger.info(f"Admin {current_user['email']} retrieved Groq settings. Default model: {current_groq_settings['default_model']}")
        logger.info(f"Available models: {available_models}")
        logger.info(f"All settings: {current_groq_settings}")
        
        return {
            "current_settings": settings_response.dict()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving Groq settings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Groq ayarları getirilemedi"
        )

@router.put("/settings", response_model=Dict[str, Any])
async def update_groq_settings(
    request: GroqSettingsUpdate,
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Groq ayarlarını güncelle (sadece admin)
    
    Args:
        request: Güncellenecek Groq ayarları
        current_user: Mevcut admin kullanıcı
        
    Returns:
        Güncellenmiş ayarlar ve işlem sonucu
    """
    try:
        groq_service = GroqService()
        available_models = groq_service.get_available_models()
        
        # Validate model if provided
        if request.default_model and request.default_model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz model: {request.default_model}. Kullanılabilir modeller: {', '.join(available_models)}"
            )
        
        # Validate creativity mode if provided
        if request.creativity_mode and request.creativity_mode not in creativity_presets:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz yaratıcılık modu: {request.creativity_mode}. Kullanılabilir modlar: {', '.join(creativity_presets.keys())}"
            )
        
        # Validate response style if provided
        valid_styles = ["concise", "detailed", "analytical", "conversational"]
        if request.response_style and request.response_style not in valid_styles:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz cevap stili: {request.response_style}. Kullanılabilir stiller: {', '.join(valid_styles)}"
            )
        
        # Update settings
        previous_settings = current_groq_settings.copy()
        updated_fields = []
        
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                current_groq_settings[field] = value
                updated_fields.append(field)
        
        # Apply creativity preset if mode was changed
        if request.creativity_mode and request.creativity_mode in creativity_presets:
            preset = creativity_presets[request.creativity_mode]
            current_groq_settings.update({
                "temperature": preset.temperature,
                "top_p": preset.top_p,
                "frequency_penalty": preset.frequency_penalty,
                "presence_penalty": preset.presence_penalty
            })
            updated_fields.extend(["temperature", "top_p", "frequency_penalty", "presence_penalty"])
        
        # Log the change
        change_log = {
            "admin_user": current_user['email'],
            "timestamp": datetime.utcnow().isoformat(),
            "updated_fields": updated_fields,
            "previous_settings": previous_settings,
            "new_settings": current_groq_settings.copy()
        }
        
        logger.info(f"Admin {current_user['email']} updated Groq settings: {updated_fields}")
        
        return {
            "success": True,
            "message": f"Groq ayarları başarıyla güncellendi. Güncellenen alanlar: {', '.join(updated_fields)}",
            "data": {
                "updated_fields": updated_fields,
                "current_settings": current_groq_settings,
                "change_log": change_log
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Groq settings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Groq ayarları güncellenirken hata oluştu"
        )

@router.get("/creativity-presets", response_model=Dict[str, CreativityPreset])
async def get_creativity_presets(
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Yaratıcılık ön ayarlarını getir (sadece admin)
    
    Returns:
        Kullanılabilir yaratıcılık ön ayarları
    """
    try:
        logger.info(f"Admin {current_user['email']} retrieved creativity presets")
        return creativity_presets
        
    except Exception as e:
        logger.error(f"Error retrieving creativity presets: {e}")
        raise HTTPException(
            status_code=500,
            detail="Yaratıcılık ön ayarları getirilemedi"
        )

@router.post("/apply-preset/{preset_name}", response_model=Dict[str, Any])
async def apply_creativity_preset(
    preset_name: str,
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Yaratıcılık ön ayarını uygula (sadece admin)
    
    Args:
        preset_name: Uygulanacak ön ayar adı
        current_user: Mevcut admin kullanıcı
        
    Returns:
        Uygulanan ön ayar detayları
    """
    try:
        if preset_name not in creativity_presets:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz ön ayar: {preset_name}. Kullanılabilir ön ayarlar: {', '.join(creativity_presets.keys())}"
            )
        
        preset = creativity_presets[preset_name]
        previous_settings = current_groq_settings.copy()
        
        # Apply preset settings
        current_groq_settings.update({
            "creativity_mode": preset_name,
            "temperature": preset.temperature,
            "top_p": preset.top_p,
            "frequency_penalty": preset.frequency_penalty,
            "presence_penalty": preset.presence_penalty
        })
        
        logger.info(f"Admin {current_user['email']} applied creativity preset: {preset_name}")
        
        return {
            "success": True,
            "message": f"'{preset.name}' yaratıcılık ön ayarı başarıyla uygulandı",
            "data": {
                "preset_name": preset_name,
                "preset_info": preset.dict(),
                "previous_settings": previous_settings,
                "current_settings": current_groq_settings
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying creativity preset {preset_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Yaratıcılık ön ayarı uygulanırken hata oluştu"
        )

@router.get("/models", response_model=Dict[str, Any])
async def get_available_models(
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Kullanılabilir Groq modellerini getir (sadece admin)
    
    Returns:
        Model listesi ve detayları
    """
    try:
        groq_service = GroqService()
        available_models = groq_service.get_available_models()
        
        # Enhanced model information
        model_info = {
            "llama3-8b-8192": ModelInfoResponse(
                model_name="LLaMA 3 8B",
                description="Hızlı ve verimli, günlük kullanım için ideal",
                context_length=8192,
                performance_tier="Fast",
                best_use_cases=["Kısa sorular", "Hızlı cevaplar", "Basit analiz"]
            ),
            "llama3-70b-8192": ModelInfoResponse(
                model_name="LLaMA 3 70B",
                description="Daha güçlü ve kapsamlı, detaylı analizler için",
                context_length=8192,
                performance_tier="High Performance",
                best_use_cases=["Karmaşık hukuki analizler", "Detaylı araştırma", "Uzun belgeler"]
            ),
            "mixtral-8x7b-32768": ModelInfoResponse(
                model_name="Mixtral 8x7B",
                description="Uzun bağlam desteği, büyük belgeler için",
                context_length=32768,
                performance_tier="Long Context",
                best_use_cases=["Uzun belgeler", "Kapsamlı analiz", "Çoklu kaynak karşılaştırma"]
            ),
            "gemma-7b-it": ModelInfoResponse(
                model_name="Gemma 7B IT",
                description="Google'ın modeli, özel görevler için optimize",
                context_length=8192,
                performance_tier="Specialized",
                best_use_cases=["Teknik belgeler", "Özel formatlar", "Yapılandırılmış veri"]
            )
        }
        
        # Filter available models
        available_model_info = {
            model: info for model, info in model_info.items() 
            if model in available_models
        }
        
        logger.info(f"Admin {current_user['email']} retrieved available models")
        logger.info(f"Current default model in models endpoint: {current_groq_settings['default_model']}")
        logger.info(f"Available models count: {len(available_model_info)}")
        
        return {
            "models": list(available_model_info.values()),
            "total_count": len(available_model_info),
            "current_default": current_groq_settings["default_model"]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving available models: {e}")
        raise HTTPException(
            status_code=500,
            detail="Model listesi getirilemedi"
        )

@router.post("/test-settings", response_model=Dict[str, Any])
async def test_groq_settings(
    test_query: str = Query(..., description="Test sorusu"),
    use_current_settings: bool = Query(True, description="Mevcut ayarları kullan"),
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Groq ayarlarını test et (sadece admin)
    
    Args:
        test_query: Test edilecek soru
        use_current_settings: Mevcut ayarları kullanıp kullanmama
        current_user: Mevcut admin kullanıcı
        
    Returns:
        Test sonuçları ve performans metrikleri
    """
    try:
        groq_service = GroqService()
        
        # Test with current settings
        test_context = "Bu bir admin test mesajıdır. Groq yapılandırma ayarları test ediliyor."
        
        if use_current_settings:
            response = await groq_service.generate_response(
                query=test_query,
                context=test_context,
                model=current_groq_settings["default_model"],
                max_tokens=current_groq_settings["max_tokens"],
                temperature=current_groq_settings["temperature"]
            )
        else:
            # Use default settings for comparison
            response = await groq_service.generate_response(
                query=test_query,
                context=test_context
            )
        
        logger.info(f"Admin {current_user['email']} tested Groq settings")
        
        return {
            "success": True,
            "message": "Groq ayarları test edildi",
            "data": {
                "test_query": test_query,
                "settings_used": current_groq_settings if use_current_settings else "default",
                "response_preview": response.get("response", "")[:200] + "..." if len(response.get("response", "")) > 200 else response.get("response", ""),
                "response_length": len(response.get("response", "")),
                "model_used": response.get("model_used"),
                "token_usage": response.get("token_usage", {}),
                "response_time": response.get("response_time", 0),
                "confidence_score": response.get("confidence_score", 0.0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing Groq settings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Groq ayarları test edilirken hata oluştu"
        )

@router.get("/status", response_model=Dict[str, Any])
async def get_groq_status(
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Groq servisinin durumunu kontrol et (sadece admin)
    
    Returns:
        Groq servis durumu ve sağlık bilgileri
    """
    try:
        groq_service = GroqService()
        
        # Test service health
        start_time = datetime.utcnow()
        health_response = await groq_service.generate_response(
            query="Test",
            context="Health check",
            max_tokens=10
        )
        end_time = datetime.utcnow()
        
        response_time = (end_time - start_time).total_seconds() * 1000  # ms
        
        status_info = {
            "service_status": "healthy" if health_response else "unhealthy",
            "response_time_ms": round(response_time, 2),
            "available_models": groq_service.get_available_models(),
            "current_settings": current_groq_settings,
            "last_check": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Admin {current_user['email']} checked Groq status")
        
        return {
            "success": True,
            "data": status_info
        }
        
    except Exception as e:
        logger.error(f"Error checking Groq status: {e}")
        return {
            "success": False,
            "data": {
                "service_status": "error",
                "error_message": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        }

@router.post("/reset-settings", response_model=Dict[str, Any])
async def reset_groq_settings(
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Groq ayarlarını varsayılana sıfırla (sadece admin)
    
    Args:
        current_user: Mevcut admin kullanıcı
        
    Returns:
        Sıfırlama işlem sonucu
    """
    try:
        global current_groq_settings
        previous_settings = current_groq_settings.copy()
        
        # Reset to default settings
        current_groq_settings = {
            "default_model": "llama3-70b-8192",
            "temperature": 0.3,
            "max_tokens": 2048,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.6,
            "creativity_mode": "balanced",
            "response_style": "detailed"
        }
        
        logger.info(f"Admin {current_user['email']} reset Groq settings to default")
        
        return {
            "success": True,
            "message": "Groq ayarları varsayılan değerlere sıfırlandı",
            "data": {
                "previous_settings": previous_settings,
                "current_settings": current_groq_settings,
                "reset_timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error resetting Groq settings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Groq ayarları sıfırlanırken hata oluştu"
        )