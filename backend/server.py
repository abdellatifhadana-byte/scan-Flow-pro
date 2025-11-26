from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import os
import uuid
import logging
from datetime import datetime, timezone
import shutil
import json

from ocr_engine import OCREngine
from pdf_processor import PDFProcessor
from smart_merge import SmartMerge
from code_alignment import CodeAlignment

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

UPLOADS_DIR = ROOT_DIR / "uploads"
RESULTS_DIR = ROOT_DIR / "results"
UPLOADS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
(RESULTS_DIR / "codes").mkdir(exist_ok=True)
(RESULTS_DIR / "temp").mkdir(exist_ok=True)

ocr_engine = OCREngine(use_easyocr=False)
pdf_processor = PDFProcessor()
smart_merge = SmartMerge()
code_alignment = CodeAlignment()

class ROIData(BaseModel):
    x: float
    y: float
    width: float
    height: float

class FileConfig(BaseModel):
    file_id: str
    keyword: str
    nom: str = ""
    code_roi: Optional[ROIData] = None
    keyword_roi: Optional[ROIData] = None
    rotation: int = 0
    pages_per_code: int = 1
    auto_detect: bool = False

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    page_count: int
    size: int

class AnalysisRequest(BaseModel):
    file_ids: List[str]
    merge_enabled: bool = True

class AnalysisStatus(BaseModel):
    file_id: str
    status: str
    progress: float
    message: str
    codes_found: List[str] = []

class CodeResult(BaseModel):
    code: str
    page_count: int
    filename: str
    file_path: str

@api_router.get("/")
async def root():
    return {"message": "ScanFlow Pro API", "version": "1.0.0"}

@api_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        file_id = str(uuid.uuid4())
        file_path = UPLOADS_DIR / f"{file_id}.pdf"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        page_count = pdf_processor.get_page_count(str(file_path))
        
        file_doc = {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "page_count": page_count,
            "size": len(content),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "config": None
        }
        
        await db.files.insert_one(file_doc)
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            page_count=page_count,
            size=len(content)
        )
    
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/files", response_model=List[Dict[str, Any]])
async def get_files():
    files = await db.files.find({}, {"_id": 0}).to_list(1000)
    return files

@api_router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    file_doc = await db.files.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = Path(file_doc["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    await db.files.delete_one({"file_id": file_id})
    return {"message": "File deleted successfully"}

@api_router.get("/files/{file_id}/preview/{page_num}")
async def get_page_preview(file_id: str, page_num: int):
    file_doc = await db.files.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_doc["file_path"]
    image_path = pdf_processor.get_page_image(file_path, page_num)
    
    return FileResponse(image_path, media_type="image/png")

@api_router.post("/files/{file_id}/config")
async def save_file_config(file_id: str, config: FileConfig):
    file_doc = await db.files.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    config_dict = config.model_dump()
    await db.files.update_one(
        {"file_id": file_id},
        {"$set": {"config": config_dict}}
    )
    
    return {"message": "Configuration saved successfully"}

@api_router.get("/files/{file_id}/config")
async def get_file_config(file_id: str):
    file_doc = await db.files.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"config": file_doc.get("config")}

@api_router.post("/analyze")
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    analysis_id = str(uuid.uuid4())
    
    analysis_doc = {
        "analysis_id": analysis_id,
        "file_ids": request.file_ids,
        "merge_enabled": request.merge_enabled,
        "status": "processing",
        "progress": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": []
    }
    
    await db.analyses.insert_one(analysis_doc)
    
    background_tasks.add_task(process_analysis, analysis_id, request)
    
    return {"analysis_id": analysis_id, "message": "Analysis started"}

async def process_analysis(analysis_id: str, request: AnalysisRequest):
    try:
        all_pages_data = []
        
        # المرحلة 1: استخراج كل الأكواد من كل الملفات
        for idx, file_id in enumerate(request.file_ids):
            file_doc = await db.files.find_one({"file_id": file_id})
            if not file_doc or not file_doc.get("config"):
                continue
            
            config = file_doc["config"]
            file_path = file_doc["file_path"]
            filename = file_doc["filename"]
            nom = config.get("nom", "")
            
            # تحديث الحالة مع اسم الملف
            progress = (idx / len(request.file_ids)) * 50
            await db.analyses.update_one(
                {"analysis_id": analysis_id},
                {"$set": {
                    "progress": progress, 
                    "status": "extracting",
                    "current_file": filename,
                    "current_page": 0
                }}
            )
            
            pages_data = ocr_engine.process_pdf(
                file_path=file_path,
                config=config,
                nom=nom,
                file_id=file_id
            )
            
            # إضافة اسم الملف وتحديث النتائج فوراً
            for page in pages_data:
                page['source_filename'] = filename
                
                # تحديث قاعدة البيانات مع كل صفحة معالجة
                await db.analyses.update_one(
                    {"analysis_id": analysis_id},
                    {
                        "$set": {
                            "current_page": page.get('page_num', 0) + 1,
                            "current_code": page.get('code', '')
                        },
                        "$push": {"results": page}
                    }
                )
            
            all_pages_data.extend(pages_data)
        
        # المرحلة 2: محاذاة الأكواد
        await db.analyses.update_one(
            {"analysis_id": analysis_id},
            {"$set": {"progress": 60, "status": "aligning"}}
        )
        
        aligned_pages = code_alignment.align_codes(all_pages_data)
        
        # المرحلة 3: تجميع حسب الكود
        await db.analyses.update_one(
            {"analysis_id": analysis_id},
            {"$set": {"progress": 75, "status": "grouping"}}
        )
        
        grouped_by_code = code_alignment.group_by_code(aligned_pages)
        
        # المرحلة 4: إنشاء الملفات
        await db.analyses.update_one(
            {"analysis_id": analysis_id},
            {"$set": {"progress": 85, "status": "creating_files"}}
        )
        
        results = []
        
        for code, pages in grouped_by_code.items():
            code_dir = RESULTS_DIR / "codes" / code
            code_dir.mkdir(parents=True, exist_ok=True)
            
            for page in pages:
                nom = page.get("nom", "")
                output_filename = f"P{code}-{nom}.pdf"
                output_path = code_dir / output_filename
                
                # إنشاء PDF يحتوي على الصفحة الرئيسية والصفحات التابعة
                pages_to_include = [page['page_num']] + page.get('dependent_pages', [])
                
                if len(pages_to_include) == 1:
                    # صفحة واحدة
                    pdf_processor.save_page_as_pdf(
                        page["source_path"],
                        page["page_num"],
                        str(output_path)
                    )
                else:
                    # صفحات متعددة
                    pages_info = [
                        {"source_path": page["source_path"], "page_num": p}
                        for p in pages_to_include
                    ]
                    pdf_processor.merge_pdfs(pages_info, str(output_path))
                
                results.append({
                    "code": code,
                    "aligned_code": page['aligned_code'],
                    "original_code": page.get('original_code'),
                    "confidence": page['aligned_confidence'],
                    "confidence_level": page.get('confidence_level'),
                    "filename": output_filename,
                    "file_path": str(output_path),
                    "page_count": len(pages_to_include),
                    "source_filename": page.get('source_filename', ''),
                    "source_page": page['page_num'],
                    "nom": nom,
                    "thumbnail": page.get('thumbnail', ''),
                    "file_id": page.get('file_id', '')
                })
        
        # حساب الإحصائيات
        stats = code_alignment.generate_statistics(aligned_pages)
        
        await db.analyses.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": "completed",
                    "progress": 100,
                    "results": results,
                    "statistics": stats,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
    
    except Exception as e:
        logging.error(f"Analysis error: {str(e)}")
        await db.analyses.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )

@api_router.get("/analysis/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    analysis = await db.analyses.find_one({"analysis_id": analysis_id}, {"_id": 0})
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@api_router.get("/results/{analysis_id}")
async def get_results(analysis_id: str):
    analysis = await db.analyses.find_one({"analysis_id": analysis_id}, {"_id": 0})
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {"results": analysis.get("results", [])}

@api_router.get("/download/{code}/{filename}")
async def download_result(code: str, filename: str):
    file_path = RESULTS_DIR / "codes" / code / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, media_type="application/pdf", filename=filename)

@api_router.get("/keywords")
async def get_keywords():
    keywords = await db.keywords.find({}, {"_id": 0}).to_list(1000)
    return [k["keyword"] for k in keywords]

@api_router.post("/keywords")
async def add_keyword(keyword: str):
    existing = await db.keywords.find_one({"keyword": keyword})
    if not existing:
        await db.keywords.insert_one({"keyword": keyword})
    return {"message": "Keyword added"}

@api_router.get("/thumbnail/{thumbnail_id}")
async def get_thumbnail(thumbnail_id: str):
    """الحصول على الصورة المصغرة لمنطقة ROI"""
    from pathlib import Path
    thumbnail_path = Path(f"/tmp/{thumbnail_id}")
    if thumbnail_path.exists():
        return FileResponse(thumbnail_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Thumbnail not found")

class PageUpdate(BaseModel):
    page_id: str
    code: Optional[str] = None
    nom: Optional[str] = None

class MergeRequest(BaseModel):
    analysis_id: str
    page_ids: List[str]
    merge_type: str  # "merge" or "individual" or "merge_all"

class MergeByFilesRequest(BaseModel):
    analysis_id: str
    parent_files: List[str]  # قائمة بأسماء الملفات الأب
    merge_type: str  # "merge" or "individual"
    custom_nom: Optional[str] = None  # الاسم المخصص للملفات المدمجة

@api_router.post("/update-page")
async def update_page_data(update: PageUpdate):
    """تحديث بيانات صفحة وحفظها في قاعدة البيانات"""
    try:
        # استخراج file_id و page_num من page_id
        # Format: {file_id}-{page_num}
        parts = update.page_id.rsplit('-', 1)
        if len(parts) == 2:
            file_id = parts[0]
            try:
                page_num = int(parts[1])
            except ValueError:
                # إذا فشل التحويل، نعتبر page_id كامل هو file_id
                file_id = update.page_id
                page_num = 0
            
            # البحث عن التحليل الذي يحتوي على هذا الملف
            analyses = await db.analyses.find({
                "results": {
                    "$elemMatch": {
                        "file_id": file_id,
                        "source_page": page_num
                    }
                }
            }).to_list(10)
            
            # تحديث كل التحليلات التي تحتوي على هذه الصفحة
            for analysis in analyses:
                results = analysis.get("results", [])
                updated = False
                
                for i, result in enumerate(results):
                    if result.get("file_id") == file_id and result.get("source_page") == page_num:
                        if update.code is not None:
                            results[i]["aligned_code"] = update.code
                            results[i]["code"] = update.code
                            updated = True
                        if update.nom is not None:
                            results[i]["nom"] = update.nom
                            # تحديث اسم الملف أيضاً
                            code = results[i].get("aligned_code") or results[i].get("code")
                            results[i]["filename"] = f"P{code}-{update.nom}.pdf"
                            updated = True
                
                if updated:
                    await db.analyses.update_one(
                        {"analysis_id": analysis["analysis_id"]},
                        {"$set": {"results": results}}
                    )
        
        return {"message": "Page updated successfully", "page_id": update.page_id}
    except Exception as e:
        logger.error(f"Update page error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/merge-selected")
async def merge_selected_pages(request: MergeRequest):
    """تجميع الصفحات المحددة"""
    try:
        analysis = await db.analyses.find_one({"analysis_id": request.analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        results = analysis.get("results", [])
        selected_results = [r for r in results if r.get("file_id") in request.page_ids or 
                           f"{r.get('file_id')}-{r.get('source_page')}" in request.page_ids]
        
        if not selected_results:
            raise HTTPException(status_code=400, detail="No pages selected")
        
        # تجميع حسب الكود
        grouped_by_code = {}
        for result in selected_results:
            code = result.get('aligned_code') or result.get('code')
            if code not in grouped_by_code:
                grouped_by_code[code] = []
            grouped_by_code[code].append(result)
        
        merged_files = []
        for code, pages in grouped_by_code.items():
            # ترتيب الصفحات حسب الملف والصفحة
            pages.sort(key=lambda x: (x.get('source_filename', ''), x.get('source_page', 0)))
            
            # تجميع noms من كل الصفحات
            noms = list(set([p.get('nom', '') for p in pages if p.get('nom')]))
            nom_str = '-'.join(noms) if noms else 'merged'
            
            output_filename = f"P{code}-PV-{nom_str}.pdf"
            output_dir = RESULTS_DIR / "codes" / code
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename
            
            # دمج كل الصفحات
            pages_to_merge = []
            for page in pages:
                pages_to_merge.append({
                    'source_path': page['file_path'] if Path(page['file_path']).exists() else page.get('source_path', ''),
                    'page_num': 0 if Path(page['file_path']).exists() else page.get('source_page', 0)
                })
            
            pdf_processor.merge_pdfs(pages_to_merge, str(output_path))
            
            merged_files.append({
                'code': code,
                'filename': output_filename,
                'path': str(output_path),
                'page_count': len(pages)
            })
        
        return {
            "message": "Merged successfully",
            "files": merged_files
        }
    
    except Exception as e:
        logger.error(f"Merge error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/create-individual")
async def create_individual_files(request: MergeRequest):
    """إنشاء ملفات منفصلة للصفحات المحددة"""
    try:
        analysis = await db.analyses.find_one({"analysis_id": request.analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        results = analysis.get("results", [])
        selected_results = [r for r in results if r.get("file_id") in request.page_ids or 
                           f"{r.get('file_id')}-{r.get('source_page')}" in request.page_ids]
        
        created_files = []
        for result in selected_results:
            code = result.get('aligned_code') or result.get('code')
            nom = result.get('nom', 'page')
            
            output_filename = f"P{code}-{nom}.pdf"
            output_dir = RESULTS_DIR / "codes" / code
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename
            
            # نسخ الملف أو إنشاؤه
            source_path = result.get('file_path')
            if source_path and Path(source_path).exists():
                import shutil
                shutil.copy(source_path, output_path)
            
            created_files.append({
                'code': code,
                'filename': output_filename,
                'path': str(output_path)
            })
        
        return {
            "message": "Individual files created successfully",
            "files": created_files
        }
    
    except Exception as e:
        logger.error(f"Create individual error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class MergeAllSmartRequest(BaseModel):
    analysis_id: str
    selected_files: List[str]  # الملفات المحددة للتجميع
    custom_nom: Optional[str] = None  # الاسم المخصص

@api_router.post("/merge-all")
async def merge_all_by_code(request: MergeRequest):
    """تجميع جميع الملفات حسب الكود"""
    try:
        analysis = await db.analyses.find_one({"analysis_id": request.analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        results = analysis.get("results", [])
        
        # تجميع حسب الكود
        grouped_by_code = {}
        for result in results:
            code = result.get('aligned_code') or result.get('code')
            if code:
                if code not in grouped_by_code:
                    grouped_by_code[code] = []
                grouped_by_code[code].append(result)
        
        merged_files = []
        for code, pages in grouped_by_code.items():
            # ترتيب
            pages.sort(key=lambda x: (x.get('source_filename', ''), x.get('source_page', 0)))
            
            # جمع noms
            noms = list(set([p.get('nom', '') for p in pages if p.get('nom')]))
            nom_str = '-'.join(noms) if noms else 'all'
            
            output_filename = f"P{code}-PV-{nom_str}.pdf"
            output_dir = RESULTS_DIR / "codes" / f"P{code}"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename
            
            # دمج
            pages_to_merge = []
            for page in pages:
                pages_to_merge.append({
                    'source_path': page['file_path'] if Path(page['file_path']).exists() else page.get('source_path', ''),
                    'page_num': 0 if Path(page['file_path']).exists() else page.get('source_page', 0)
                })
            
            pdf_processor.merge_pdfs(pages_to_merge, str(output_path))
            
            merged_files.append({
                'code': code,
                'filename': output_filename,
                'path': str(output_path),
                'page_count': len(pages)
            })
        
        return {
            "message": "All files merged successfully",
            "files": merged_files,
            "total_codes": len(merged_files)
        }
    
    except Exception as e:
        logger.error(f"Merge all error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/merge-all-smart")
async def merge_all_smart(request: MergeAllSmartRequest):
    """معالجة ذكية: تجميع الملفات المحددة، وإنشاء فردي للباقي"""
    try:
        analysis = await db.analyses.find_one({"analysis_id": request.analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        results = analysis.get("results", [])
        
        # الحصول على معلومات الملفات - استخدام file_id من النتائج
        all_file_ids = set()
        for r in results:
            if r.get('file_id'):
                all_file_ids.add(r.get('file_id'))
        
        files_map = {}
        if all_file_ids:
            files = await db.files.find({"file_id": {"$in": list(all_file_ids)}}, {"_id": 0}).to_list(1000)
            for f in files:
                files_map[f['file_id']] = f['file_path']
        
        # تقسيم النتائج حسب الملفات المحددة
        selected_results = [r for r in results if r.get('source_filename') in request.selected_files]
        unselected_results = [r for r in results if r.get('source_filename') not in request.selected_files]
        
        created_files = []
        
        # 1. تجميع الملفات المحددة حسب الكود
        if selected_results and request.selected_files:
            grouped_by_code = {}
            for result in selected_results:
                code = result.get('aligned_code') or result.get('code')
                if code:
                    if code not in grouped_by_code:
                        grouped_by_code[code] = []
                    grouped_by_code[code].append(result)
            
            for code, pages in grouped_by_code.items():
                pages.sort(key=lambda x: (x.get('source_filename', ''), x.get('source_page', 0)))
                
                nom_str = request.custom_nom if request.custom_nom else 'merged'
                output_filename = f"P{code}-PV-{nom_str}.pdf"
                output_dir = RESULTS_DIR / "codes" / f"P{code}"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / output_filename
                
                pages_to_merge = []
                for page in pages:
                    file_id = page.get('file_id')
                    if file_id and file_id in files_map:
                        pages_to_merge.append({
                            'source_path': files_map[file_id],
                            'page_num': page.get('source_page', 0)
                        })
                
                if pages_to_merge:
                    pdf_processor.merge_pdfs(pages_to_merge, str(output_path))
                    created_files.append({
                        'code': code,
                        'filename': output_filename,
                        'path': str(output_path),
                        'type': 'merged'
                    })
        
        # 2. إنشاء ملفات فردية للملفات غير المحددة
        if unselected_results:
            for result in unselected_results:
                code = result.get('aligned_code') or result.get('code')
                nom = result.get('nom', 'page')
                
                output_filename = f"P{code}-{nom}.pdf"
                output_dir = RESULTS_DIR / "codes" / f"P{code}"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / output_filename
                
                file_id = result.get('file_id')
                if file_id and file_id in files_map:
                    pdf_processor.save_page_as_pdf(
                        files_map[file_id],
                        result.get('source_page', 0),
                        str(output_path)
                    )
                    
                    created_files.append({
                        'code': code,
                        'filename': output_filename,
                        'path': str(output_path),
                        'type': 'individual'
                    })
        
        merged_count = len([f for f in created_files if f['type'] == 'merged'])
        individual_count = len([f for f in created_files if f['type'] == 'individual'])
        
        return {
            "message": f"تم إنشاء {merged_count} ملف مدمج و {individual_count} ملف فردي",
            "files": created_files,
            "total_merged": merged_count,
            "total_individual": individual_count
        }
    
    except Exception as e:
        logger.error(f"Merge all smart error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/download-result/{code}/{filename}")
async def download_result_file(code: str, filename: str):
    """تحميل ملف نتيجة معين"""
    file_path = RESULTS_DIR / "codes" / code / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path, 
        media_type="application/pdf", 
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/download-code-zip/{code}")
async def download_code_as_zip(code: str):
    """تحميل جميع ملفات كود معين كملف مضغوط"""
    import zipfile
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    code_dir = RESULTS_DIR / "codes" / code
    if not code_dir.exists():
        raise HTTPException(status_code=404, detail="Code directory not found")
    
    # إنشاء ملف zip في الذاكرة
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in code_dir.glob("*.pdf"):
            zip_file.write(file_path, file_path.name)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=Code_{code}_files.zip"}
    )

@api_router.post("/download-selected")
async def download_selected_files(request: MergeRequest):
    """تحميل الملفات المحددة كملف مضغوط"""
    import zipfile
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    try:
        analysis = await db.analyses.find_one({"analysis_id": request.analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        results = analysis.get("results", [])
        selected_results = [r for r in results if r.get("file_id") in request.page_ids or 
                           f"{r.get('file_id')}-{r.get('source_page')}" in request.page_ids]
        
        if not selected_results:
            raise HTTPException(status_code=400, detail="No pages selected")
        
        # إنشاء ملف zip
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in selected_results:
                file_path = Path(result.get('file_path', ''))
                if file_path.exists():
                    zip_file.write(file_path, file_path.name)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=selected_files.zip"}
        )
    
    except Exception as e:
        logger.error(f"Download selected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/cleanup/old-files")
async def cleanup_old_files():
    """حذف الملفات القديمة من مجلد النتائج"""
    try:
        from datetime import datetime, timedelta
        import time
        
        deleted_count = 0
        # حذف الملفات الأقدم من 7 أيام
        cutoff_time = time.time() - (7 * 24 * 60 * 60)
        
        for code_dir in (RESULTS_DIR / "codes").iterdir():
            if code_dir.is_dir():
                for file_path in code_dir.glob("*.pdf"):
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                
                # حذف المجلد إذا كان فارغاً
                if not any(code_dir.iterdir()):
                    code_dir.rmdir()
        
        return {
            "message": f"تم حذف {deleted_count} ملف قديم",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        logger.error(f"Cleanup old files error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/cleanup/all")
async def cleanup_all_data():
    """تنظيف جميع البيانات والملفات"""
    try:
        deleted_info = {
            "uploads": 0,
            "results": 0,
            "db_files": 0,
            "db_analyses": 0
        }
        
        # حذف ملفات الرفع
        if UPLOADS_DIR.exists():
            for file_path in UPLOADS_DIR.glob("*.pdf"):
                file_path.unlink()
                deleted_info["uploads"] += 1
        
        # حذف ملفات النتائج
        if (RESULTS_DIR / "codes").exists():
            for code_dir in (RESULTS_DIR / "codes").iterdir():
                if code_dir.is_dir():
                    for file_path in code_dir.glob("*"):
                        file_path.unlink()
                        deleted_info["results"] += 1
                    code_dir.rmdir()
        
        # حذف البيانات من قاعدة البيانات
        result_files = await db.files.delete_many({})
        deleted_info["db_files"] = result_files.deleted_count
        
        result_analyses = await db.analyses.delete_many({})
        deleted_info["db_analyses"] = result_analyses.deleted_count
        
        return {
            "message": "تم تنظيف جميع البيانات بنجاح",
            "details": deleted_info
        }
    
    except Exception as e:
        logger.error(f"Cleanup all error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/system/restart")
async def restart_application():
    """إعادة تشغيل التطبيق"""
    try:
        import subprocess
        import sys
        
        # إعادة تشغيل supervisor
        subprocess.Popen(["sudo", "supervisorctl", "restart", "backend"])
        
        return {
            "message": "جاري إعادة تشغيل التطبيق...",
            "status": "restarting"
        }
    
    except Exception as e:
        logger.error(f"Restart error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/merge-by-files")
async def merge_by_parent_files(request: MergeByFilesRequest):
    """تجميع أو إنشاء ملفات فردية حسب الملفات الأب المحددة"""
    try:
        analysis = await db.analyses.find_one({"analysis_id": request.analysis_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        results = analysis.get("results", [])
        
        # تصفية النتائج لتشمل فقط الصفحات من الملفات المحددة
        filtered_results = [
            r for r in results 
            if r.get('source_filename') in request.parent_files
        ]
        
        if not filtered_results:
            raise HTTPException(status_code=400, detail="No pages found for selected files")
        
        if request.merge_type == "merge":
            # تجميع حسب الكود - ملف واحد لكل كود
            grouped_by_code = {}
            for result in filtered_results:
                code = result.get('aligned_code') or result.get('code')
                if code:
                    if code not in grouped_by_code:
                        grouped_by_code[code] = []
                    grouped_by_code[code].append(result)
            
            merged_files = []
            for code, pages in grouped_by_code.items():
                # ترتيب الصفحات: الصفحة الرئيسية أولاً، ثم التابعة
                pages.sort(key=lambda x: (
                    x.get('source_filename', ''),
                    x.get('source_page', 0)
                ))
                
                # استخدام الاسم المخصص أو جمع أسماء nom
                if request.custom_nom:
                    nom_str = request.custom_nom
                else:
                    noms = list(set([p.get('nom', '') for p in pages if p.get('nom')]))
                    nom_str = '-'.join(noms) if noms else 'merged'
                
                output_filename = f"P{code}-PV-{nom_str}.pdf"
                output_dir = RESULTS_DIR / "codes" / f"P{code}"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / output_filename
                
                # جمع كل الصفحات للدمج
                pages_to_merge = []
                for page in pages:
                    source_path = page.get('file_path', '')
                    
                    # إذا كان الملف موجوداً مسبقاً، نستخدمه
                    if source_path and Path(source_path).exists():
                        pages_to_merge.append({
                            'source_path': source_path,
                            'page_num': 0
                        })
                    else:
                        # نستخدم ملف PDF الأصلي والصفحة المحددة
                        file_doc = await db.files.find_one({"file_id": page.get('file_id')})
                        if file_doc:
                            pages_to_merge.append({
                                'source_path': file_doc['file_path'],
                                'page_num': page.get('source_page', 0)
                            })
                
                # دمج جميع الصفحات
                if pages_to_merge:
                    pdf_processor.merge_pdfs(pages_to_merge, str(output_path))
                    
                    merged_files.append({
                        'code': code,
                        'filename': output_filename,
                        'path': str(output_path),
                        'page_count': len(pages_to_merge)
                    })
            
            return {
                "message": f"تم تجميع {len(merged_files)} ملف بنجاح",
                "files": merged_files,
                "total_codes": len(merged_files)
            }
        
        elif request.merge_type == "individual":
            # إنشاء ملف منفصل لكل صفحة
            created_files = []
            
            for result in filtered_results:
                code = result.get('aligned_code') or result.get('code')
                nom = result.get('nom', 'page')
                
                output_filename = f"P{code}-{nom}.pdf"
                output_dir = RESULTS_DIR / "codes" / code
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / output_filename
                
                # إنشاء الملف
                source_path = result.get('file_path', '')
                if source_path and Path(source_path).exists():
                    # نسخ الملف الموجود
                    shutil.copy(source_path, output_path)
                else:
                    # إنشاء من PDF الأصلي
                    file_doc = await db.files.find_one({"file_id": result.get('file_id')})
                    if file_doc:
                        pdf_processor.save_page_as_pdf(
                            file_doc['file_path'],
                            result.get('source_page', 0),
                            str(output_path)
                        )
                
                created_files.append({
                    'code': code,
                    'filename': output_filename,
                    'path': str(output_path),
                    'source_file': result.get('source_filename', '')
                })
            
            return {
                "message": f"تم إنشاء {len(created_files)} ملف منفصل بنجاح",
                "files": created_files,
                "total_files": len(created_files)
            }
        
        else:
            raise HTTPException(status_code=400, detail="Invalid merge_type")
    
    except Exception as e:
        logger.error(f"Merge by files error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()