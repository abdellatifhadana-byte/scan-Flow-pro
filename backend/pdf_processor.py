import fitz
from PIL import Image
import io
from pathlib import Path
import logging
import tempfile

logger = logging.getLogger(__name__)

class PDFProcessor:
    def get_page_count(self, pdf_path: str) -> int:
        """الحصول على عدد الصفحات"""
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
            return 0
    
    def get_page_image(self, pdf_path: str, page_num: int, zoom: float = 2.0) -> str:
        """تحويل صفحة إلى صورة"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            pix.save(temp_file.name)
            
            doc.close()
            return temp_file.name
        
        except Exception as e:
            logger.error(f"Error converting page to image: {str(e)}")
            return None
    
    def save_page_as_pdf(self, source_pdf: str, page_num: int, output_path: str):
        """حفظ صفحة واحدة كملف PDF"""
        try:
            doc = fitz.open(source_pdf)
            
            output_doc = fitz.open()
            output_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            output_doc.save(output_path)
            output_doc.close()
            doc.close()
        
        except Exception as e:
            logger.error(f"Error saving page as PDF: {str(e)}")
            raise
    
    def merge_pdfs(self, pdf_list: list, output_path: str):
        """دمج عدة ملفات PDF"""
        try:
            output_doc = fitz.open()
            
            for pdf_info in pdf_list:
                source_doc = fitz.open(pdf_info['source_path'])
                output_doc.insert_pdf(
                    source_doc,
                    from_page=pdf_info['page_num'],
                    to_page=pdf_info['page_num']
                )
                source_doc.close()
            
            output_doc.save(output_path)
            output_doc.close()
        
        except Exception as e:
            logger.error(f"Error merging PDFs: {str(e)}")
            raise