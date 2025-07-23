#!/bin/bash

echo "=== Multi-Tool Document Converter Backend Setup ==="
echo "Setting up Python backend with pdf2docx for reliable PDF to Word conversion..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update

# Install LibreOffice for Word to PDF conversion
echo "📄 Installing LibreOffice for Word to PDF conversion..."
sudo apt-get install -y libreoffice

# Install Python3 and pip if not already installed
echo "🐍 Installing Python3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install system dependencies for pdf2docx and image processing
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    python3-dev \
    libmagic1 \
    libmagic-dev \
    poppler-utils \
    ghostscript \
    imagemagick

# Create virtual environment (optional but recommended)
echo "🌐 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Verify installations
echo ""
echo "=== Verification ==="

# Check LibreOffice
if command -v libreoffice &> /dev/null; then
    echo "✅ LibreOffice installed: $(libreoffice --version)"
else
    echo "❌ LibreOffice installation failed"
fi

# Check Python packages
echo "🐍 Checking Python packages..."
python3 -c "
try:
    import flask
    print('✅ Flask installed:', flask.__version__)
except ImportError:
    print('❌ Flask not installed')

try:
    from pdf2docx import Converter
    print('✅ pdf2docx installed successfully')
except ImportError:
    print('❌ pdf2docx not installed')

try:
    import PyPDF2
    print('✅ PyPDF2 installed:', PyPDF2.__version__)
except ImportError:
    print('❌ PyPDF2 not installed')

try:
    from PIL import Image
    print('✅ Pillow (PIL) installed')
except ImportError:
    print('❌ Pillow not installed')

try:
    from reportlab.pdfgen import canvas
    print('✅ ReportLab installed')
except ImportError:
    print('❌ ReportLab not installed')
"

echo ""
echo "=== Setup Complete! ==="
echo "🚀 To start the backend server, run:"
echo "   cd backend"
echo "   python3 app.py"
echo ""
echo "📝 The server will run on http://localhost:5000"
echo "🔍 Check converter.log for detailed conversion logs"
echo ""
echo "🎯 Key improvements:"
echo "   • PDF to Word: Now uses pdf2docx library (much more reliable than LibreOffice)"
echo "   • Word to PDF: Uses LibreOffice (works well for this direction)"
echo "   • PDF Merge: Uses PyPDF2"
echo "   • Image to PDF: Uses Pillow + ReportLab"