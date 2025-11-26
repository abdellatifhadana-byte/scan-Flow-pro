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
import { FileText, Download, ArrowRight, CheckCircle2, AlertCircle, XCircle, Search, Package, Files, Sparkles } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ResultsPage = () => {
  const { analysisId } = useParams();
  const navigate = useNavigate();
  const [allPages, setAllPages] = useState([]);
  const [filteredPages, setFilteredPages] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [mergeNom, setMergeNom] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [editingCell, setEditingCell] = useState(null);
  const [savingChanges, setSavingChanges] = useState(false);

  useEffect(() => {
    loadResults();
  }, [analysisId]);

  useEffect(() => {
    filterResults();
  }, [searchTerm, filterType, selectedFiles, allPages]);

  const loadResults = async () => {
    try {
      const response = await axios.get(`${API}/results/${analysisId}`);
      const resultsData = response.data.results || [];
      
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

    if (searchTerm) {
      filtered = filtered.filter(page => {
        const searchLower = searchTerm.toLowerCase();
        return (
          page.code?.toString().includes(searchLower) ||
          page.parentFile?.toLowerCase().includes(searchLower) ||
          page.filename?.toLowerCase().includes(searchLower) ||
          page.nom?.toLowerCase().includes(searchLower)
        );
      });
    }

    // فقط اعرض الصفحات من الملفات المحددة (إذا كانت هناك ملفات محددة)
    if (selectedFiles.length > 0) {
      filtered = filtered.filter(page => selectedFiles.includes(page.parentFile));
    }
    // إذا لم يتم تحديد أي ملف، اعرض كل الصفحات
    else {
      filtered = allPages;
    }

    if (filterType !== 'all') {
      filtered = filtered.filter(page => {
        if (filterType === 'high') return page.confidenceLevel === 'high';
        if (filterType === 'medium') return page.confidenceLevel === 'medium';
        if (filterType === 'low') return page.confidenceLevel === 'low';
        return true;
      });
    }

    setFilteredPages(filtered);
  };

  const handleEditCell = (pageId, field, value) => {
    setAllPages(prev => prev.map(page => 
      page.id === pageId 
        ? { ...page, [field]: value, isEdited: true }
        : page
    ));
  };

  const savePageChanges = async (pageId, updates) => {
    try {
      setSavingChanges(true);
      
      await axios.post(`${API}/update-page`, {
        page_id: pageId,
        code: updates.code,
        nom: updates.nom
      });
      
      toast.success('✓ تم الحفظ');
    } catch (error) {
      console.error('Save error:', error);
      toast.error('خطأ في الحفظ');
    } finally {
      setSavingChanges(false);
    }
  };

  const handleCellBlur = (pageId) => {
    const page = allPages.find(p => p.id === pageId);
    if (page && page.isEdited) {
      savePageChanges(pageId, {
        code: page.code,
        nom: page.nom
      });
    }
    setEditingCell(null);
  };

  const handleSelectFile = (filename) => {
    setSelectedFiles(prev => 
      prev.includes(filename)
        ? prev.filter(f => f !== filename)
        : [...prev, filename]
    );
  };

  const handleSelectAllFiles = () => {
    const uniqueFiles = getUniqueFiles();
    if (selectedFiles.length === uniqueFiles.length) {
      setSelectedFiles([]);
    } else {
      setSelectedFiles(uniqueFiles);
    }
  };

  const handleMergeSelected = async () => {
    if (selectedFiles.length === 0) {
      toast.error('الرجاء اختيار ملفات');
      return;
    }

    if (!mergeNom || mergeNom.trim() === '') {
      toast.error('الرجاء إدخال اسم للملفات المدمجة');
      return;
    }

    try {
      toast.info(`جاري تجميع ${selectedFiles.length} ملف...`);
      
      const response = await axios.post(`${API}/merge-by-files`, {
        analysis_id: analysisId,
        parent_files: selectedFiles,
        merge_type: 'merge',
        custom_nom: mergeNom.trim()
      });
      
      toast.success(`✓ ${response.data.message}`);
      loadResults();
    } catch (error) {
      console.error('Merge error:', error);
      toast.error('خطأ في التجميع');
    }
  };

  const handleMergeAll = async () => {
    try {
      toast.info('جاري معالجة جميع الملفات...');
      
      const response = await axios.post(`${API}/merge-all`, {
        analysis_id: analysisId,
        page_ids: [],
        merge_type: 'merge_all'
      });
      
      toast.success(`✓ تم المعالجة بنجاح!`);
      loadResults();
    } catch (error) {
      console.error('Merge all error:', error);
      toast.error('خطأ في المعالجة');
    }
  };

  const getConfidenceBadge = (confidence, level) => {
    if (level === 'high' || confidence >= 80) {
      return <Badge className="bg-emerald-500 text-white"><CheckCircle2 size={12} className="ml-1" /> {confidence?.toFixed(0)}%</Badge>;
    } else if (level === 'medium' || confidence >= 50) {
      return <Badge className="bg-amber-500 text-white"><AlertCircle size={12} className="ml-1" /> {confidence?.toFixed(0)}%</Badge>;
    } else {
      return <Badge className="bg-red-500 text-white"><XCircle size={12} className="ml-1" /> {confidence?.toFixed(0)}%</Badge>;
    }
  };

  const getUniqueFiles = () => {
    return [...new Set(allPages.map(p => p.parentFile))];
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50" dir="rtl">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            نتائج التحليل
          </h1>
          <p className="text-gray-600">إجمالي {allPages.length} صفحة من {getUniqueFiles().length} ملفات</p>
        </div>

        {/* Main Control Card */}
        <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
          {/* Search and Filter */}
          <div className="flex gap-4 items-center mb-6 flex-wrap">
            <div className="flex-1 min-w-[300px] relative">
              <Search className="absolute right-3 top-3 text-gray-400" size={20} />
              <Input
                placeholder="ابحث بالكود أو اسم الملف..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pr-10 h-11 border-2 border-gray-200 focus:border-blue-500"
              />
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-48 h-11 border-2 border-gray-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع المستويات</SelectItem>
                <SelectItem value="high">ثقة عالية</SelectItem>
                <SelectItem value="medium">ثقة متوسطة</SelectItem>
                <SelectItem value="low">ثقة منخفضة</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => navigate('/')} className="h-11">
              <ArrowRight size={16} className="ml-2" />
              العودة
            </Button>
          </div>

          {/* File Selection */}
          <div className="border-t pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <FileText className="text-blue-600" size={20} />
                اختر الملفات للعرض والمعالجة
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSelectAllFiles}
              >
                {selectedFiles.length === getUniqueFiles().length ? 'إلغاء الكل' : 'تحديد الكل'}
              </Button>
            </div>
            <div className="flex gap-3 flex-wrap">
              {getUniqueFiles().map((file, idx) => (
                <div
                  key={idx}
                  onClick={() => handleSelectFile(file)}
                  className={`cursor-pointer px-4 py-3 rounded-xl border-2 transition-all flex items-center gap-2 ${
                    selectedFiles.includes(file)
                      ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white border-transparent shadow-lg scale-105'
                      : 'bg-white border-gray-200 hover:border-blue-300 text-gray-700'
                  }`}
                >
                  <Checkbox checked={selectedFiles.includes(file)} />
                  <span className="font-medium text-sm">{file}</span>
                </div>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-3">
              {selectedFiles.length} من {getUniqueFiles().length} محدد
            </p>
          </div>

          {/* Merge Name Input */}
          {selectedFiles.length > 0 && (
            <div className="mt-6 pt-6 border-t">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                الاسم للملفات المدمجة (مطلوب):
              </label>
              <Input
                value={mergeNom}
                onChange={(e) => setMergeNom(e.target.value)}
                placeholder="مثال: AQUIESSEMENT"
                className="max-w-md h-11 border-2 border-gray-200 focus:border-blue-500 text-lg"
              />
              <p className="text-xs text-gray-500 mt-1">
                سيتم استخدام هذا الاسم في تسمية الملفات المدمجة: P{'{code}'}-PV-{mergeNom || 'الاسم'}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 mt-6 pt-6 border-t">
            <Button 
              onClick={handleMergeSelected}
              disabled={selectedFiles.length === 0 || !mergeNom}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white shadow-lg disabled:opacity-50"
            >
              <Package size={18} className="ml-2" />
              تجميع الملفات المحددة ({selectedFiles.length})
            </Button>
            <Button 
              variant="outline"
              onClick={handleMergeAll}
              className="border-2 border-purple-600 text-purple-600 hover:bg-purple-50"
            >
              <Sparkles size={18} className="ml-2" />
              معالجة جميع الملفات
            </Button>
          </div>
        </div>

        {/* Statistics */}
        {statistics && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl p-4 text-white shadow-lg">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle2 size={20} />
                <span className="text-sm opacity-90">ثقة عالية</span>
              </div>
              <p className="text-3xl font-bold">{statistics.high_confidence}</p>
            </div>
            <div className="bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl p-4 text-white shadow-lg">
              <div className="flex items-center gap-2 mb-1">
                <AlertCircle size={20} />
                <span className="text-sm opacity-90">ثقة متوسطة</span>
              </div>
              <p className="text-3xl font-bold">{statistics.medium_confidence}</p>
            </div>
            <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-4 text-white shadow-lg">
              <div className="flex items-center gap-2 mb-1">
                <XCircle size={20} />
                <span className="text-sm opacity-90">ثقة منخفضة</span>
              </div>
              <p className="text-3xl font-bold">{statistics.low_confidence}</p>
            </div>
          </div>
        )}

        {/* Results Table */}
        {filteredPages.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-xl p-12 text-center">
            <FileText size={64} className="mx-auto mb-4 text-gray-300" />
            <h3 className="text-xl font-semibold mb-2 text-gray-700">لا توجد نتائج</h3>
            <p className="text-gray-500">قم بتحديد ملفات لعرض صفحاتها</p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-gradient-to-r from-blue-50 to-purple-50">
                    <TableHead className="text-right font-bold">الملف</TableHead>
                    <TableHead className="text-right font-bold">الصفحة</TableHead>
                    <TableHead className="text-right font-bold">صورة ROI</TableHead>
                    <TableHead className="text-right font-bold">الكود</TableHead>
                    <TableHead className="text-right font-bold">الثقة</TableHead>
                    <TableHead className="text-right font-bold">الاسم</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPages.map((page) => (
                    <TableRow key={page.id} className="hover:bg-blue-50/50 transition-colors">
                      <TableCell className="font-medium text-gray-700">{page.parentFile}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono">
                          {page.pageNumber}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="w-20 h-20 bg-gray-100 rounded-lg border-2 border-gray-200 overflow-hidden">
                          {page.thumbnail ? (
                            <img
                              src={`${API}/thumbnail/${page.thumbnail.split('/').pop()}`}
                              alt="ROI"
                              className="w-full h-full object-contain"
                              onError={(e) => e.target.style.display = 'none'}
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                              <FileText size={24} />
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {editingCell === `${page.id}-code` ? (
                          <Input
                            value={page.code || ''}
                            onChange={(e) => handleEditCell(page.id, 'code', e.target.value)}
                            onBlur={() => handleCellBlur(page.id)}
                            autoFocus
                            className="w-28 font-mono font-bold text-lg"
                          />
                        ) : (
                          <div
                            className="font-mono font-bold text-xl text-blue-600 cursor-pointer hover:bg-blue-50 px-3 py-2 rounded-lg transition-colors"
                            onClick={() => setEditingCell(`${page.id}-code`)}
                          >
                            {page.code || '-'}
                            {savingChanges && page.isEdited && (
                              <span className="text-xs text-green-600 ml-2">💾</span>
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
                            onBlur={() => handleCellBlur(page.id)}
                            autoFocus
                            className="w-32"
                          />
                        ) : (
                          <div
                            className="cursor-pointer hover:bg-blue-50 px-3 py-2 rounded-lg transition-colors font-medium"
                            onClick={() => setEditingCell(`${page.id}-nom`)}
                          >
                            {page.nom || '-'}
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsPage;
