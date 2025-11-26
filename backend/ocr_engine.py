import cv2
import numpy as np
from PIL import Image
import pytesseract
import easyocr
import re
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
import fitz

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self):
        self.tesseract_langs = 'ara+fra+eng'
        self.easyocr_reader_ar = easyocr.Reader(['ar', 'en'], gpu=False)
        self.easyocr_reader_fr = easyocr.Reader(['fr', 'en'], gpu=False)
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """معالجة الصورة لتحسين دقة OCR"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        denoised = cv2.fastNlMeansDenoising(gray)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_roi(self, image: np.ndarray, roi: Dict) -> np.ndarray:
        """استخراج منطقة ROI من الصورة"""
        h, w = image.shape[:2]
        x = int(roi['x'] * w)
        y = int(roi['y'] * h)
        width = int(roi['width'] * w)
        height = int(roi['height'] * h)
        
        x = max(0, x)
        y = max(0, y)
        width = min(width, w - x)
        height = min(height, h - y)
        
        return image[y:y+height, x:x+width]
    
    def rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """تدوير الصورة"""
        if angle == 0:
            return image
        
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    
    def ocr_tesseract(self, image: np.ndarray) -> str:
        """OCR باستخدام Tesseract"""
        try:
            text = pytesseract.image_to_string(
                image,
                lang=self.tesseract_langs,
                config='--psm 6'
            )
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract OCR error: {str(e)}")
            return ""
    
    def ocr_easyocr(self, image: np.ndarray) -> str:
        """OCR باستخدام EasyOCR"""
        try:
            results = self.easyocr_reader.readtext(image, detail=0)
            return ' '.join(results)
        except Exception as e:
            logger.error(f"EasyOCR error: {str(e)}")
            return ""
    
    def extract_code_from_text(self, text: str, keyword: str) -> Optional[str]:
        """استخراج الكود من النص بعد الكلمة المفتاحية"""
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        keyword_patterns = [
            keyword,
            keyword.replace(' ', ''),
            keyword.replace(' ', '.*')
        ]
        
        for pattern in keyword_patterns:
            regex = f"{re.escape(pattern)}[\s:]*([0-9]{{4,8}})"
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        code_match = re.search(r'\b([0-9]{4,8})\b', text)
        if code_match:
            return code_match.group(1)
        
        return None
    
    def auto_detect_keyword(self, image: np.ndarray, known_keywords: List[str]) -> Optional[str]:
        """الكشف التلقائي عن الكلمة المفتاحية"""
        text = self.ocr_tesseract(image)
        
        for keyword in known_keywords:
            if keyword.lower() in text.lower():
                return keyword
        
        return None
    
    def auto_detect_code_roi(self, image: np.ndarray) -> Optional[Dict]:
        """الكشف التلقائي عن منطقة الكود"""
        try:
            results = self.easyocr_reader.readtext(image)
            
            for (bbox, text, prob) in results:
                if re.search(r'[0-9]{4,8}', text):
                    (top_left, top_right, bottom_right, bottom_left) = bbox
                    x = min(top_left[0], bottom_left[0])
                    y = min(top_left[1], top_right[1])
                    w = max(top_right[0], bottom_right[0]) - x
                    h = max(bottom_left[1], bottom_right[1]) - y
                    
                    img_h, img_w = image.shape[:2]
                    return {
                        'x': x / img_w,
                        'y': y / img_h,
                        'width': w / img_w,
                        'height': h / img_h
                    }
        except Exception as e:
            logger.error(f"Auto detect ROI error: {str(e)}")
        
        return None
    
    def process_page(self, pdf_path: str, page_num: int, config: Dict) -> Optional[str]:
        """معالجة صفحة واحدة واستخراج الكود"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            if config.get('rotation', 0) != 0:
                image = self.rotate_image(image, config['rotation'])
            
            if config.get('code_roi'):
                roi_image = self.extract_roi(image, config['code_roi'])
            else:
                roi_image = image
            
            processed = self.preprocess_image(roi_image)
            
            text_tesseract = self.ocr_tesseract(processed)
            text_easyocr = self.ocr_easyocr(processed)
            
            combined_text = text_tesseract + " " + text_easyocr
            
            keyword = config.get('keyword', '')
            code = self.extract_code_from_text(combined_text, keyword)
            
            doc.close()
            return code
        
        except Exception as e:
            logger.error(f"Error processing page {page_num} of {pdf_path}: {str(e)}")
            return None
    
    def process_pdf(self, file_path: str, config: Dict, nom: str) -> Dict[str, List]:
        """معالجة ملف PDF كامل"""
        codes_data = {}
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            doc.close()
            
            pages_per_code = config.get('pages_per_code', 1)
            
            page_num = 0
            while page_num < total_pages:
                code = self.process_page(file_path, page_num, config)
                
                if code:
                    if code not in codes_data:
                        codes_data[code] = []
                    
                    pages_to_include = [page_num]
                    for i in range(1, pages_per_code):
                        if page_num + i < total_pages:
                            pages_to_include.append(page_num + i)
                    
                    for p in pages_to_include:
                        codes_data[code].append({
                            'source_path': file_path,
                            'page_num': p,
                            'code': code
                        })
                    
                    page_num += len(pages_to_include)
                else:
                    page_num += 1
        
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
        
        return codes_data