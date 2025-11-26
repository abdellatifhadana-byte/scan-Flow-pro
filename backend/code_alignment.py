import logging
from typing import List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)

class CodeAlignment:
    """
    خوارزمية محاذاة الأكواد الذكية
    تتحقق من تطابق الأكواد عبر الملفات واختيار الأفضل حسب الثقة
    """
    
    def align_codes(self, all_pages_data: List[Dict]) -> List[Dict]:
        """
        محاذاة الأكواد عبر الملفات المختلفة
        
        Args:
            all_pages_data: قائمة بمعلومات كل الصفحات من كل الملفات
            
        Returns:
            قائمة بالصفحات مع الأكواد المحاذاة
        """
        logger.info(f"Starting code alignment for {len(all_pages_data)} pages")
        
        # تجميع الصفحات حسب رقم الصفحة (الموضع)
        pages_by_position = defaultdict(list)
        
        for page_data in all_pages_data:
            # استخدام page_num كمؤشر للموضع
            position = page_data['page_num']
            pages_by_position[position].append(page_data)
        
        logger.info(f"Grouped pages into {len(pages_by_position)} positions")
        
        # لكل موضع، اختر الكود بأعلى ثقة
        aligned_pages = []
        
        for position in sorted(pages_by_position.keys()):
            pages_at_position = pages_by_position[position]
            
            # إيجاد الصفحة بأعلى ثقة
            best_page = max(pages_at_position, key=lambda p: p['confidence'])
            best_code = best_page['code']
            best_confidence = best_page['confidence']
            
            logger.info(f"Position {position}: Best code = {best_code} (confidence: {best_confidence:.2f}%)")
            candidates_info = [(p['file_id'][:8], p['code'], f"{p['confidence']:.2f}%") for p in pages_at_position]
            logger.info(f"  Candidates: {candidates_info}")
            
            # تطبيق الكود الأفضل على جميع الصفحات في هذا الموضع
            for page in pages_at_position:
                aligned_page = page.copy()
                aligned_page['original_code'] = page['code']
                aligned_page['original_confidence'] = page['confidence']
                aligned_page['aligned_code'] = best_code
                aligned_page['aligned_confidence'] = best_confidence
                aligned_page['code_source'] = best_page['file_id']
                
                # تحديد حالة الثقة
                if page['confidence'] >= 80:
                    aligned_page['confidence_level'] = 'high'
                elif page['confidence'] >= 50:
                    aligned_page['confidence_level'] = 'medium'
                else:
                    aligned_page['confidence_level'] = 'low'
                
                aligned_pages.append(aligned_page)
        
        logger.info(f"Code alignment completed: {len(aligned_pages)} aligned pages")
        return aligned_pages
    
    def group_by_code(self, aligned_pages: List[Dict]) -> Dict[str, List[Dict]]:
        """
        تجميع الصفحات حسب الكود المحاذى
        
        Args:
            aligned_pages: قائمة الصفحات المحاذاة
            
        Returns:
            قاموس: {code: [pages]}
        """
        grouped = defaultdict(list)
        
        for page in aligned_pages:
            code = page['aligned_code']
            if code:
                grouped[code].append(page)
        
        logger.info(f"Grouped {len(aligned_pages)} pages into {len(grouped)} codes")
        return dict(grouped)
    
    def generate_statistics(self, aligned_pages: List[Dict]) -> Dict:
        """
        إحصائيات عن عملية المحاذاة
        """
        total = len(aligned_pages)
        high_confidence = sum(1 for p in aligned_pages if p.get('confidence_level') == 'high')
        medium_confidence = sum(1 for p in aligned_pages if p.get('confidence_level') == 'medium')
        low_confidence = sum(1 for p in aligned_pages if p.get('confidence_level') == 'low')
        
        codes_changed = sum(1 for p in aligned_pages 
                           if p.get('original_code') != p.get('aligned_code'))
        
        stats = {
            'total_pages': total,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'codes_changed': codes_changed,
            'alignment_rate': (codes_changed / total * 100) if total > 0 else 0
        }
        
        logger.info(f"Alignment statistics: {stats}")
        return stats
