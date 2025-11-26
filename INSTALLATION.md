# 📥 دليل تحميل وتثبيت ScanFlow Pro

## كيف تحمل البرنامج لتشتغل به في حاسوبك الخاص

---

## 📋 المتطلبات الأساسية

قبل التثبيت، تأكد من توفر:

### 1. نظام التشغيل
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu 20.04+)

### 2. البرامج المطلوبة

#### أ. Python 3.11+
```bash
# تحقق من التثبيت
python --version
# أو
python3 --version
```
**تحميل:** https://www.python.org/downloads/

#### ب. Node.js 20+
```bash
# تحقق من التثبيت
node --version
npm --version
```
**تحميل:** https://nodejs.org/

#### ج. MongoDB 7.0+
```bash
# تحقق من التثبيت
mongod --version
```
**تحميل:** https://www.mongodb.com/try/download/community

#### د. Tesseract OCR
**Windows:**
- تحميل: https://github.com/UB-Mannheim/tesseract/wiki
- ثبت مع اللغات: Arabic, French, English

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra poppler-utils
```

---

## 📦 طريقة 1: تحميل من Emergent Platform

### الخطوة 1: تصدير المشروع
```bash
# في نافذة terminal داخل Emergent
cd /app
tar -czf scanflow-pro.tar.gz backend/ frontend/ README.md *.md
```

### الخطوة 2: تحميل الملف
- اضغط على "Download" في Emergent
- أو استخدم SCP لنقل الملف

---

## 📦 طريقة 2: تحميل الملفات يدوياً

### البنية المطلوبة:
```
scanflow-pro/
├── backend/
│   ├── server.py
│   ├── ocr_engine.py
│   ├── pdf_processor.py
│   ├── smart_merge.py
│   ├── code_alignment.py
│   ├── requirements.txt
│   ├── .env
│   └── uploads/ (أنشئها)
│   └── results/ (أنشئها)
│
├── frontend/
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── App.css
│       ├── index.js
│       ├── pages/
│       │   ├── UploadPage.jsx
│       │   ├── ROIEditor.jsx
│       │   ├── AnalysisPage.jsx
│       │   └── ResultsPage.jsx
│       └── components/
│
└── README.md
```

---

## 🔧 خطوات التثبيت

### 1️⃣ إعداد قاعدة البيانات

#### تشغيل MongoDB:

**Windows:**
```bash
# ابدأ MongoDB كخدمة
net start MongoDB
```

**macOS/Linux:**
```bash
# ابدأ MongoDB
sudo systemctl start mongod
# أو
mongod --dbpath /path/to/data
```

#### إنشاء قاعدة البيانات:
```bash
mongosh
> use scanflow_pro
> db.createCollection("files")
> db.createCollection("analyses")
> db.createCollection("keywords")
> exit
```

---

### 2️⃣ إعداد Backend

```bash
cd scanflow-pro/backend

# إنشاء بيئة افتراضية
python -m venv venv

# تفعيل البيئة الافتراضية
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate

# تثبيت المكتبات
pip install -r requirements.txt

# إنشاء المجلدات المطلوبة
mkdir uploads results logs
mkdir results/codes results/temp
```

#### إعداد ملف .env:
```bash
# أنشئ ملف .env
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=scanflow_pro
CORS_ORIGINS=http://localhost:3000
EOF
```

#### تشغيل Backend:
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

### 3️⃣ إعداد Frontend

```bash
cd scanflow-pro/frontend

# تثبيت المكتبات
npm install
# أو
yarn install

# إعداد ملف .env
cat > .env << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
EOF

# تشغيل Frontend
npm start
# أو
yarn start
```

---

## 🚀 التشغيل

### الطريقة 1: تشغيل يدوي (للتطوير)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # أو venv\\Scripts\\activate في Windows
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

**Terminal 3 - MongoDB:**
```bash
mongod --dbpath /path/to/data
```

### الطريقة 2: استخدام Scripts

#### أنشئ ملف `start.sh` (Linux/macOS):
```bash
#!/bin/bash

# بدء MongoDB
echo "Starting MongoDB..."
sudo systemctl start mongod

# بدء Backend
echo "Starting Backend..."
cd backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

# بدء Frontend
echo "Starting Frontend..."
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "ScanFlow Pro is running!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Access at: http://localhost:3000"

# للإيقاف اضغط Ctrl+C
wait
```

#### أنشئ ملف `start.bat` (Windows):
```batch
@echo off

echo Starting MongoDB...
net start MongoDB

echo Starting Backend...
cd backend
call venv\\Scripts\\activate
start /B uvicorn server:app --host 0.0.0.0 --port 8001

echo Starting Frontend...
cd ..\\frontend
start /B npm start

echo ScanFlow Pro is running!
echo Access at: http://localhost:3000
pause
```

---

## ✅ التحقق من التثبيت

### 1. فحص Backend:
```bash
curl http://localhost:8001/api/
# يجب أن يرجع: {"message":"ScanFlow Pro API","version":"1.0.0"}
```

### 2. فحص Frontend:
- افتح المتصفح: http://localhost:3000
- يجب أن تظهر صفحة رفع الملفات

### 3. فحص MongoDB:
```bash
mongosh
> use scanflow_pro
> show collections
# يجب أن تظهر: files, analyses, keywords
```

### 4. فحص Tesseract:
```bash
tesseract --version
tesseract --list-langs
# يجب أن تظهر: ara, fra, eng
```

---

## 🐳 طريقة 3: استخدام Docker (الأسهل)

### إنشاء Dockerfile للـ Backend:
```dockerfile
FROM python:3.11-slim

# تثبيت tesseract
RUN apt-get update && apt-get install -y \\
    tesseract-ocr \\
    tesseract-ocr-ara \\
    tesseract-ocr-fra \\
    tesseract-ocr-eng \\
    poppler-utils

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### docker-compose.yml:
```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db

  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=scanflow_pro
    depends_on:
      - mongodb
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/results:/app/results

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_BACKEND_URL=http://localhost:8001
    depends_on:
      - backend

volumes:
  mongodb_data:
```

### تشغيل Docker:
```bash
docker-compose up -d
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: Backend لا يعمل
```bash
# فحص السجلات
tail -f backend/logs/app.log

# تحقق من المنفذ
lsof -i :8001  # Linux/macOS
netstat -ano | findstr :8001  # Windows
```

### المشكلة: Frontend لا يعمل
```bash
# تحقق من المنفذ
lsof -i :3000  # Linux/macOS
netstat -ano | findstr :3000  # Windows

# امسح Cache
rm -rf node_modules package-lock.json
npm install
```

### المشكلة: Tesseract لا يعمل
```bash
# Windows: أضف Tesseract للـ PATH
# Control Panel > System > Advanced > Environment Variables
# أضف: C:\\Program Files\\Tesseract-OCR

# Linux/macOS: تأكد من التثبيت
which tesseract
```

### المشكلة: MongoDB لا يعمل
```bash
# تحقق من الحالة
sudo systemctl status mongod

# أعد التشغيل
sudo systemctl restart mongod
```

---

## 📱 الوصول من أجهزة أخرى

### في الشبكة المحلية:

1. **اعرف IP الخاص بجهازك:**
```bash
# Windows
ipconfig

# Linux/macOS
ifconfig
# أو
ip addr show
```

2. **عدّل Frontend .env:**
```bash
REACT_APP_BACKEND_URL=http://[YOUR_IP]:8001
```

3. **افتح الجدار الناري:**
```bash
# Linux
sudo ufw allow 8001
sudo ufw allow 3000

# Windows: Firewall Settings
```

4. **الوصول من جهاز آخر:**
```
http://[YOUR_IP]:3000
```

---

## 🔐 الأمان (للإنتاج)

### 1. استخدم HTTPS:
```bash
# احصل على شهادة SSL (Let's Encrypt)
certbot --nginx -d yourdomain.com
```

### 2. غيّر المنافذ الافتراضية

### 3. أضف مصادقة

### 4. استخدم بيئة إنتاج:
```bash
# Backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:app

# Frontend
npm run build
serve -s build
```

---

## 📊 متطلبات النظام

**الحد الأدنى:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB
- Internet: للتحميل الأولي فقط

**الموصى به:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ (للملفات الكبيرة)
- SSD لأداء أفضل

---

## 🎯 الخلاصة

**للبدء السريع:**
1. ثبت: Python, Node.js, MongoDB, Tesseract
2. نزّل الملفات
3. شغل: `setup.sh` أو `setup.bat`
4. افتح: http://localhost:3000

**للإنتاج:**
- استخدم Docker
- أضف HTTPS
- استخدم خادم إنتاج

---

## 📞 الدعم

إذا واجهت مشاكل:
1. راجع قسم استكشاف الأخطاء
2. افحص السجلات
3. تأكد من تثبيت كل المتطلبات

---

**البرنامج جاهز للتحميل والاستخدام! 🚀**
