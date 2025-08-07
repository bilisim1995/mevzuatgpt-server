#!/usr/bin/env python3
"""
PDF Parsing Test
PDF dosyası indirme ve text extraction işlemlerini test eder
"""

import os
import sys
import aiohttp
import asyncio
import PyPDF2
import pdfplumber
import io
from datetime import datetime
from dotenv import load_dotenv
from services.storage_service import StorageService

# Load environment variables
load_dotenv()

class PDFParsingTester:
    def __init__(self):
        self.storage_service = StorageService()
    
    async def test_pdf_download_and_parsing(self, file_url: str):
        """PDF indirme ve parsing testi"""
        try:
            print(f"🔍 PDF test ediliyor: {file_url}")
            print(f"🕐 Test zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Test 1: Download PDF
            print("📥 1. PDF indiriliyor...")
            try:
                pdf_content = await self.storage_service.download_file(file_url)
                print(f"✅ İndirme başarılı - Dosya boyutu: {len(pdf_content)} bytes")
                
                # Check if content looks like PDF
                if pdf_content.startswith(b'%PDF'):
                    print("✅ İçerik geçerli PDF formatında")
                else:
                    print("❌ İçerik PDF formatında görünmüyor")
                    print(f"İlk 50 byte: {pdf_content[:50]}")
                    return False
            except Exception as e:
                print(f"❌ İndirme hatası: {str(e)}")
                return False
            
            print()
            
            # Test 2: Parse PDF with pdfplumber (more robust)
            print("📖 2. PDF parsing (pdfplumber)...")
            try:
                pdf_file = io.BytesIO(pdf_content)
                extracted_text = ""
                
                with pdfplumber.open(pdf_file) as pdf:
                    page_count = len(pdf.pages)
                    print(f"✅ PDF açıldı - Sayfa sayısı: {page_count}")
                    
                    for page_num, page in enumerate(pdf.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n"
                                print(f"   📄 Sayfa {page_num + 1}: {len(page_text)} karakter")
                            else:
                                print(f"   📄 Sayfa {page_num + 1}: 0 karakter")
                        except Exception as page_error:
                            print(f"   ❌ Sayfa {page_num + 1} okuma hatası: {str(page_error)}")
                
                total_chars = len(extracted_text.strip())
                print(f"✅ Text extraction tamamlandı - Toplam: {total_chars} karakter")
                
                if total_chars > 0:
                    # Show sample text
                    sample_text = extracted_text.strip()[:200]
                    print(f"📝 Örnek metin: {sample_text}...")
                    return True
                else:
                    print("❌ Hiç metin çıkarılamadı")
                    
                    # Try PyPDF2 as fallback
                    print("🔄 PyPDF2 ile tekrar deneniyor...")
                    pdf_file.seek(0)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    fallback_text = ""
                    for page_num in range(len(pdf_reader.pages)):
                        try:
                            page = pdf_reader.pages[page_num]
                            page_text = page.extract_text()
                            fallback_text += page_text + "\n"
                        except Exception as page_error:
                            continue
                    
                    fallback_chars = len(fallback_text.strip())
                    if fallback_chars > 0:
                        print(f"✅ PyPDF2 ile {fallback_chars} karakter çıkarıldı")
                        return True
                    else:
                        print("❌ PyPDF2 ile de metin çıkarılamadı")
                        return False
                    
            except Exception as e:
                print(f"❌ PDF parsing hatası: {str(e)}")
                return False
            
        except Exception as e:
            print(f"❌ Genel test hatası: {str(e)}")
            return False
    
    async def test_multiple_pdfs(self):
        """Birden fazla PDF'i test et"""
        print("=" * 60)
        print("🧪 PDF Parsing Test Başlıyor")
        print("=" * 60)
        
        # Test URLs from recent uploads
        test_urls = [
            "https://cdn.mevzuatgpt.org/documents/46dca142-8275-4ab6-a194-73e23f3f9d53.pdf",
            "https://cdn.mevzuatgpt.org/documents/cd953aa3-e827-471b-a22e-6a54366461eb.pdf",
            "https://cdn.mevzuatgpt.org/documents/da179331-6646-495a-9182-ceb4b7bd0250.pdf"
        ]
        
        successful_tests = 0
        total_tests = len(test_urls)
        
        for i, url in enumerate(test_urls):
            print(f"\n🔍 Test {i + 1}/{total_tests}")
            print("-" * 40)
            
            success = await self.test_pdf_download_and_parsing(url)
            if success:
                successful_tests += 1
                print("✅ Test başarılı!")
            else:
                print("❌ Test başarısız!")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Sonuçları: {successful_tests}/{total_tests} başarılı")
        
        if successful_tests == total_tests:
            print("🎉 TÜM PDF TESTLERI BAŞARILI!")
            print("✅ PDF indirme çalışıyor")
            print("✅ PDF parsing çalışıyor")
            print("✅ Text extraction çalışıyor")
        else:
            print("⚠️ BAZI PDF TESTLERI BAŞARISIZ!")
            print("❌ PDF processing pipeline'ında problem var")
        
        return successful_tests == total_tests

async def main():
    """Ana test fonksiyonu"""
    tester = PDFParsingTester()
    
    try:
        success = await tester.test_multiple_pdfs()
        
        if success:
            print("\n🎯 Sonuç: PDF parsing tamamen çalışıyor!")
            sys.exit(0)
        else:
            print("\n⚠️ Sonuç: PDF parsing'de problemler var.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Test kullanıcı tarafından iptal edildi.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Beklenmeyen hata: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())