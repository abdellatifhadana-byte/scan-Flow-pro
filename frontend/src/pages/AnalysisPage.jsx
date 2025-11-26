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
    <div className="page-container" dir="rtl">
      <div className="page-header">
        <h1 className="page-title">تحليل الملفات</h1>
        <p className="page-subtitle">الرجاء الانتظار أثناء معالجة الملفات...</p>
      </div>

      <div className="card text-center">
        <div className="mb-6">
          {getStatusIcon()}
        </div>
        
        <h2 className="text-2xl font-bold mb-4" data-testid="analysis-status">{getStatusText()}</h2>
        
        {analysis && (
          <>
            <Progress value={analysis.progress || 0} className="w-full mb-4" data-testid="analysis-progress" />
            <p className="text-gray-600 mb-6">{Math.round(analysis.progress || 0)}% مكتمل</p>
          </>
        )}

        {analysis?.status === 'completed' && (
          <Button
            size="lg"
            onClick={() => navigate(`/results/${analysisId}`)}
            data-testid="view-results-btn"
          >
            <ArrowRight size={20} className="ml-2" />
            عرض النتائج
          </Button>
        )}

        {analysis?.status === 'failed' && (
          <Button
            variant="outline"
            onClick={() => navigate('/')}
          >
            العودة للبداية
          </Button>
        )}
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">سجل الأحداث</h3>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {logs.map((log, index) => (
            <div
              key={index}
              className={`p-3 rounded ${
                log.type === 'success'
                  ? 'bg-green-50 text-green-800'
                  : log.type === 'error'
                  ? 'bg-red-50 text-red-800'
                  : 'bg-blue-50 text-blue-800'
              }`}
              data-testid={`log-entry-${index}`}
            >
              <span className="font-mono text-sm">[{log.timestamp}]</span> {log.message}
            </div>
          ))}
          {logs.length === 0 && (
            <p className="text-gray-500 text-center py-8">لا توجد أحداث بعد...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisPage;