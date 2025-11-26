import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ZoomIn, ZoomOut, RotateCw, Save, ArrowRight } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ROIEditor = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const [file, setFile] = useState(null);
  const [pageImage, setPageImage] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [keyword, setKeyword] = useState('');
  const [keywords, setKeywords] = useState([]);
  const [nom, setNom] = useState('');
  const [pagesPerCode, setPagesPerCode] = useState(1);
  const [codeROI, setCodeROI] = useState(null);
  const [keywordROI, setKeywordROI] = useState(null);
  const [drawing, setDrawing] = useState(null);
  const [startPos, setStartPos] = useState(null);

  useEffect(() => {
    loadFileData();
    loadKeywords();
  }, [fileId]);

  useEffect(() => {
    if (file) {
      loadPageImage(currentPage);
    }
  }, [file, currentPage]);

  useEffect(() => {
    if (pageImage && canvasRef.current) {
      drawCanvas();
    }
  }, [pageImage, zoom, codeROI, keywordROI]);

  const loadFileData = async () => {
    try {
      const response = await axios.get(`${API}/files`);
      const fileData = response.data.find(f => f.file_id === fileId);
      setFile(fileData);
      
      if (fileData?.config) {
        setKeyword(fileData.config.keyword || '');
        setRotation(fileData.config.rotation || 0);
        setCodeROI(fileData.config.code_roi);
        setKeywordROI(fileData.config.keyword_roi);
        setPagesPerCode(fileData.config.pages_per_code || 1);
      }
    } catch (error) {
      toast.error('خطأ في تحميل بيانات الملف');
    }
  };

  const loadKeywords = async () => {
    try {
      const response = await axios.get(`${API}/keywords`);
      setKeywords(response.data);
    } catch (error) {
      console.error('Error loading keywords:', error);
    }
  };

  const loadPageImage = async (pageNum) => {
    try {
      const response = await axios.get(
        `${API}/files/${fileId}/preview/${pageNum}`,
        { responseType: 'blob' }
      );
      const imageUrl = URL.createObjectURL(response.data);
      const img = new Image();
      img.onload = () => setPageImage(img);
      img.src = imageUrl;
    } catch (error) {
      toast.error('خطأ في تحميل الصورة');
    }
  };

  const drawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas || !pageImage) return;

    const ctx = canvas.getContext('2d');
    const scaledWidth = pageImage.width * zoom;
    const scaledHeight = pageImage.height * zoom;
    
    canvas.width = scaledWidth;
    canvas.height = scaledHeight;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(pageImage, 0, 0, scaledWidth, scaledHeight);

    if (codeROI) {
      drawROI(ctx, codeROI, scaledWidth, scaledHeight, '#667eea', 'منطقة الكود');
    }

    if (keywordROI) {
      drawROI(ctx, keywordROI, scaledWidth, scaledHeight, '#f59e0b', 'منطقة الكلمة المفتاحية');
    }
  };

  const drawROI = (ctx, roi, width, height, color, label) => {
    const x = roi.x * width;
    const y = roi.y * height;
    const w = roi.width * width;
    const h = roi.height * height;

    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = color + '30';
    ctx.fillRect(x, y, w, h);

    ctx.fillStyle = color;
    ctx.font = '16px Arial';
    ctx.fillText(label, x + 5, y + 20);
  };

  const handleMouseDown = (e) => {
    if (!drawing) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / canvas.width;
    const y = (e.clientY - rect.top) / canvas.height;
    
    setStartPos({ x, y });
  };

  const handleMouseUp = (e) => {
    if (!drawing || !startPos) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / canvas.width;
    const y = (e.clientY - rect.top) / canvas.height;

    const roi = {
      x: Math.min(startPos.x, x),
      y: Math.min(startPos.y, y),
      width: Math.abs(x - startPos.x),
      height: Math.abs(y - startPos.y)
    };

    if (drawing === 'code') {
      setCodeROI(roi);
    } else if (drawing === 'keyword') {
      setKeywordROI(roi);
    }

    setStartPos(null);
    setDrawing(null);
  };

  const handleSave = async () => {
    if (!keyword.trim()) {
      toast.error('الرجاء إدخال الكلمة المفتاحية');
      return;
    }

    try {
      if (!keywords.includes(keyword)) {
        await axios.post(`${API}/keywords?keyword=${encodeURIComponent(keyword)}`);
      }

      await axios.post(`${API}/files/${fileId}/config`, {
        file_id: fileId,
        keyword: keyword,
        code_roi: codeROI,
        keyword_roi: keywordROI,
        rotation: rotation,
        pages_per_code: pagesPerCode,
        auto_detect: false
      });

      toast.success('تم حفظ الإعدادات بنجاح');
      navigate('/');
    } catch (error) {
      toast.error('خطأ في حفظ الإعدادات');
    }
  };

  return (
    <div className="page-container" dir="rtl">
      <div className="page-header">
        <h1 className="page-title">إعداد ROI</h1>
        <p className="page-subtitle">{file?.filename}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="flex gap-2 mb-4 flex-wrap">
              <Button variant="outline" size="sm" onClick={() => setZoom(z => Math.min(z + 0.25, 3))}>
                <ZoomIn size={16} />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setZoom(z => Math.max(z - 0.25, 0.5))}>
                <ZoomOut size={16} />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setRotation(r => (r + 90) % 360)}>
                <RotateCw size={16} />
              </Button>
              <Button 
                variant={drawing === 'code' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDrawing(drawing === 'code' ? null : 'code')}
                data-testid="draw-code-roi-btn"
              >
                رسم منطقة الكود
              </Button>
              <Button 
                variant={drawing === 'keyword' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDrawing(drawing === 'keyword' ? null : 'keyword')}
                data-testid="draw-keyword-roi-btn"
              >
                رسم منطقة الكلمة المفتاحية
              </Button>
            </div>
            
            <div className="overflow-auto" style={{ maxHeight: '70vh' }}>
              <canvas
                ref={canvasRef}
                onMouseDown={handleMouseDown}
                onMouseUp={handleMouseUp}
                style={{ cursor: drawing ? 'crosshair' : 'default' }}
                data-testid="roi-canvas"
              />
            </div>
          </div>
        </div>

        <div>
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">الإعدادات</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">الصفحة الحالية</label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                  disabled={currentPage === 0}
                >
                  السابق
                </Button>
                <span className="flex-1 text-center py-2">{currentPage + 1} / {file?.page_count}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(file.page_count - 1, p + 1))}
                  disabled={currentPage >= (file?.page_count - 1)}
                >
                  التالي
                </Button>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">الكلمة المفتاحية</label>
              <Select value={keyword} onValueChange={setKeyword}>
                <SelectTrigger data-testid="keyword-select">
                  <SelectValue placeholder="اختر أو أدخل كلمة" />
                </SelectTrigger>
                <SelectContent>
                  {keywords.map((kw) => (
                    <SelectItem key={kw} value={kw}>{kw}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="أو أدخل كلمة جديدة"
                className="mt-2"
                data-testid="keyword-input"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">عدد الصفحات التابعة</label>
              <Input
                type="number"
                min="1"
                max="10"
                value={pagesPerCode}
                onChange={(e) => setPagesPerCode(parseInt(e.target.value) || 1)}
                data-testid="pages-per-code-input"
              />
            </div>

            <div className="space-y-2 mb-4">
              {codeROI && (
                <div className="p-2 bg-blue-50 rounded text-sm">
                  ✓ تم تحديد منطقة الكود
                </div>
              )}
              {keywordROI && (
                <div className="p-2 bg-amber-50 rounded text-sm">
                  ✓ تم تحديد منطقة الكلمة المفتاحية
                </div>
              )}
            </div>

            <Button className="w-full mb-2" onClick={handleSave} data-testid="save-config-btn">
              <Save size={16} className="ml-2" />
              حفظ الإعدادات
            </Button>
            
            <Button variant="outline" className="w-full" onClick={() => navigate('/')}>
              <ArrowRight size={16} className="ml-2" />
              العودة
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ROIEditor;