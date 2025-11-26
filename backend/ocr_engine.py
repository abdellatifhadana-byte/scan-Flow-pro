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
    def __init__(self, use_easyocr=False):
        self.tesseract_langs = 'ara+fra+eng'
        self.use_easyocr = use_easyocr
        self.easyocr_reader_ar = None
        self.easyocr_reader_fr = None
        
        if use_easyocr:
            try:
                self.easyocr_reader_ar = easyocr.Reader(['ar', 'en'], gpu=False)
                self.easyocr_reader_fr = easyocr.Reader(['fr', 'en'], gpu=False)
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR: {str(e)}")
                self.use_easyocr = False
    
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
    
    def ocr_tesseract(self, image: np.ndarray) -> tuple:
        """OCR باستخدام Tesseract - يرجع (text, confidence)"""
        try:
            # استخراج النص
            text = pytesseract.image_to_string(
                image,
                lang=self.tesseract_langs,
                config='--psm 6'
            )
            
            # استخراج البيانات التفصيلية مع الثقة
            data = pytesseract.image_to_data(
                image,
                lang=self.tesseract_langs,
                config='--psm 6',
                output_type=pytesseract.Output.DICT
            )
            
            # حساب متوسط الثقة للنص المستخرج
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return text.strip(), avg_confidence
        except Exception as e:
            logger.error(f"Tesseract OCR error: {str(e)}")
            return "", 0
    
    def ocr_easyocr(self, image: np.ndarray, use_arabic: bool = True) -> str:
        """OCR باستخدام EasyOCR"""
        if not self.use_easyocr or (self.easyocr_reader_ar is None and self.easyocr_reader_fr is None):
            return ""
        
        try:
            reader = self.easyocr_reader_ar if use_arabic else self.easyocr_reader_fr
            if reader is None:
                return ""
            results = reader.readtext(image, detail=0)
            return ' '.join(results)
        except Exception as e:
            logger.error(f"EasyOCR error: {str(e)}")
            return ""
    
    def extract_code_from_text(self, text: str, keyword: str, base_confidence: float = 0) -> tuple:
        """استخراج الكود من النص بعد الكلمة المفتاحية - يرجع (code, confidence)"""
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        logger.info(f"Extracting code from text (length: {len(text)})")
        logger.info(f"Keyword: '{keyword}'")
        logger.info(f"Text preview: {text[:200]}")
        logger.info(f"Base OCR confidence: {base_confidence:.2f}%")
        
        # تنظيف النص من الرموز والمسافات الزائدة
        cleaned_text = re.sub(r'[|،,.\s]+', ' ', text).strip()
        logger.info(f"Cleaned text: {cleaned_text}")
        
        confidence = base_confidence
        
        # البحث عن الكلمة المفتاحية والكود بعدها
        if keyword.strip():
            keyword_patterns = [
                keyword,
                keyword.replace(' ', ''),
                keyword.replace(' ', '.*')
            ]
            
            for pattern in keyword_patterns:
                regex = f"{re.escape(pattern)}[\\s:.-]*([0-9]{{4,8}})"
                match = re.search(regex, text, re.IGNORECASE)
                if match:
                    code = match.group(1)
                    # ثقة عالية: وجدنا الكلمة المفتاحية والكود
                    confidence = min(100, base_confidence + 20)
                    logger.info(f"✓ Code found with keyword: {code} (confidence: {confidence:.2f}%)")
                    return code, confidence
        
        # البحث عن أي كود رقمي (4-8 أرقام) مباشرة في النص
        all_numbers = re.findall(r'[0-9]+', cleaned_text)
        logger.info(f"Found numbers in text: {all_numbers}")
        
        for num in all_numbers:
            if 4 <= len(num) <= 8:
                # ثقة متوسطة: وجدنا كود بدون كلمة مفتاحية
                confidence = base_confidence
                logger.info(f"✓ Code found (direct): {num} (confidence: {confidence:.2f}%)")
                return num, confidence
        
        # محاولة استخراج من النص الأصلي أيضاً
        code_match = re.search(r'([0-9]{4,8})', text)
        if code_match:
            code = code_match.group(1)
            # ثقة أقل: محاولة أخيرة
            confidence = max(0, base_confidence - 10)
            logger.info(f"✓ Code found (fallback): {code} (confidence: {confidence:.2f}%)")
            return code, confidence
        
        logger.warning(f"✗ No code found in text")
        return None, 0
    
    def auto_detect_keyword(self, image: np.ndarray, known_keywords: List[str]) -> Optional[str]:
        """الكشف التلقائي عن الكلمة المفتاحية"""
        text = self.ocr_tesseract(image)
        
        for keyword in known_keywords:
            if keyword.lower() in text.lower():
                return keyword
        
        return None
    
    def auto_detect_code_roi(self, image: np.ndarray) -> Optional[Dict]:
        """الكشف التلقائي عن منطقة الكود"""
        if not self.use_easyocr or self.easyocr_reader_ar is None:
            return None
            
        try:
            results = self.easyocr_reader_ar.readtext(image)
            
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
    
    def process_page(self, pdf_path: str, page_num: int, config: Dict) -> tuple:
        """معالجة صفحة واحدة واستخراج الكود"""
        try:
            logger.info(f"Processing page {page_num} from {pdf_path}")
            
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            logger.info(f"Image size: {image.shape}")
            
            if config.get('rotation', 0) != 0:
                image = self.rotate_image(image, config['rotation'])
                logger.info(f"Rotated image by {config['rotation']} degrees")
            
            if config.get('code_roi'):
                roi_image = self.extract_roi(image, config['code_roi'])
                logger.info(f"Extracted ROI, size: {roi_image.shape}")
            else:
                roi_image = image
                logger.info("Using full page (no ROI)")
            
            processed = self.preprocess_image(roi_image)
            logger.info("Image preprocessing completed")
            
            text_tesseract = self.ocr_tesseract(processed)
            logger.info(f"Tesseract OCR result length: {len(text_tesseract)}")
            
            combined_text = text_tesseract
            
            if self.use_easyocr:
                text_easyocr_ar = self.ocr_easyocr(processed, use_arabic=True)
                text_easyocr_fr = self.ocr_easyocr(processed, use_arabic=False)
                combined_text += " " + text_easyocr_ar + " " + text_easyocr_fr
                logger.info("EasyOCR completed")
            
            keyword = config.get('keyword', '')
            code = self.extract_code_from_text(combined_text, keyword)
            
            doc.close()
            
            if code:
                logger.info(f"✓ Successfully extracted code: {code} from page {page_num}")
            else:
                logger.warning(f"✗ Failed to extract code from page {page_num}")
            
            return code
        
        except Exception as e:
            logger.error(f"Error processing page {page_num} of {pdf_path}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
                            'code': code,
                            'nom': nom
                        })
                    
                    page_num += len(pages_to_include)
                else:
                    page_num += 1
        
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
        
        return codes_data