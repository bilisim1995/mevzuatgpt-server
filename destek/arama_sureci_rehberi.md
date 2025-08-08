# MevzuatGPT Arama Süreci Rehberi

## Genel Bakış

MevzuatGPT'de kullanıcılar iki farklı arama yöntemi ile hukuki belgelerde bilgi arayabilir:
1. **Semantik Arama** - Doğrudan belge parçalarını bulma
2. **AI Sorgu (Ask)** - Yapay zeka destekli cevap üretimi

## 1. Semantik Arama Süreci

### Endpoint
```
POST /api/user/search
```

### Çalışma Akışı
1. **İstek Alımı**: Kullanıcı arama sorgusunu gönderir
2. **Embedding Üretimi**: OpenAI ile sorgu vektöre dönüştürülür
3. **Vector Search**: Supabase PostgreSQL'de pgvector ile benzerlik araması
4. **Sonuç Filtreleme**: Kategori ve tarih filtreleri uygulanır
5. **Dönüş**: İlgili belge parçaları similarity score ile birlikte döner

### Örnek İstek
```json
{
  "query": "vergi kanunu madde 10",
  "limit": 10,
  "similarity_threshold": 0.7,
  "category": "vergi",
  "date_range": {
    "start": "2020-01-01",
    "end": "2024-12-31"
  }
}
```

### Örnek Cevap
```json
{
  "query": "vergi kanunu madde 10",
  "results": [
    {
      "document_id": "uuid",
      "title": "Gelir Vergisi Kanunu",
      "chunk_text": "Madde 10 - Gelir vergisi...",
      "similarity_score": 0.92,
      "metadata": {
        "page": 5,
        "institution": "Maliye Bakanlığı"
      }
    }
  ],
  "total_results": 1
}
```

## 2. AI Sorgu (Ask) Süreci

### Endpoint
```
POST /api/user/ask
```

### Detaylı Çalışma Akışı

#### Adım 1: İstek Validasyonu
- Rate limiting kontrolü (30 istek/dakika per user)
- İstek parametrelerinin doğrulanması
- Kullanıcı yetkilendirmesi

#### Adım 2: Cache Kontrolü
- **Embedding Cache**: Aynı sorgu için embedding var mı? (1 saat TTL)
- **Search Cache**: Arama sonuçları cache'de var mı? (30 dakika TTL)
- **User History**: Kullanıcının son aramalarına ekleme

#### Adım 3: Embedding Üretimi
```python
# OpenAI API çağrısı
embedding = await openai.embeddings.create(
    model="text-embedding-3-large",
    input=query,
    dimensions=1536
)
```

#### Adım 4: Vector Search
```sql
-- Supabase'de pgvector sorgusu
SELECT *, 1 - (embedding <=> query_embedding) as similarity
FROM mevzuat_embeddings 
WHERE 1 - (embedding <=> query_embedding) > similarity_threshold
ORDER BY similarity DESC
LIMIT limit_value;
```

#### Adım 5: Context Hazırlama
- En alakalı belge parçaları seçilir
- Institution filter uygulanır
- Context metni oluşturulur

#### Adım 6: AI Cevap Üretimi
```python
# Ollama (Llama3) API çağrısı
response = await ollama_client.post("/api/generate", {
    "model": "llama3",
    "prompt": f"Context: {context}\n\nSoru: {query}\n\nCevap:",
    "stream": false
})
```

#### Adım 7: Confidence Scoring
```python
def calculate_confidence(sources, response_length, similarity_scores):
    avg_similarity = sum(similarity_scores) / len(similarity_scores)
    source_diversity = len(set(s['document_id'] for s in sources))
    length_factor = min(response_length / 500, 1.0)
    
    confidence = (avg_similarity * 0.5 + 
                 source_diversity/10 * 0.3 + 
                 length_factor * 0.2)
    return min(confidence, 1.0)
```

#### Adım 8: Caching ve Sonuç Dönüşü
- Sonuç Redis'e cache'lenir
- Performance metrics kaydedilir
- User history güncellenir

### Örnek İstek
```json
{
  "query": "Vergi borcu yapılandırması nasıl yapılır?",
  "institution_filter": "Maliye Bakanlığı",
  "limit": 10,
  "similarity_threshold": 0.7,
  "use_cache": true
}
```

### Örnek Cevap
```json
{
  "answer": "Vergi borcu yapılandırması için öncelikle...",
  "sources": [
    {
      "document_id": "uuid",
      "title": "Vergi Borçlarının Yapılandırılması Hakkında Kanun",
      "chunk_text": "İlgili maddeler...",
      "similarity_score": 0.89,
      "page": 3
    }
  ],
  "confidence_score": 0.85,
  "processing_time": 2.3,
  "cached": false,
  "metadata": {
    "total_sources": 1,
    "embedding_cached": true,
    "institution_filtered": true
  }
}
```

## 3. Redis Caching Stratejisi

### Cache Türleri
1. **Embedding Cache** (1 saat TTL)
   - Key: `embedding:{hash(query)}`
   - Value: OpenAI embedding vector

2. **Search Results Cache** (30 dakika TTL)
   - Key: `search:{hash(query+filters)}`
   - Value: Arama sonuçları

3. **User History Cache** (24 saat TTL)
   - Key: `user_history:{user_id}`
   - Value: Son 20 arama

4. **Rate Limiting Cache** (1 dakika TTL)
   - Key: `rate_limit:{user_id}`
   - Value: İstek sayısı

### Cache Kontrol Akışı
```python
async def get_cached_or_compute(cache_key, compute_func, ttl):
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    result = await compute_func()
    await redis.setex(cache_key, ttl, json.dumps(result))
    return result
```

## 4. Performance Optimizasyonları

### Embedding Optimizasyonu
- Aynı sorular için embedding yeniden üretilmez
- Batch embedding işlemi için queue sistemi
- OpenAI API quota yönetimi

### Database Optimizasyonu
- pgvector index'leri
- Connection pooling
- Query optimization

### Redis Optimizasyonu
- TTL stratejisi
- Memory usage monitoring
- Cluster yapısı

## 5. Hata Yönetimi

### Rate Limiting
```json
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded",
    "detail": "Maximum 30 requests per minute",
    "retry_after": 60
  }
}
```

### Cache Miss Durumu
- Embedding üretimi başarısız → Fallback search
- Ollama erişilemez → OpenAI ChatGPT fallback
- Redis erişilemez → Direct processing

### Confidence Threshold
- %70'in altında confidence → Uyarı mesajı
- Kaynak bulunamaz → "Yeterli bilgi yok" cevabı
- Sistem hatası → Generic error response

## 6. Monitoring ve Metrics

### Performance Metrics
- Average response time
- Cache hit rate
- Confidence score distribution
- User satisfaction tracking

### System Health
- Redis connection status
- Ollama service availability
- OpenAI API quota usage
- Database performance

## 7. User Experience Features

### Personalized Suggestions
```
GET /api/user/suggestions
```
- Recent searches
- Popular searches
- Available institutions
- Recommended queries

### Search History
- Last 20 user searches
- Search performance analytics
- Favorite queries

## 8. Gelecek Geliştirmeler

### Planlanan Özellikler
- Multi-modal search (image + text)
- Advanced filtering options
- Export functionality
- Collaboration features

### Teknik İyileştirmeler
- Elasticsearch integration
- Advanced caching strategies
- Machine learning optimizations
- Real-time updates

---

**Not**: Bu döküman sistem architecture'ına dayalı olarak hazırlanmıştır. Teknik detaylar ve implementasyon özellikleri güncel kod tabanını yansıtmaktadır.