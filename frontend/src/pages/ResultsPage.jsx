import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { FileText, Download, FolderOpen, ArrowRight, Eye, Package, CheckCircle2, AlertCircle, XCircle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ResultsPage = () => {
  const { analysisId } = useParams();
  const navigate = useNavigate();
  const [results, setResults] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [previewFile, setPreviewFile] = useState(null);
  const [groupedResults, setGroupedResults] = useState({});

  useEffect(() => {
    loadResults();
  }, [analysisId]);

  const loadResults = async () => {
    try {
      const response = await axios.get(`${API}/results/${analysisId}`);
      const resultsData = response.data.results || [];
      setResults(resultsData);
      
      // تجميع النتائج حسب الكود
      const grouped = resultsData.reduce((acc, result) => {
        const code = result.code || result.aligned_code;
        if (!acc[code]) {
          acc[code] = [];
        }
        acc[code].push(result);
        return acc;
      }, {});
      setGroupedResults(grouped);
      
      // تحميل الإحصائيات
      const analysisResponse = await axios.get(`${API}/analysis/${analysisId}`);
      setStatistics(analysisResponse.data.statistics);
      
      setLoading(false);
    } catch (error) {
      toast.error('خطأ في تحميل النتائج');
      setLoading(false);
    }
  };

  const handleDownload = async (code, filename) => {
    try {
      const response = await axios.get(
        `${API}/download/${code}/${filename}`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('تم تحميل الملف');
    } catch (error) {
      toast.error('خطأ في تحميل الملف');
    }
  };

  const handlePreview = (result) => {
    setPreviewFile(result);
  };

  const getConfidenceBadge = (confidence, level) => {
    if (level === 'high' || confidence >= 80) {
      return <Badge className="bg-green-500"><CheckCircle2 size={14} className="ml-1" /> عالية {confidence?.toFixed(0)}%</Badge>;
    } else if (level === 'medium' || confidence >= 50) {
      return <Badge className="bg-yellow-500"><AlertCircle size={14} className="ml-1" /> متوسطة {confidence?.toFixed(0)}%</Badge>;
    } else {
      return <Badge className="bg-red-500"><XCircle size={14} className="ml-1" /> منخفضة {confidence?.toFixed(0)}%</Badge>;
    }
  };

  const handleDownloadAll = async (code) => {
    try {
      toast.info(`جاري تحضير ملفات الكود ${code}...`);
      
      const filesInCode = groupedResults[code] || [];
      
      for (const file of filesInCode) {
        await handleDownload(file.code, file.filename);
        await new Promise(resolve => setTimeout(resolve, 500)); // تأخير بسيط بين التحميلات
      }
      
      toast.success(`تم تحميل جميع ملفات الكود ${code}`);
    } catch (error) {
      toast.error('خطأ في تحميل الملفات');
    }
  };

  if (loading) {
    return (
      <div className="page-container" dir="rtl">
        <div className="flex justify-center items-center min-h-screen">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container" dir="rtl">
      <div className="page-header">
        <h1 className="page-title">نتائج التحليل</h1>
        <p className="page-subtitle">تم استخراج {Object.keys(groupedResults).length} كود من {results.length} ملف</p>
      </div>

      <div className="flex gap-4 mb-4">
        <div className="card flex-1">
          <Button variant="outline" onClick={() => navigate('/')}>
            <ArrowRight size={16} className="ml-2" />
            العودة للبداية
          </Button>
        </div>
        
        {statistics && (
          <div className="card flex-1">
            <h3 className="text-sm font-semibold mb-2">إحصائيات الثقة</h3>
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-1">
                <CheckCircle2 size={16} className="text-green-500" />
                <span>عالية: {statistics.high_confidence}</span>
              </div>
              <div className="flex items-center gap-1">
                <AlertCircle size={16} className="text-yellow-500" />
                <span>متوسطة: {statistics.medium_confidence}</span>
              </div>
              <div className="flex items-center gap-1">
                <XCircle size={16} className="text-red-500" />
                <span>منخفضة: {statistics.low_confidence}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {results.length === 0 ? (
        <div className="card text-center py-12">
          <FileText size={64} className="mx-auto mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold mb-2">لا توجد نتائج</h3>
          <p className="text-gray-500">لم يتم استخراج أي أكواد من الملفات</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedResults).map(([code, files]) => (
            <div key={code} className="card" data-testid={`code-group-${code}`}>
              <div className="flex items-center justify-between mb-4 pb-3 border-b">
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold text-blue-600">الكود: {code}</h2>
                  <Badge variant="outline">{files.length} ملف</Badge>
                </div>
                <Button
                  variant="outline"
                  onClick={() => handleDownloadAll(code)}
                  data-testid={`download-all-${code}`}
                >
                  <Package size={16} className="ml-2" />
                  تحميل الكل
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {files.map((result, idx) => (
                  <div
                    key={idx}
                    className="flex gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                    data-testid={`result-item-${code}-${idx}`}
                  >
                    {/* صورة مصغرة */}
                    <div className="w-24 h-24 bg-white rounded border overflow-hidden flex-shrink-0">
                      {result.thumbnail ? (
                        <img
                          src={`${API}/thumbnail/${result.thumbnail.split('/').pop()}`}
                          alt="ROI"
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <div className="w-full h-full flex items-center justify-center text-gray-400" style={{display: result.thumbnail ? 'none' : 'flex'}}>
                        <FileText size={32} />
                      </div>
                    </div>

                    {/* المعلومات */}
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-bold text-lg">{result.filename}</h3>
                          <p className="text-sm text-gray-600">
                            الملف الأب: {result.source_filename} • الصفحة: {result.source_page + 1}
                          </p>
                        </div>
                        {getConfidenceBadge(result.confidence, result.confidence_level)}
                      </div>

                      <div className="flex gap-4 text-sm text-gray-600 mb-3">
                        <span>📄 {result.page_count} صفحة</span>
                        <span>📝 {result.nom}</span>
                        {result.original_code !== result.aligned_code && (
                          <span className="text-orange-600">
                            ⚠️ تم التعديل من: {result.original_code}
                          </span>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePreview(result)}
                          data-testid={`preview-btn-${code}-${idx}`}
                        >
                          <Eye size={14} className="ml-1" />
                          معاينة
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(result.code, result.filename)}
                          data-testid={`download-btn-${code}-${idx}`}
                        >
                          <Download size={14} className="ml-1" />
                          تحميل
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!previewFile} onOpenChange={() => setPreviewFile(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>معاينة: {previewFile?.filename}</DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {previewFile && (
              <iframe
                src={`${API}/download/${previewFile.code}/${previewFile.filename}`}
                className="w-full h-[70vh] border rounded"
                title="PDF Preview"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ResultsPage;