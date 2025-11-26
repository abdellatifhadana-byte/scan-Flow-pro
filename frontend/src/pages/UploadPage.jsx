import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Upload, FileText, Trash2, Settings, Play } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UploadPage = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [nom, setNom] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const response = await axios.get(`${API}/files`);
      setFiles(response.data);
    } catch (error) {
      console.error('Error loading files:', error);
    }
  };

  const handleFileUpload = async (selectedFiles) => {
    setUploading(true);
    
    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await axios.post(`${API}/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        toast.success(`تم رفع ${file.name} بنجاح`);
      } catch (error) {
        toast.error(`خطأ في رفع ${file.name}`);
      }
    }
    
    setUploading(false);
    loadFiles();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      f => f.type === 'application/pdf'
    );
    if (droppedFiles.length > 0) {
      handleFileUpload(droppedFiles);
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await axios.delete(`${API}/files/${fileId}`);
      toast.success('تم حذف الملف');
      loadFiles();
    } catch (error) {
      toast.error('خطأ في حذف الملف');
    }
  };

  const handleStartAnalysis = async () => {
    if (files.length === 0) {
      toast.error('الرجاء رفع ملفات أولاً');
      return;
    }

    const unconfiguredFiles = files.filter(f => !f.config);
    if (unconfiguredFiles.length > 0) {
      toast.error('بعض الملفات لم يتم إعدادها بعد');
      return;
    }
    
    const filesWithoutNom = files.filter(f => !f.config?.nom);
    if (filesWithoutNom.length > 0) {
      toast.error('بعض الملفات لا تحتوي على اسم (nom). الرجاء إعدادها.');
      return;
    }

    try {
      const response = await axios.post(`${API}/analyze`, {
        file_ids: files.map(f => f.file_id),
        merge_enabled: true
      });
      
      toast.success('بدأ التحليل');
      navigate(`/analysis/${response.data.analysis_id}`);
    } catch (error) {
      toast.error('خطأ في بدء التحليل');
    }
  };

  return (
    <div className="page-container" dir="rtl">
      <div className="page-header">
        <h1 className="page-title">ScanFlow Pro</h1>
        <p className="page-subtitle">نظام معالجة وتحليل ملفات PDF الاحترافي</p>
      </div>

      <div className="card">
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input').click()}
          data-testid="upload-zone"
        >
          <Upload size={48} className="mx-auto mb-4 text-blue-500" />
          <h3 className="text-xl font-semibold mb-2">اسحب الملفات هنا أو انقر للاختيار</h3>
          <p className="text-gray-500">يدعم ملفات PDF فقط</p>
          <input
            id="file-input"
            type="file"
            multiple
            accept=".pdf"
            onChange={(e) => handleFileUpload(Array.from(e.target.files))}
            style={{ display: 'none' }}
            data-testid="file-input"
          />
        </div>
      </div>

      {uploading && (
        <div className="card">
          <p className="text-center mb-2">جاري رفع الملفات...</p>
          <Progress value={50} className="w-full" />
        </div>
      )}

      <div className="card">
        <div className="mb-4">
          <h3 className="text-lg font-semibold mb-3">الملفات المرفوعة ({files.length})</h3>
          {files.map((file) => (
            <div key={file.file_id} className="file-item" data-testid={`file-item-${file.file_id}`}>
              <div className="flex items-center gap-3 flex-1">
                <FileText size={24} className="text-blue-500" />
                <div>
                  <p className="font-semibold">{file.filename}</p>
                  <p className="text-sm text-gray-500">
                    {file.page_count} صفحة • {(file.size / 1024).toFixed(2)} KB
                  </p>
                  {file.config ? (
                    <span className="badge badge-success">تم الإعداد ✓</span>
                  ) : (
                    <span className="badge badge-warning">بحاجة للإعداد</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/roi/${file.file_id}`)}
                  data-testid={`config-btn-${file.file_id}`}
                >
                  <Settings size={16} className="ml-1" />
                  إعداد
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDeleteFile(file.file_id)}
                  data-testid={`delete-btn-${file.file_id}`}
                >
                  <Trash2 size={16} />
                </Button>
              </div>
            </div>
          ))}
        </div>

        <Button
          className="w-full"
          size="lg"
          onClick={handleStartAnalysis}
          disabled={files.length === 0 || !nom.trim()}
          data-testid="start-analysis-btn"
        >
          <Play size={20} className="ml-2" />
          بدء التحليل
        </Button>
      </div>
    </div>
  );
};

export default UploadPage;