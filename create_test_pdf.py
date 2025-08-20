from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

def create_test_pdf():
    # Create test PDF
    doc = SimpleDocTemplate("test_mevzuat.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Add content
    title = Paragraph("TÜRK TİCARET KANUNU - TEST BELGESİ", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    content = """
    Bu belge MevzuatGPT sistemi için hazırlanmış test belgesidir.
    
    MADDE 1 - Bu kanunun amacı ticari faaliyetleri düzenlemek ve 
    iş hayatında güvenliği sağlamaktır.
    
    MADDE 2 - Ticaret unvanı kullanımı zorunludur. Şirket türleri:
    - Limited Şirket (Ltd. Şti.)
    - Anonim Şirket (A.Ş.)
    - Kollektif Şirket
    
    MADDE 3 - Çalışma koşulları:
    • Haftalık çalışma süresi 45 saati geçemez
    • Fazla mesai ödemesi yapılmalıdır  
    • İş sağlığı ve güvenliği önlemleri alınır
    
    Bu test belgesi semantic search ve embedding generation 
    testleri için kullanılacaktır.
    """
    
    para = Paragraph(content, styles['Normal'])
    story.append(para)
    
    doc.build(story)
    print("✅ test_mevzuat.pdf oluşturuldu")

if __name__ == "__main__":
    create_test_pdf()
