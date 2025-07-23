# Multi-Tool Document Converter

A comprehensive web application that provides multiple document conversion tools in one place.

## 🚀 Features

### 📄 PDF to Word Conversion
- **NEW: Uses pdf2docx library** - Much more reliable than LibreOffice
- Converts PDF files to editable Word documents (.docx)
- Maintains formatting and structure
- Handles complex layouts and images

### 📝 Word to PDF Conversion
- Convert Word documents (.doc, .docx) to PDF format
- Uses LibreOffice for reliable conversion
- Preserves formatting and layout

### 🔗 PDF Merging
- Combine up to 10 PDF files into a single document
- Maintains page order and quality
- Uses PyPDF2 for fast processing

### 🖼️ Images to PDF
- Convert up to 20 images (JPG, PNG) to PDF
- Automatic scaling and centering
- Supports batch conversion

## 🛠️ Tech Stack

### Frontend
- **React** with TypeScript
- **Tailwind CSS** for styling
- **Vite** for development and building
- Drag-and-drop file upload interface
- Responsive design for mobile and desktop

### Backend
- **Python Flask** API
- **pdf2docx** - Reliable PDF to Word conversion
- **LibreOffice** - Word to PDF conversion
- **PyPDF2** - PDF manipulation and merging
- **Pillow + ReportLab** - Image processing and PDF generation

## 📦 Installation & Setup

### Prerequisites
- Node.js (for frontend)
- Python 3.8+ (for backend)
- LibreOffice (for Word to PDF conversion)

### Frontend Setup
```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Run setup script (installs all dependencies)
./setup.sh

# Start the Flask server
python3 app.py
```

The setup script will:
- Install LibreOffice
- Install Python dependencies including pdf2docx
- Install system dependencies for image processing
- Verify all installations

## 🔧 API Endpoints

### Health Check
```
GET /api/health
```
Returns the status of all conversion services.

### PDF to Word
```
POST /api/convert/pdf-to-word
Content-Type: multipart/form-data
Body: file (PDF)
```

### Word to PDF
```
POST /api/convert/word-to-pdf
Content-Type: multipart/form-data
Body: file (Word document)
```

### Merge PDFs
```
POST /api/convert/merge-pdf
Content-Type: multipart/form-data
Body: file_0, file_1, ..., file_count
```

### Images to PDF
```
POST /api/convert/image-to-pdf
Content-Type: multipart/form-data
Body: file_0, file_1, ..., file_count (or single file)
```

## 🎯 Key Improvements

### PDF to Word Conversion
- **Replaced LibreOffice with pdf2docx library**
- Much more reliable and accurate conversion
- Better handling of complex layouts
- Proper DOCX structure validation
- Files open correctly in Microsoft Word

### Error Handling
- Comprehensive logging to `converter.log`
- File validation before and after conversion
- Proper cleanup of temporary files
- Clear error messages for users

### File Management
- Automatic cleanup of old files (1 hour)
- Proper binary file handling
- MIME type validation
- File size limits (10MB per file)

## 🐛 Troubleshooting

### PDF to Word Issues
If PDF to Word conversion fails:
1. Check if pdf2docx is installed: `pip list | grep pdf2docx`
2. Install if missing: `pip install pdf2docx`
3. Check the logs in `backend/converter.log`

### Word to PDF Issues
If Word to PDF conversion fails:
1. Check LibreOffice installation: `libreoffice --version`
2. Install if missing: `sudo apt-get install libreoffice`
3. Check the logs for LibreOffice errors

### General Issues
- Check file permissions in upload/converted directories
- Ensure all Python dependencies are installed
- Check the Flask server logs for detailed error messages

## 📝 File Limits

- **Maximum file size**: 10MB per file
- **PDF merging**: Up to 10 PDF files
- **Image to PDF**: Up to 20 images
- **Supported formats**:
  - PDF: .pdf
  - Word: .doc, .docx
  - Images: .jpg, .jpeg, .png

## 🔒 Security

- File validation and sanitization
- Temporary file cleanup
- No permanent file storage
- CORS enabled for frontend integration

## 📊 Logging

All conversion activities are logged to `backend/converter.log` including:
- File upload verification
- Conversion process details
- Success/failure status
- File cleanup operations
- Error messages and debugging info

## 🚀 Deployment

### Development
```bash
# Frontend
npm run dev

# Backend
cd backend && python3 app.py
```

### Production
```bash
# Build frontend
npm run build

# Serve with a production server (nginx, apache, etc.)
# Run backend with gunicorn or similar WSGI server
```

## 📄 License

This project is open source and available under the MIT License.