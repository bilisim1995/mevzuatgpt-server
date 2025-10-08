"""
Mevzuat Karşılaştırma Servisi
İki mevzuat metnini AI ile karşılaştırır ve farklılıkları analiz eder
"""

import logging
import time
from typing import Dict, Any
from openai import AsyncOpenAI
from groq import AsyncGroq

from core.config import settings

logger = logging.getLogger(__name__)


class DocumentCompareService:
    """Mevzuat karşılaştırma AI servisi"""
    
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        
    async def compare_documents(
        self,
        old_content: str,
        new_content: str,
        analysis_level: str = "normal",
        old_title: str | None = None,
        new_title: str | None = None
    ) -> Dict[str, Any]:
        """
        İki belgeyi karşılaştır ve farklılıkları analiz et
        
        Args:
            old_content: Eski mevzuat metni
            new_content: Yeni mevzuat metni
            analysis_level: Analiz seviyesi (yuzeysel, normal, detayli)
            old_title: Eski belge başlığı
            new_title: Yeni belge başlığı
            
        Returns:
            Dict[str, Any]: Karşılaştırma sonuçları (Markdown formatında)
        """
        try:
            start_time = time.time()
            
            # Prompt oluştur
            system_prompt = self._get_system_prompt(analysis_level)
            user_prompt = self._build_user_prompt(
                old_content, new_content, old_title, new_title, analysis_level
            )
            
            # Groq ile dene (hızlı)
            if self.groq_client:
                try:
                    response = await self._generate_with_groq(system_prompt, user_prompt)
                    generation_time = int((time.time() - start_time) * 1000)
                    
                    return {
                        "comparison_markdown": response,
                        "generation_time_ms": generation_time,
                        "provider": "groq"
                    }
                except Exception as groq_error:
                    logger.warning(f"Groq failed, falling back to OpenAI: {str(groq_error)}")
            
            # OpenAI fallback
            if self.openai_client:
                response = await self._generate_with_openai(system_prompt, user_prompt)
                generation_time = int((time.time() - start_time) * 1000)
                
                return {
                    "comparison_markdown": response,
                    "generation_time_ms": generation_time,
                    "provider": "openai"
                }
            
            raise Exception("No AI provider available")
            
        except Exception as e:
            logger.error(f"Document comparison failed: {str(e)}")
            raise
    
    def _get_system_prompt(self, analysis_level: str) -> str:
        """Analiz seviyesine göre system prompt oluştur"""
        
        base_prompt = """Sen Türkiye mevzuatı konusunda uzman bir hukuk asistanısın. 
İki mevzuat metnini karşılaştırıp aralarındaki farkları analiz ediyorsun.

Görevin:
1. İki metin arasındaki önemli farkları tespit et
2. Eklenen, çıkarılan ve değiştirilen kısımları belirt
3. Değişikliklerin hukuki etkilerini açıkla
4. Markdown formatında düzenli ve okunabilir bir rapor hazırla

Format Kuralları:
- Başlıklar için ## ve ### kullan
- Her maddeyi ayrı satırda göster
- Eklenenler için: ✅ **MADDE X** - Açıklama
- Çıkarılanlar için: ❌ **MADDE X** - Açıklama  
- Değişenler için: 🔄 **MADDE X** - Eski → Yeni karşılaştırması
- Önemli kısımlar için **bold** kullan
- Her değişiklik maddesi numaralı veya adlandırılmış olmalı
- Değişiklik detayları için alt maddeler (  - ) kullan"""

        if analysis_level == "yuzeysel":
            return base_prompt + """

Yüzeysel Analiz İçin:
- Sadece ana değişiklikleri listele
- Kısa ve öz açıklamalar yap
- 5-10 madde ile sınırlı tut
- Detaylara girme"""

        elif analysis_level == "normal":
            return base_prompt + """

Normal Analiz İçin:
- Tüm önemli değişiklikleri listele
- Her değişiklik için kısa açıklama ekle
- Mantıksal gruplamalar yap (eklenenler, çıkarılanlar, değişenler)
- Orta düzey detay seviyesi kullan"""

        elif analysis_level == "detayli":
            return base_prompt + """

Detaylı Analiz İçin:
- Her değişikliği ayrıntılı incele
- Hukuki etkileri derinlemesine açıkla
- Madde madde karşılaştırma yap
- Önceki ve sonraki versiyonları tablo halinde göster
- Uygulama örnekleri ekle
- Muhtemel sonuçları açıkla"""

        return base_prompt

    def _build_user_prompt(
        self,
        old_content: str,
        new_content: str,
        old_title: str,
        new_title: str,
        analysis_level: str
    ) -> str:
        """Kullanıcı prompt'u oluştur"""
        
        prompt = f"""Aşağıdaki iki mevzuat metnini karşılaştır ve farklılıkları analiz et:

## ESKİ MEVZUAT:
Başlık: {old_title or 'Belirtilmemiş'}

{old_content}

---

## YENİ MEVZUAT:
Başlık: {new_title or 'Belirtilmemiş'}

{new_content}

---

Analiz Seviyesi: **{analysis_level.upper()}**

Lütfen yukarıdaki iki metin arasındaki farkları markdown formatında raporla.

## Rapor Yapısı:

### 📊 ÖZET
Tek bir cümlede belge karşılaştırmasının sonucunu özetle.

### 📝 DETAYLI FARKLAR

Her değişiklik için şu formata uy:

**[Değişiklik Numarası]. [DEĞİŞİKLİK TÜRÜ]** (✅ Eklenen / ❌ Çıkarılan / 🔄 Değiştirilen)

> **Eski Metin:**
> "[Eski metinden alıntı]"

> **Yeni Metin:**
> "[Yeni metinden alıntı]"

**Ne Değişti:** [Kısa açıklama - ne eklendi, ne çıkarıldı veya ne değiştirildi]

---

**ÖNEMLİ KURALLAR**: 
- Özet kısa ve öz olsun (cümle tekrarı yapma)
- Her değişikliği numaralandır (1, 2, 3...)
- Eski ve yeni metinlerden doğrudan alıntı yap
- Emoji kullan: ✅ (eklenen), ❌ (çıkarılan), 🔄 (değiştirilen)
- Değişiklikler arasında `---` ayırıcı kullan
- Alıntılar blockquote (>) ile göster"""
        
        return prompt

    async def _generate_with_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Groq API ile yanıt oluştur"""
        
        response = await self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000,
            top_p=0.9
        )
        
        return response.choices[0].message.content

    async def _generate_with_openai(self, system_prompt: str, user_prompt: str) -> str:
        """OpenAI API ile yanıt oluştur"""
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000,
            top_p=0.9
        )
        
        return response.choices[0].message.content
    
    def count_changes(self, markdown_text: str) -> int:
        """Markdown metninde değişiklik sayısını hesapla"""
        
        change_markers = ['✅', '❌', '🔄']
        count = 0
        
        for marker in change_markers:
            count += markdown_text.count(marker)
        
        return count
    
    def generate_summary(self, markdown_text: str, analysis_level: str) -> str:
        """Markdown metninden özet çıkar"""
        
        lines = markdown_text.split('\n')
        
        # İlk özet bölümünü bul
        for i, line in enumerate(lines):
            if '## Özet' in line or '## ÖZET' in line:
                summary_lines = []
                for j in range(i+1, min(i+6, len(lines))):
                    if lines[j].strip() and not lines[j].startswith('#'):
                        summary_lines.append(lines[j].strip())
                
                if summary_lines:
                    return ' '.join(summary_lines)
        
        # Özet bulunamazsa, ilk paragrafı kullan
        for line in lines:
            if line.strip() and not line.startswith('#'):
                return line.strip()[:200] + "..."
        
        return f"{analysis_level.capitalize()} seviyede karşılaştırma yapıldı."
