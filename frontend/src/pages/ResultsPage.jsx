import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileText, Download, ArrowRight, CheckCircle2, AlertCircle, XCircle, Search, Package, FileCheck, Files, Trash2, RefreshCw, RotateCcw } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ResultsPage = () => {
  const { analysisId } = useParams();
  const navigate = useNavigate();
  const [allPages, setAllPages] = useState([]);
  const [filteredPages, setFilteredPages] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPages, setSelectedPages] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterByFile, setFilterByFile] = useState('all');
  const [editingCell, setEditingCell] = useState(null);
  const [showCleanupDialog, setShowCleanupDialog] = useState(false);
  const [showRestartDialog, setShowRestartDialog] = useState(false);
  const [showCleanAllDialog, setShowCleanAllDialog] = useState(false);

  useEffect(() => {
    loadResults();
  }, [analysisId]);

  useEffect(() => {
    filterResults();
  }, [searchTerm, filterType, allPages]);

  const loadResults = async () => {
    try {
      const response = await axios.get(`${API}/results/${analysisId}`);
      const resultsData = response.data.results || [];
      
      // تحويل النتائج إلى صفحات فردية
      const pages = resultsData.map((result, idx) => ({
        id: `${result.file_id}-${result.source_page}`,
        index: idx,
        parentFile: result.source_filename,
        pageNumber: result.source_page + 1,
        code: result.aligned_code || result.code,
        originalCode: result.original_code,
        confidence: result.confidence || 0,
        confidenceLevel: result.confidence_level,
        nom: result.nom,
        filename: result.filename,
        thumbnail: result.thumbnail,
        pageCount: result.page_count,
        filePath: result.file_path,
        keyword: result.keyword || '',
        isEdited: false
      }));
      
      setAllPages(pages);
      setFilteredPages(pages);
      
      // تحميل الإحصائيات
      const analysisResponse = await axios.get(`${API}/analysis/${analysisId}`);
      setStatistics(analysisResponse.data.statistics);
      
      setLoading(false);
    } catch (error) {
      toast.error('خطأ في تحميل النتائج');
      setLoading(false);
    }
  };

  const filterResults = () => {
    let filtered = [...allPages];

    // البحث
    if (searchTerm) {
      filtered = filtered.filter(page => {
        const searchLower = searchTerm.toLowerCase();
        return (
          page.code?.toString().includes(searchLower) ||
          page.parentFile?.toLowerCase().includes(searchLower) ||
          page.filename?.toLowerCase().includes(searchLower) ||
          page.nom?.toLowerCase().includes(searchLower) ||
          page.keyword?.toLowerCase().includes(searchLower)
        );
      });
    }

    // الفلترة حسب النوع
    if (filterType !== 'all') {
      filtered = filtered.filter(page => {
        if (filterType === 'high') return page.confidenceLevel === 'high';
        if (filterType === 'medium') return page.confidenceLevel === 'medium';
        if (filterType === 'low') return page.confidenceLevel === 'low';
        if (filterType === 'edited') return page.originalCode !== page.code;
        return true;
      });
    }

    setFilteredPages(filtered);
  };

  const handleSelectPage = (pageId) => {
    setSelectedPages(prev => 
      prev.includes(pageId) 
        ? prev.filter(id => id !== pageId)
        : [...prev, pageId]
    );
  };

  const handleSelectAll = () => {
    if (selectedPages.length === filteredPages.length) {
      setSelectedPages([]);
    } else {
      setSelectedPages(filteredPages.map(p => p.id));
    }
  };

  const handleEditCell = (pageId, field, value) => {
    setAllPages(prev => prev.map(page => 
      page.id === pageId 
        ? { ...page, [field]: value, isEdited: true }
        : page
    ));
  };

  const getConfidenceBadge = (confidence, level) => {
    if (level === 'high' || confidence >= 80) {
      return <Badge className="bg-green-500 flex items-center gap-1"><CheckCircle2 size={14} /> عالية {confidence?.toFixed(0)}%</Badge>;
    } else if (level === 'medium' || confidence >= 50) {
      return <Badge className="bg-yellow-500 flex items-center gap-1"><AlertCircle size={14} /> متوسطة {confidence?.toFixed(0)}%</Badge>;
    } else {
      return <Badge className="bg-red-500 flex items-center gap-1"><XCircle size={14} /> منخفضة {confidence?.toFixed(0)}%</Badge>;
    }
  };

  const handleMergeSelected = async () => {
    if (selectedPages.length === 0) {
      toast.error('الرجاء اختيار صفحات للتجميع');
      return;
    }

    try {
      toast.info(`جاري تجميع ${selectedPages.length} صفحة...`);
      
      const response = await axios.post(`${API}/merge-selected`, {
        analysis_id: analysisId,
        page_ids: selectedPages,
        merge_type: 'merge'
      });
      
      toast.success(`تم التجميع بنجاح! تم إنشاء ${response.data.files.length} ملف`);
      
      // إعادة تحميل النتائج
      loadResults();
    } catch (error) {
      console.error('Merge error:', error);
      toast.error('خطأ في التجميع: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleCreateIndividual = async () => {
    if (selectedPages.length === 0) {
      toast.error('الرجاء اختيار صفحات');
      return;
    }

    try {
      toast.info(`جاري إنشاء ${selectedPages.length} ملف منفصل...`);
      
      const response = await axios.post(`${API}/create-individual`, {
        analysis_id: analysisId,
        page_ids: selectedPages,
        merge_type: 'individual'
      });
      
      toast.success(`تم الإنشاء بنجاح! ${response.data.files.length} ملف`);
      
      loadResults();
    } catch (error) {
      console.error('Create individual error:', error);
      toast.error('خطأ في الإنشاء: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleMergeAll = async () => {
    try {
      toast.info('جاري تجميع جميع الملفات...');
      
      const response = await axios.post(`${API}/merge-all`, {
        analysis_id: analysisId,
        page_ids: [],
        merge_type: 'merge_all'
      });
      
      toast.success(`تم تجميع الكل بنجاح! ${response.data.total_codes} كود`);
      
      loadResults();
    } catch (error) {
      console.error('Merge all error:', error);
      toast.error('خطأ في التجميع الكامل: ' + (error.response?.data?.detail || error.message));
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
        <h1 className="page-title">نتائج التحليل - عرض تفصيلي</h1>
        <p className="page-subtitle">إجمالي {allPages.length} صفحة من {new Set(allPages.map(p => p.parentFile)).size} ملفات</p>
      </div>

      {/* شريط الأدوات */}
      <div className="card mb-4">
        <div className="flex flex-col gap-4">
          {/* الصف الأول: البحث والفلترة */}
          <div className="flex gap-4 items-center">
            <div className="flex-1 relative">
              <Search className="absolute right-3 top-3 text-gray-400" size={20} />
              <Input
                placeholder="ابحث بالكود، الملف، الاسم، أو الكلمة المفتاحية..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pr-10"
                data-testid="search-input"
              />
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">الكل</SelectItem>
                <SelectItem value="high">ثقة عالية</SelectItem>
                <SelectItem value="medium">ثقة متوسطة</SelectItem>
                <SelectItem value="low">ثقة منخفضة</SelectItem>
                <SelectItem value="edited">تم التعديل</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => navigate('/')}>
              <ArrowRight size={16} className="ml-2" />
              العودة
            </Button>
          </div>

          {/* الصف الثاني: الإحصائيات */}
          {statistics && (
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-green-500" />
                <span>عالية: {statistics.high_confidence}</span>
              </div>
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className="text-yellow-500" />
                <span>متوسطة: {statistics.medium_confidence}</span>
              </div>
              <div className="flex items-center gap-2">
                <XCircle size={16} className="text-red-500" />
                <span>منخفضة: {statistics.low_confidence}</span>
              </div>
              <div className="mr-auto text-blue-600 font-semibold">
                المحددة: {selectedPages.length} من {filteredPages.length}
              </div>
            </div>
          )}

          {/* الصف الثالث: أزرار الإجراءات */}
          <div className="flex gap-2">
            <Button 
              onClick={handleMergeSelected}
              disabled={selectedPages.length === 0}
              data-testid="merge-selected-btn"
            >
              <Package size={16} className="ml-2" />
              تجميع المحددة ({selectedPages.length})
            </Button>
            <Button 
              variant="outline"
              onClick={handleCreateIndividual}
              disabled={selectedPages.length === 0}
              data-testid="create-individual-btn"
            >
              <FileCheck size={16} className="ml-2" />
              إنشاء منفصل للمحددة
            </Button>
            <Button 
              variant="outline"
              onClick={handleMergeAll}
              data-testid="merge-all-btn"
            >
              <Files size={16} className="ml-2" />
              تجميع الكل
            </Button>
          </div>
        </div>
      </div>

      {/* الجدول */}
      {filteredPages.length === 0 ? (
        <div className="card text-center py-12">
          <FileText size={64} className="mx-auto mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold mb-2">لا توجد نتائج</h3>
          <p className="text-gray-500">لا توجد صفحات تطابق معايير البحث</p>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-right w-12">
                  <Checkbox
                    checked={selectedPages.length === filteredPages.length && filteredPages.length > 0}
                    onCheckedChange={handleSelectAll}
                    data-testid="select-all-checkbox"
                  />
                </TableHead>
                <TableHead className="text-right">الملف الأب</TableHead>
                <TableHead className="text-right">رقم الصفحة</TableHead>
                <TableHead className="text-right w-32">صورة ROI</TableHead>
                <TableHead className="text-right">الكود</TableHead>
                <TableHead className="text-right">الثقة</TableHead>
                <TableHead className="text-right">الاسم (nom)</TableHead>
                <TableHead className="text-right">الملف النهائي</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPages.map((page) => (
                <TableRow key={page.id} data-testid={`page-row-${page.id}`}>
                  <TableCell>
                    <Checkbox
                      checked={selectedPages.includes(page.id)}
                      onCheckedChange={() => handleSelectPage(page.id)}
                      data-testid={`checkbox-${page.id}`}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{page.parentFile}</TableCell>
                  <TableCell>{page.pageNumber}</TableCell>
                  <TableCell>
                    <div className="w-24 h-24 bg-gray-100 rounded border overflow-hidden">
                      {page.thumbnail ? (
                        <img
                          src={`${API}/thumbnail/${page.thumbnail.split('/').pop()}`}
                          alt="ROI"
                          className="w-full h-full object-contain"
                          onError={(e) => e.target.style.display = 'none'}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                          <FileText size={32} />
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {editingCell === `${page.id}-code` ? (
                      <Input
                        value={page.code || ''}
                        onChange={(e) => handleEditCell(page.id, 'code', e.target.value)}
                        onBlur={() => setEditingCell(null)}
                        autoFocus
                        className="w-24"
                      />
                    ) : (
                      <div
                        className="font-mono font-bold text-blue-600 cursor-pointer hover:bg-blue-50 p-1 rounded"
                        onClick={() => setEditingCell(`${page.id}-code`)}
                        data-testid={`code-cell-${page.id}`}
                      >
                        {page.code || '-'}
                        {page.originalCode !== page.code && (
                          <span className="text-xs text-orange-600 block">من: {page.originalCode}</span>
                        )}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>{getConfidenceBadge(page.confidence, page.confidenceLevel)}</TableCell>
                  <TableCell>
                    {editingCell === `${page.id}-nom` ? (
                      <Input
                        value={page.nom || ''}
                        onChange={(e) => handleEditCell(page.id, 'nom', e.target.value)}
                        onBlur={() => setEditingCell(null)}
                        autoFocus
                        className="w-32"
                      />
                    ) : (
                      <div
                        className="cursor-pointer hover:bg-blue-50 p-1 rounded"
                        onClick={() => setEditingCell(`${page.id}-nom`)}
                        data-testid={`nom-cell-${page.id}`}
                      >
                        {page.nom || '-'}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-sm">
                    {page.filename}
                    <div className="text-xs text-gray-500">{page.pageCount} صفحات</div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
};

export default ResultsPage;