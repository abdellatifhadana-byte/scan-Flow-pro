from pathlib import Path
import logging
from pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

class SmartMerge:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
    
    def merge_by_code(self, codes_data: dict) -> list:
        """دمج الصفحات حسب الكود"""
        results = []
        
        for code, pages in codes_data.items():
            try:
                # استخدام nom من أول صفحة (كل الصفحات لنفس الكود يجب أن تأتي من نفس الملف)
                nom = pages[0].get('nom', '') if pages else ''
                
                output_dir = Path("results") / "codes" / code
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_filename = f"P{code}-{nom}.pdf"
                output_path = output_dir / output_filename
                
                pages_sorted = sorted(pages, key=lambda x: (x['source_path'], x['page_num']))
                
                self.pdf_processor.merge_pdfs(pages_sorted, str(output_path))
                
                results.append({
                    'code': code,
                    'page_count': len(pages_sorted),
                    'filename': output_filename,
                    'file_path': str(output_path)
                })
                
                logger.info(f"Merged {len(pages_sorted)} pages for code {code}")
            
            except Exception as e:
                logger.error(f"Error merging code {code}: {str(e)}")
        
        return results