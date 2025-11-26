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
            
            progress = (idx / len(request.file_ids)) * 50
            await db.analyses.update_one(
                {"analysis_id": analysis_id},
                {"$set": {"progress": progress, "status": "extracting"}}
            )
            
            config = file_doc["config"]
            file_path = file_doc["file_path"]
            filename = file_doc["filename"]
            nom = config.get("nom", "")
            
            pages_data = ocr_engine.process_pdf(
                file_path=file_path,
                config=config,
                nom=nom,
                file_id=file_id
            )
            
            # إضافة اسم الملف
            for page in pages_data:
                page['source_filename'] = filename
            
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