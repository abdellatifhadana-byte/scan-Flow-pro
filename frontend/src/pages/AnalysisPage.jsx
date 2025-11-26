import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { CheckCircle2, XCircle, Loader2, ArrowRight, FileText, Hash, Clock } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AnalysisPage = () => {
  const { analysisId } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState(null);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchAnalysisStatus();
    }, 2000);

    return () => clearInterval(interval);
  }, [analysisId]);

  const fetchAnalysisStatus = async () => {
    try {
      const response = await axios.get(`${API}/analysis/${analysisId}`);
      setAnalysis(response.data);
      
      if (response.data.status === 'completed') {
        addLog('تم إكمال التحليل بنجاح!', 'success');
      } else if (response.data.status === 'failed') {
        addLog(`فشل التحليل: ${response.data.error}`, 'error');
      }
    } catch (error) {
      console.error('Error fetching analysis status:', error);
    }
  };

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString('ar-EG');
    setLogs(prev => [...prev, { message, type, timestamp }]);
  };

  const getStatusIcon = () => {
    if (!analysis) return <Loader2 className="animate-spin" size={24} />;
    
    switch (analysis.status) {
      case 'completed':
        return <CheckCircle2 size={48} className="text-green-500" />;
      case 'failed':
        return <XCircle size={48} className="text-red-500" />;
      default:
        return <Loader2 className="animate-spin" size={48} className="text-blue-500" />;
    }
  };

  const getStatusText = () => {
    if (!analysis) return 'جاري التحميل...';
    
    switch (analysis.status) {
      case 'completed':
        return 'اكتمل التحليل';
      case 'failed':
        return 'فشل التحليل';
      default:
        return 'جاري التحليل...';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50" dir="rtl">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">تحليل الملفات</h1>
          <p className="text-gray-600">جاري استخراج البيانات من المستندات...</p>
        </div>

        {/* Status Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
          <div className="flex items-center justify-center mb-6">
            {getStatusIcon()}
          </div>
          
          <h2 className="text-3xl font-bold text-center mb-6 text-gray-800" data-testid="analysis-status">
            {getStatusText()}
          </h2>
          
          {analysis && (
            <div className="mb-6">
              <Progress value={analysis.progress || 0} className="h-3 mb-3" data-testid="analysis-progress" />
              <div className="flex justify-between text-sm text-gray-600">
                <span>{Math.round(analysis.progress || 0)}%</span>
                <span>مكتمل</span>
              </div>
            </div>
          )}

          {analysis?.status === 'completed' && (
            <div className="text-center">
              <Button
                size="lg"
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-3 text-lg"
                onClick={() => navigate(`/results/${analysisId}`)}
                data-testid="view-results-btn"
              >
                <ArrowRight size={24} className="ml-2" />
                عرض النتائج
              </Button>
            </div>
          )}

          {analysis?.status === 'failed' && (
            <div className="text-center">
              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate('/')}
              >
                العودة للبداية
              </Button>
            </div>
          )}
        </div>

        {/* Processing Details */}
        {analysis?.results && analysis.results.length > 0 && (
          <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
            <h3 className="text-xl font-bold mb-4 text-gray-800">التفاصيل المعالجة</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
              {analysis.results.slice(-9).reverse().map((result, index) => (
                <div
                  key={index}
                  className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-4 border-2 border-blue-100 hover:border-blue-300 transition-all"
                >
                  <div className="flex items-start gap-3">
                    <FileText className="text-blue-600 flex-shrink-0 mt-1" size={20} />
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-gray-800 text-sm truncate mb-1">
                        {result.source_filename || 'ملف'}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
                        <Hash size={14} />
                        <span>صفحة {result.source_page + 1}</span>
                      </div>
                      {result.aligned_code && (
                        <div className="bg-white rounded-lg px-3 py-2 mt-2">
                          <p className="text-xs text-gray-500 mb-1">الكود المستخرج:</p>
                          <p className="font-mono font-bold text-lg text-blue-600">
                            {result.aligned_code}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Activity Log */}
        <div className="bg-white rounded-2xl shadow-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="text-gray-600" size={20} />
            <h3 className="text-xl font-bold text-gray-800">سجل النشاط</h3>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {logs.map((log, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border-l-4 ${
                  log.type === 'success'
                    ? 'bg-green-50 border-green-500 text-green-800'
                    : log.type === 'error'
                    ? 'bg-red-50 border-red-500 text-red-800'
                    : 'bg-blue-50 border-blue-500 text-blue-800'
                }`}
                data-testid={`log-entry-${index}`}
              >
                <span className="font-mono text-xs opacity-75">[{log.timestamp}]</span>{' '}
                <span className="font-medium">{log.message}</span>
              </div>
            ))}
            {logs.length === 0 && (
              <p className="text-gray-400 text-center py-8">لا توجد أحداث بعد...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisPage;