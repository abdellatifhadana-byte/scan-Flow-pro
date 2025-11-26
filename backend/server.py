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
        "nom": request.nom,
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
        all_codes = {}
        
        for idx, file_id in enumerate(request.file_ids):
            file_doc = await db.files.find_one({"file_id": file_id})
            if not file_doc or not file_doc.get("config"):
                continue
            
            progress = (idx / len(request.file_ids)) * 100
            await db.analyses.update_one(
                {"analysis_id": analysis_id},
                {"$set": {"progress": progress}}
            )
            
            config = file_doc["config"]
            file_path = file_doc["file_path"]
            nom = config.get("nom", "")
            
            codes_data = ocr_engine.process_pdf(
                file_path=file_path,
                config=config,
                nom=nom
            )
            
            for code, pages in codes_data.items():
                if code not in all_codes:
                    all_codes[code] = []
                all_codes[code].extend(pages)
        
        results = []
        if request.merge_enabled:
            results = smart_merge.merge_by_code(all_codes)
        else:
            for code, pages in all_codes.items():
                for page_data in pages:
                    nom = page_data.get("nom", "")
                    output_path = RESULTS_DIR / "codes" / code / f"P{code}-{nom}.pdf"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    pdf_processor.save_page_as_pdf(
                        page_data["source_path"],
                        page_data["page_num"],
                        str(output_path)
                    )
                    
                    results.append({
                        "code": code,
                        "filename": output_path.name,
                        "file_path": str(output_path),
                        "page_count": 1
                    })
        
        await db.analyses.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": "completed",
                    "progress": 100,
                    "results": results,
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