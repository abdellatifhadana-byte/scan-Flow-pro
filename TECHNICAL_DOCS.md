# 🔧 Technical Documentation - ScanFlow Pro

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Upload  │→ │   ROI    │→ │ Analysis │→ │Results │ │
│  │   Page   │  │  Editor  │  │   Page   │  │  Page  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST API
                         ↓
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │   API    │  │   OCR    │  │   PDF    │  │ Smart  │ │
│  │  Router  │→ │  Engine  │→ │Processor │→ │ Merge  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ Motor (Async)
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   MongoDB Database                      │
│     ┌─────────┐  ┌──────────┐  ┌──────────┐           │
│     │  files  │  │ analyses │  │ keywords │           │
│     └─────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────┘
```

## Backend Architecture

### 1. FastAPI Application (server.py)

#### Endpoints Structure

```python
/api/
├── GET  /                          # Health check
├── POST /upload                    # Upload PDF file
├── GET  /files                     # List all files
├── DELETE /files/{file_id}         # Delete file
├── GET  /files/{file_id}/preview/{page_num}  # Page preview
├── POST /files/{file_id}/config    # Save ROI config
├── GET  /files/{file_id}/config    # Get ROI config
├── POST /analyze                   # Start analysis
├── GET  /analysis/{analysis_id}    # Get analysis status
├── GET  /results/{analysis_id}     # Get results
├── GET  /download/{code}/{filename}# Download result
├── GET  /keywords                  # Get keywords list
└── POST /keywords                  # Add keyword
```

#### Data Models

```python
class ROIData(BaseModel):
    x: float           # 0.0 - 1.0
    y: float           # 0.0 - 1.0
    width: float       # 0.0 - 1.0
    height: float      # 0.0 - 1.0

class FileConfig(BaseModel):
    file_id: str
    keyword: str
    code_roi: Optional[ROIData]
    keyword_roi: Optional[ROIData]
    rotation: int                  # 0, 90, 180, 270
    pages_per_code: int            # Number of pages per code
    auto_detect: bool              # Use auto-detection

class AnalysisRequest(BaseModel):
    file_ids: List[str]
    nom: str                       # Name for output files
    merge_enabled: bool            # Enable smart merge
```

### 2. OCR Engine (ocr_engine.py)

#### Image Processing Pipeline

```
Raw PDF Page
    ↓
Convert to Image (2x resolution)
    ↓
Apply Rotation (if needed)
    ↓
Extract ROI (if specified)
    ↓
Preprocessing:
├── Convert to Grayscale
├── Denoise (fastNlMeansDenoising)
├── CLAHE (Contrast Limited Adaptive Histogram Equalization)
└── Threshold (Binary + Otsu)
    ↓
OCR (Tesseract)
    ↓
Text Extraction
    ↓
Code Extraction (Regex)
```

#### Key Methods

```python
class OCREngine:
    def __init__(self, use_easyocr=False):
        # Initialize with Tesseract only (memory efficient)
        # EasyOCR optional for higher accuracy
        
    def preprocess_image(image):
        # Apply image enhancement
        # Returns: preprocessed binary image
        
    def extract_roi(image, roi):
        # Extract region of interest
        # ROI uses normalized coordinates (0-1)
        
    def ocr_tesseract(image):
        # Perform OCR using Tesseract
        # Supports: Arabic, French, English
        
    def extract_code_from_text(text, keyword):
        # Extract code after keyword
        # Pattern: keyword + 4-8 digits
        
    def process_page(pdf_path, page_num, config):
        # Process single page
        # Returns: extracted code or None
        
    def process_pdf(file_path, config, nom):
        # Process entire PDF
        # Returns: dict of codes and pages
```

#### OCR Configuration

```python
# Tesseract Configuration
tesseract_langs = 'ara+fra+eng'
psm = 6  # Assume uniform block of text

# Image Resolution
matrix = fitz.Matrix(2, 2)  # 2x zoom for higher quality

# CLAHE Parameters
clipLimit = 2.0
tileGridSize = (8, 8)
```

### 3. PDF Processor (pdf_processor.py)

```python
class PDFProcessor:
    def get_page_count(pdf_path):
        # Get total page count
        
    def get_page_image(pdf_path, page_num, zoom=2.0):
        # Convert page to image
        # Returns: temporary image path
        
    def save_page_as_pdf(source_pdf, page_num, output_path):
        # Extract single page as PDF
        
    def merge_pdfs(pdf_list, output_path):
        # Merge multiple pages into one PDF
        # Input: [{'source_path': ..., 'page_num': ...}]
```

### 4. Smart Merge (smart_merge.py)

```python
class SmartMerge:
    def merge_by_code(codes_data, nom):
        # Group pages by code
        # Sort pages chronologically
        # Merge into single PDF per code
        # Save with naming: P{code}-{nom}.pdf
        
        # Returns: list of results with:
        # - code
        # - page_count
        # - filename
        # - file_path
```

## Frontend Architecture

### 1. Component Structure

```
App.js
├── UploadPage/
│   ├── Upload Zone (Drag & Drop)
│   ├── File List
│   │   └── File Item
│   │       ├── Info Display
│   │       └── Action Buttons
│   └── Analysis Trigger
│
├── ROIEditor/
│   ├── Canvas Display
│   │   └── Interactive Drawing
│   ├── Controls Panel
│   │   ├── Zoom Controls
│   │   ├── Rotation
│   │   ├── ROI Drawing Buttons
│   │   └── Page Navigation
│   └── Configuration Panel
│       ├── Keyword Selector
│       ├── Pages Per Code
│       └── Save Button
│
├── AnalysisPage/
│   ├── Progress Bar
│   ├── Status Display
│   └── Event Logs
│
└── ResultsPage/
    ├── Results Table
    │   └── Result Row
    │       ├── Code Display
    │       ├── Info
    │       └── Action Buttons
    └── Preview Dialog
```

### 2. State Management

```javascript
// UploadPage State
{
  files: [],              // Uploaded files
  nom: '',               // Output name
  uploading: false,      // Upload status
  dragOver: false        // Drag state
}

// ROIEditor State
{
  file: {},              // Current file
  pageImage: null,       // Current page image
  currentPage: 0,        // Page number
  zoom: 1,               // Zoom level
  rotation: 0,           // Rotation angle
  keyword: '',           // Selected keyword
  codeROI: null,         // Code region
  keywordROI: null,      // Keyword region
  drawing: null,         // Drawing mode
  startPos: null         // Drawing start
}

// AnalysisPage State
{
  analysis: {},          // Analysis data
  logs: []               // Event logs
}

// ResultsPage State
{
  results: [],           // Analysis results
  loading: true,         // Loading state
  previewFile: null      // Preview modal
}
```

### 3. API Integration

```javascript
const API = `${BACKEND_URL}/api`;

// Upload
POST `${API}/upload`
FormData: { file: File }

// Get Files
GET `${API}/files`

// Delete File
DELETE `${API}/files/${fileId}`

// Get Page Preview
GET `${API}/files/${fileId}/preview/${pageNum}`
Response: Image Blob

// Save Config
POST `${API}/files/${fileId}/config`
Body: FileConfig

// Start Analysis
POST `${API}/analyze`
Body: { file_ids, nom, merge_enabled }

// Get Analysis Status
GET `${API}/analysis/${analysisId}`
Polling: Every 2 seconds

// Get Results
GET `${API}/results/${analysisId}`

// Download Result
GET `${API}/download/${code}/${filename}`
```

## Database Schema

### Collections

#### 1. files
```javascript
{
  file_id: "uuid",
  filename: "document.pdf",
  file_path: "/app/backend/uploads/uuid.pdf",
  page_count: 50,
  size: 1024000,
  uploaded_at: "2025-11-26T12:00:00Z",
  config: {
    file_id: "uuid",
    keyword: "رقم",
    code_roi: { x: 0.1, y: 0.2, width: 0.3, height: 0.1 },
    keyword_roi: { x: 0.05, y: 0.15, width: 0.2, height: 0.05 },
    rotation: 0,
    pages_per_code: 3,
    auto_detect: false
  }
}
```

#### 2. analyses
```javascript
{
  analysis_id: "uuid",
  file_ids: ["uuid1", "uuid2"],
  nom: "PV-AQUIESSEMENT",
  merge_enabled: true,
  status: "completed",  // processing, completed, failed
  progress: 100,
  started_at: "2025-11-26T12:05:00Z",
  completed_at: "2025-11-26T12:15:00Z",
  results: [
    {
      code: "19092",
      page_count: 3,
      filename: "P19092-PV-AQUIESSEMENT.pdf",
      file_path: "/app/backend/results/codes/19092/..."
    }
  ],
  error: null  // Error message if failed
}
```

#### 3. keywords
```javascript
{
  keyword: "رقم"
}
```

## Performance Optimization

### 1. Memory Management

```python
# Use Tesseract only (default)
ocr_engine = OCREngine(use_easyocr=False)

# EasyOCR uses ~1.5GB RAM per reader
# Disable to save memory on large files
```

### 2. Background Processing

```python
# Async processing with BackgroundTasks
@api_router.post("/analyze")
async def start_analysis(request, background_tasks):
    # Immediate response
    background_tasks.add_task(process_analysis, ...)
    return {"analysis_id": "..."}
```

### 3. Image Optimization

```python
# Use appropriate zoom level
matrix = fitz.Matrix(2, 2)  # 2x is optimal

# Don't store images, process directly
# Use temporary files for previews
```

### 4. Database Queries

```python
# Use projections to exclude _id
await db.files.find({}, {"_id": 0}).to_list(1000)

# Limit result sets
.to_list(1000)  # Max 1000 documents
```

## Error Handling

### Backend

```python
try:
    # Operation
    pass
except Exception as e:
    logging.error(f"Error: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))
```

### Frontend

```javascript
try {
  // API call
} catch (error) {
  toast.error('خطأ في العملية');
  console.error(error);
}
```

## Testing

### Backend Tests

```bash
# Test API endpoint
curl -X GET http://localhost:8001/api/

# Test file upload
curl -X POST http://localhost:8001/api/upload \
  -F "file=@test.pdf"

# Test OCR
python -c "from ocr_engine import OCREngine; \
  engine = OCREngine(); \
  print(engine.ocr_tesseract(image))"
```

### Frontend Tests

```bash
# Check if page loads
curl http://localhost:3000

# Check build
cd /app/frontend
yarn build
```

## Deployment

### Requirements

```
Server:
- CPU: 2+ cores
- RAM: 4GB+ (8GB recommended)
- Storage: 20GB+

Software:
- Ubuntu 20.04+
- Python 3.11+
- Node.js 20+
- MongoDB 7.0+
- Tesseract OCR
```

### Environment Variables

```bash
# Backend
MONGO_URL="mongodb://localhost:27017"
DB_NAME="scanflow_pro"
CORS_ORIGINS="*"

# Frontend
REACT_APP_BACKEND_URL="https://your-domain.com"
```

### Supervisor Configuration

```ini
[program:backend]
command=uvicorn server:app --host 0.0.0.0 --port 8001
directory=/app/backend
autostart=true
autorestart=true

[program:frontend]
command=yarn start
directory=/app/frontend
autostart=true
autorestart=true
```

## Security Considerations

### File Validation

```python
# Only allow PDF files
if not file.filename.endswith('.pdf'):
    raise HTTPException(400, "Only PDF files allowed")
```

### CORS Configuration

```python
# Configure allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### Input Sanitization

```python
# Use Pydantic for validation
class FileConfig(BaseModel):
    keyword: str  # Automatically validated
    pages_per_code: int  # Type checked
```

## Monitoring & Logging

### Backend Logs

```bash
# Supervisor logs
/var/log/supervisor/backend.err.log
/var/log/supervisor/backend.out.log

# Application logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Frontend Logs

```javascript
// Console logging
console.log('Action:', data);
console.error('Error:', error);

// Toast notifications
toast.success('Success message');
toast.error('Error message');
```

## Future Enhancements

### Potential Features

1. **Batch Processing**
   - Process multiple analyses simultaneously
   - Queue system for large workloads

2. **Advanced OCR**
   - Custom training for specific document types
   - Handwriting recognition

3. **Export Options**
   - Excel/CSV export
   - JSON/XML export
   - Cloud storage integration

4. **User Management**
   - Multi-user support
   - Role-based access
   - Audit logs

5. **Analytics**
   - Processing statistics
   - Success rates
   - Performance metrics

---

**Version**: 1.0.0
**Last Updated**: November 2025
**Documentation**: Complete
