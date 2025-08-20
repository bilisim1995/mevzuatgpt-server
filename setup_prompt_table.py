#!/usr/bin/env python3
"""
AI Prompts tablosunu Supabase'de oluştur ve varsayılan promptları ekle
"""

import asyncio
import logging
from models.supabase_client import supabase_client

logger = logging.getLogger(__name__)

async def setup_ai_prompts_table():
    """AI prompts tablosunu kur ve varsayılan verileri ekle"""
    
    try:
        supabase = supabase_client.supabase
        
        # 1. Tabloyu oluştur (Supabase web interface'den yapılması gerekiyor)
        print("🏗️  ai_prompts tablosu oluşturuluyor...")
        print("📝 Bu tabloyu Supabase SQL Editor'da manuel oluşturmanız gerekiyor:")
        print("\n" + "="*50)
        print("""
CREATE TABLE IF NOT EXISTS ai_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_type VARCHAR(50) NOT NULL,
    prompt_content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    version VARCHAR(20),
    updated_by UUID,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index'ler
CREATE INDEX IF NOT EXISTS idx_ai_prompts_type_active ON ai_prompts(prompt_type, is_active);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_updated_at ON ai_prompts(updated_at DESC);
        """)
        print("="*50 + "\n")
        
        # 2. Varsayılan promptları ekle
        print("📝 Varsayılan promptlar ekleniyor...")
        
        # Groq legal prompt
        groq_prompt = {
            'prompt_type': 'groq_legal',
            'prompt_content': '''Sen hukuki belgeleri analiz eden uzman bir hukuk danışmanısın. 

TEMEL KURALLAR:
1. SADECE verilen belge içeriklerindeki bilgileri kullan
2. Kendi genel bilgini ASLA kullanma
3. Belge dışından örnek, yorum veya ek bilgi verme
4. Kapsamlı, detaylı ve analitik cevaplar ver
5. Yasal metinleri açıklayarak anlaşılır hale getir

CEVAP STİLİ:
- **Kapsamlı ve detaylı** yanıtlar ver (en az 3-4 paragraf)
- **Analitik yaklaşım** kullan - sadece aktarma değil, açıklama da yap
- **Hukuki terimleri açıkla** ve anlamlarını netleştir
- **Bağlam bilgisi** ver - düzenlemenin amacını ve kapsamını açıkla
- **Pratik uygulamalar** hakkında belgedeki bilgileri detaylandır
- **İlgili maddeler** arasında bağlantı kur ve bir bütün olarak ele al

CEVAP FORMATINI:
- Markdown formatında profesyonel sunum
- Ana başlıklar için ## kullan
- Alt başlıklar için ### kullan  
- Önemli noktalar için **kalın** yazı
- Madde numaraları ve referanslar için `kod` formatı
- Listeler için - veya 1. kullan
- Uzun cevaplar tercih et - kısa değil, kapsamlı ol

YASAKLAR:
- Aynı cümleleri tekrarlama
- Çok kısa, yüzeysel cevaplar verme
- Genel hukuki bilgi ekleme (sadece belge içeriği)

ÖNEMLİ: Belge boş veya alakasız ise: "Verilen belge içeriğinde bu konuda detaylı bilgi bulunmamaktadır. Lütfen daha spesifik soru sorun veya ilgili belge bölümünü kontrol edin." yaz.''',
            'is_active': True,
            'version': '20250820_0215',
            'description': 'Varsayılan Groq legal analiz promptu'
        }
        
        # OpenAI legal prompt
        openai_prompt = {
            'prompt_type': 'openai_legal',
            'prompt_content': 'Sen hukuki belgeleri analiz eden uzman bir hukuk danışmanısın. Sadece verilen belge içeriklerini kullanarak kapsamlı ve analitik cevaplar ver. Türkçe yanıt ver.',
            'is_active': True,
            'version': '20250820_0215',
            'description': 'Varsayılan OpenAI legal analiz promptu'
        }
        
        # Mevcut promptları kontrol et
        existing_groq = supabase.table('ai_prompts').select('id').eq('prompt_type', 'groq_legal').execute()
        existing_openai = supabase.table('ai_prompts').select('id').eq('prompt_type', 'openai_legal').execute()
        
        # Groq prompt ekle
        if not existing_groq.data:
            response = supabase.table('ai_prompts').insert(groq_prompt).execute()
            if response.data:
                print("✅ Groq legal prompt eklendi")
            else:
                print("❌ Groq prompt eklenirken hata oluştu")
        else:
            print("ℹ️  Groq legal prompt zaten mevcut")
        
        # OpenAI prompt ekle
        if not existing_openai.data:
            response = supabase.table('ai_prompts').insert(openai_prompt).execute()
            if response.data:
                print("✅ OpenAI legal prompt eklendi")
            else:
                print("❌ OpenAI prompt eklenirken hata oluştu")
        else:
            print("ℹ️  OpenAI legal prompt zaten mevcut")
        
        print("\n🎉 Prompt sistemi kurulumu tamamlandı!")
        print("📍 Artık dinamik prompt sistemi aktif")
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        logger.error(f"Setup error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(setup_ai_prompts_table())