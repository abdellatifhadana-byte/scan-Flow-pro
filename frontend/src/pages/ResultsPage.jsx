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
  const [loading, setLoading] = useState(true);
  const [previewFile, setPreviewFile] = useState(null);

  useEffect(() => {
    loadResults();
  }, [analysisId]);

  const loadResults = async () => {
    try {
      const response = await axios.get(`${API}/results/${analysisId}`);
      setResults(response.data.results || []);
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
        <p className="page-subtitle">تم استخراج {results.length} كود</p>
      </div>

      <div className="card mb-4">
        <Button variant="outline" onClick={() => navigate('/')}>
          <ArrowRight size={16} className="ml-2" />
          العودة للبداية
        </Button>
      </div>

      {results.length === 0 ? (
        <div className="card text-center py-12">
          <FileText size={64} className="mx-auto mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold mb-2">لا توجد نتائج</h3>
          <p className="text-gray-500">لم يتم استخراج أي أكواد من الملفات</p>
        </div>
      ) : (
        <div className="card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-right">الكود</TableHead>
                <TableHead className="text-right">عدد الصفحات</TableHead>
                <TableHead className="text-right">اسم المللف</TableHead>
                <TableHead className="text-right">الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result, index) => (
                <TableRow key={index} data-testid={`result-row-${result.code}`}>
                  <TableCell className="font-mono font-bold text-blue-600">
                    {result.code}
                  </TableCell>
                  <TableCell>{result.page_count}</TableCell>
                  <TableCell className="font-medium">{result.filename}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handlePreview(result)}
                        data-testid={`preview-btn-${result.code}`}
                      >
                        <Eye size={16} className="ml-1" />
                        معاينة
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(result.code, result.filename)}
                        data-testid={`download-btn-${result.code}`}
                      >
                        <Download size={16} className="ml-1" />
                        تحميل
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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