# دليل التثبيت على Windows - ScanFlow Pro

## المتطلبات الأساسية

قبل التثبيت، تأكد من تحميل وتثبيت:

### 1. Python 3.11 أو أحدث
- تحميل من: https://www.python.org/downloads/
- ✅ **مهم جداً**: اختر "Add Python to PATH" أثناء التثبيت

### 2. Node.js 18 أو أحدث
- تحميل من: https://nodejs.org/
- سيتم تثبيت npm تلقائياً

### 3. MongoDB (اختياري)
**الخيار 1: MongoDB محلي**
- تحميل من: https://www.mongodb.com/try/download/community
- اتبع تعليمات التثبيت
- شغّل MongoDB Service

**الخيار 2: MongoDB Atlas (سحابي - مجاني)**
- سجل حساب على: https://www.mongodb.com/cloud/atlas
- أنشئ Cluster مجاني
- احصل على Connection String
- ضعه في `backend/.env`:
  ```
  MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/
  ```

### 4. Tesseract OCR (مطلوب للـ OCR)
- تحميل من: https://github.com/UB-Mannheim/tesseract/wiki
- الملف: `tesseract-ocr-w64-setup-5.3.3.20231005.exe`
- **مهم**: المسار الافتراضي: `C:\Program Files\Tesseract-OCR`

#### إضافة Tesseract إلى PATH:
1. انسخ المسار: `C:\Program Files\Tesseract-OCR`
2. اذهب إلى:
   - Control Panel → System → Advanced System Settings
   - Environment Variables
   - تحت System Variables، اختر `Path` واضغط Edit
   - اضغط New وألصق المسار
   - OK على كل النوافذ
3. أعد تشغيل Command Prompt

#### تحميل ملفات اللغات:
- العربية: https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata
- الفرنسية: https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
- ضعها في: `C:\Program Files\Tesseract-OCR\tessdata\`

---

## طريقة التثبيت

### الطريقة الأولى: التثبيت التلقائي (مُوصى به)

1. **فك ضغط المشروع**
   - استخرج جميع الملفات إلى مجلد (مثلاً: `C:\ScanFlowPro`)

2. **تشغيل ملف التثبيت**
   - انقر بزر الماوس الأيمن على `install.bat`
   - اختر **"Run as Administrator"** (تشغيل كمسؤول)
   - اتبع التعليمات على الشاشة

3. **انتظر حتى انتهاء التثبيت**
   - سيتم تثبيت جميع المكتبات تلقائياً
   - قد يستغرق 5-10 دقائق

### الطريقة الثانية: التثبيت اليدوي

#### Backend:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend:
```bash
cd frontend
npm install -g yarn
yarn install
```

---

## التشغيل

### الطريقة السريعة:
1. **ابدأ MongoDB** (إذا كنت تستخدم MongoDB محلي)
   - من Services أو Command Prompt: `net start MongoDB`

2. **شغّل التطبيق**
   - انقر مرتين على `start.bat`
   - سيتم فتح نافذتين للـ Backend والـ Frontend
   - سيفتح المتصفح تلقائياً على: http://localhost:3000

### إيقاف التطبيق:
- أغلق النافذتين (Backend و Frontend)
- أو اضغط `Ctrl+C` في كل نافذة

---

## الروابط

- **التطبيق**: http://localhost:3000
- **API Backend**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

---

## حل المشاكل الشائعة

### 1. خطأ: "Python is not recognized"
- **الحل**: تأكد من إضافة Python إلى PATH
- أعد تشغيل الحاسوب بعد تثبيت Python

### 2. خطأ: "Tesseract is not installed"
- **الحل**: 
  - تأكد من تثبيت Tesseract
  - أضفه إلى PATH
  - أعد تشغيل Command Prompt

### 3. خطأ: "MongoDB connection failed"
- **الحل**:
  - تأكد من تشغيل MongoDB Service
  - أو استخدم MongoDB Atlas وحدّث Connection String

### 4. Frontend لا يفتح:
- **الحل**: 
  - تأكد من تثبيت Node.js
  - افتح `http://localhost:3000` يدوياً
  - تحقق من عدم استخدام Port 3000 من برنامج آخر

### 5. خطأ: "Port already in use"
- **الحل**:
  - Backend (8001): أغلق أي تطبيق يستخدم هذا المنفذ
  - Frontend (3000): نفس الشيء

---

## ملاحظات

- تأكد من تشغيل `install.bat` كمسؤول
- لا تغلق نوافذ Backend/Frontend أثناء استخدام التطبيق
- الملفات المُحملة تُحفظ في: `backend/uploads/`
- النتائج تُحفظ في: `backend/results/codes/`

---

## الدعم

إذا واجهت أي مشكلة:
1. تحقق من Logs في نوافذ Backend/Frontend
2. تأكد من تثبيت جميع المتطلبات بشكل صحيح
3. أعد تشغيل التطبيق

---

**🎉 استمتع باستخدام ScanFlow Pro!**
