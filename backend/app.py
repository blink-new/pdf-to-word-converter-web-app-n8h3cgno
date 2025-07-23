#!/usr/bin/env python3
"""
Multi-Tool Document Converter Backend
A Flask API that supports:
- PDF to Word conversion (using pdf2docx)
- Word to PDF conversion (using LibreOffice)
- PDF merging
- Image to PDF conversion
"""

import os
import tempfile
import subprocess
import uuid
import logging
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import time
from PIL import Image
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
import io
import zipfile

# Import pdf2docx for reliable PDF to Word conversion
try:
    from pdf2docx import Converter
    PDF2DOCX_AVAILABLE = True
    print("✅ pdf2docx library loaded successfully")
except ImportError:
    PDF2DOCX_AVAILABLE = False
    print("❌ pdf2docx library not available - PDF to Word conversion will not work")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Configuration
UPLOAD_FOLDER = tempfile.mkdtemp()
CONVERTED_FOLDER = tempfile.mkdtemp()
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    'pdf': {'pdf'},
    'word': {'doc', 'docx'},
    'image': {'jpg', 'jpeg', 'png'}
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename, file_type):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[file_type]

def cleanup_old_files():
    """Clean up files older than 1 hour"""
    while True:
        try:
            current_time = time.time()
            
            # Clean upload folder
            for file_path in Path(UPLOAD_FOLDER).glob('*'):
                if current_time - file_path.stat().st_mtime > 3600:  # 1 hour
                    file_path.unlink(missing_ok=True)
                    logger.info(f"Cleaned up old upload file: {file_path}")
            
            # Clean converted folder
            for file_path in Path(CONVERTED_FOLDER).glob('*'):
                if current_time - file_path.stat().st_mtime > 3600:  # 1 hour
                    file_path.unlink(missing_ok=True)
                    logger.info(f"Cleaned up old converted file: {file_path}")
                    
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        time.sleep(1800)  # Run every 30 minutes

def check_libreoffice_installation():
    """Check if LibreOffice is properly installed"""
    try:
        result = subprocess.run(['libreoffice', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"LibreOffice version: {result.stdout.strip()}")
            return True
        else:
            logger.error("LibreOffice not found or not working")
            return False
    except Exception as e:
        logger.error(f"LibreOffice check failed: {e}")
        return False

def convert_pdf_to_docx_with_pdf2docx(pdf_path, docx_path):
    """
    Convert PDF to DOCX using pdf2docx library - much more reliable than LibreOffice
    """
    try:
        logger.info(f"=== Starting pdf2docx conversion ===")
        logger.info(f"Input PDF: {pdf_path}")
        logger.info(f"Output DOCX: {docx_path}")
        
        # Validate input file
        if not os.path.exists(pdf_path):
            raise Exception(f"Input PDF file does not exist: {pdf_path}")
        
        input_size = os.path.getsize(pdf_path)
        if input_size == 0:
            raise Exception(f"Input PDF file is empty: {pdf_path}")
        
        logger.info(f"Input PDF size: {input_size} bytes")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(docx_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Remove any existing output file
        if os.path.exists(docx_path):
            os.remove(docx_path)
            logger.info(f"Removed existing output file: {docx_path}")
        
        # Convert PDF to DOCX using pdf2docx
        logger.info("Starting pdf2docx conversion...")
        
        # Create converter instance
        cv = Converter(pdf_path)
        
        # Convert with progress tracking
        try:
            cv.convert(docx_path, start=0, end=None)  # Convert all pages
            cv.close()
            logger.info("✅ pdf2docx conversion completed")
        except Exception as e:
            cv.close()
            raise Exception(f"pdf2docx conversion failed: {str(e)}")
        
        # Wait for file system to sync
        time.sleep(0.5)
        
        # Validate output file
        if not os.path.exists(docx_path):
            raise Exception("pdf2docx did not create output file")
        
        output_size = os.path.getsize(docx_path)
        logger.info(f"Output DOCX size: {output_size} bytes")
        
        if output_size == 0:
            raise Exception("Output DOCX file is empty")
        
        if output_size < 100:  # Very small files are likely corrupted
            raise Exception(f"Output DOCX file is suspiciously small ({output_size} bytes)")
        
        # Validate DOCX structure
        logger.info("Validating DOCX file structure...")
        
        try:
            with zipfile.ZipFile(docx_path, 'r') as zip_file:
                zip_contents = zip_file.namelist()
                logger.info(f"DOCX contains {len(zip_contents)} files")
                
                # Check for essential DOCX components
                required_files = ['[Content_Types].xml', 'word/document.xml']
                missing_files = []
                
                for req_file in required_files:
                    if req_file not in zip_contents:
                        missing_files.append(req_file)
                
                if missing_files:
                    raise Exception(f"DOCX missing essential files: {missing_files}")
                
                # Try to read the main document
                try:
                    document_xml = zip_file.read('word/document.xml')
                    if len(document_xml) < 50:
                        raise Exception("Document XML is too small - likely corrupted")
                    else:
                        logger.info(f"Document XML size: {len(document_xml)} bytes")
                except KeyError:
                    raise Exception("Could not read word/document.xml - DOCX is corrupted")
                
                logger.info("✅ DOCX structure validation passed")
                
        except zipfile.BadZipFile as e:
            raise Exception(f"Generated DOCX is not a valid ZIP file: {e}")
        
        logger.info(f"✅ PDF to DOCX conversion successful: {docx_path}")
        return docx_path
        
    except Exception as e:
        logger.error(f"❌ PDF to DOCX conversion failed: {str(e)}")
        raise Exception(f"PDF to DOCX conversion failed: {str(e)}")

def convert_with_libreoffice(input_path, output_dir, output_format):
    """
    Convert documents using LibreOffice (for Word to PDF only)
    """
    try:
        logger.info(f"=== Starting LibreOffice conversion ===")
        logger.info(f"Input: {input_path}")
        logger.info(f"Output dir: {output_dir}")
        logger.info(f"Format: {output_format}")
        
        # Validate input file
        if not os.path.exists(input_path):
            raise Exception(f"Input file does not exist: {input_path}")
        
        input_size = os.path.getsize(input_path)
        if input_size == 0:
            raise Exception(f"Input file is empty: {input_path}")
        
        logger.info(f"Input file size: {input_size} bytes")
        
        # Ensure output directory exists and is writable
        os.makedirs(output_dir, exist_ok=True)
        if not os.access(output_dir, os.W_OK):
            raise Exception(f"Output directory is not writable: {output_dir}")
        
        # Get input file info
        input_path_obj = Path(input_path)
        input_name = input_path_obj.stem
        
        # Define expected output file
        output_filename = f"{input_name}.{output_format}"
        expected_output = Path(output_dir) / output_filename
        
        # Remove any existing output file
        if expected_output.exists():
            os.remove(expected_output)
            logger.info(f"Removed existing output file: {expected_output}")
        
        # Build LibreOffice command
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', output_format,
            '--outdir', str(output_dir),
            str(input_path)
        ]
        
        logger.info(f"LibreOffice command: {' '.join(cmd)}")
        
        # Set up environment for headless operation
        env = os.environ.copy()
        env['HOME'] = tempfile.gettempdir()
        env['TMPDIR'] = tempfile.gettempdir()
        
        # Run LibreOffice conversion
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env,
                cwd=output_dir
            )
            
            logger.info(f"LibreOffice exit code: {result.returncode}")
            if result.stdout:
                logger.info(f"LibreOffice stdout: {result.stdout}")
            if result.stderr:
                logger.info(f"LibreOffice stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"LibreOffice failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                raise Exception(error_msg)
                
        except subprocess.TimeoutExpired:
            raise Exception("LibreOffice conversion timeout - file may be too large or complex")
        
        # Wait for file system to sync
        time.sleep(1)
        
        # Check if output file was created
        if not expected_output.exists():
            # Try to find the file with different naming
            possible_files = list(Path(output_dir).glob(f"{input_name}.*"))
            logger.info(f"Possible output files: {[str(f) for f in possible_files]}")
            
            for pf in possible_files:
                if pf.suffix.lower() == f'.{output_format.lower()}':
                    expected_output = pf
                    logger.info(f"Found output file: {expected_output}")
                    break
            
            if not expected_output.exists():
                raise Exception(f"LibreOffice did not create output file. Expected: {expected_output}")
        
        # Validate output file
        output_size = expected_output.stat().st_size
        logger.info(f"Output file size: {output_size} bytes")
        
        if output_size == 0:
            raise Exception("Output file is empty")
        
        if output_size < 50:
            raise Exception(f"Output file is suspiciously small ({output_size} bytes)")
        
        logger.info(f"✅ LibreOffice conversion successful: {expected_output}")
        return str(expected_output)
        
    except Exception as e:
        logger.error(f"❌ LibreOffice conversion failed: {str(e)}")
        raise Exception(f"LibreOffice conversion failed: {str(e)}")

def merge_pdfs(pdf_paths, output_path):
    """
    Merge multiple PDF files into one
    """
    try:
        logger.info(f"Starting PDF merge: {len(pdf_paths)} files -> {output_path}")
        
        pdf_writer = PyPDF2.PdfWriter()
        
        for i, pdf_path in enumerate(pdf_paths):
            logger.info(f"Processing PDF {i+1}/{len(pdf_paths)}: {pdf_path}")
            
            if not os.path.exists(pdf_path):
                raise Exception(f"PDF file does not exist: {pdf_path}")
            
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Check if PDF is valid
                    if len(pdf_reader.pages) == 0:
                        raise Exception(f"PDF file has no pages: {pdf_path}")
                    
                    logger.info(f"PDF {i+1} has {len(pdf_reader.pages)} pages")
                    
                    # Add all pages from this PDF
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdf_writer.add_page(page)
                        
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_path}: {e}")
                raise Exception(f"Error processing PDF {os.path.basename(pdf_path)}: {str(e)}")
        
        # Write the merged PDF
        logger.info(f"Writing merged PDF to: {output_path}")
        with open(output_path, 'wb') as output_file:
            pdf_writer.write(output_file)
        
        # Verify the output file
        if not os.path.exists(output_path):
            raise Exception("Failed to create merged PDF file")
        
        if os.path.getsize(output_path) == 0:
            raise Exception("Merged PDF file is empty")
        
        logger.info(f"PDF merge successful: {output_path} (size: {os.path.getsize(output_path)} bytes)")
        return output_path
        
    except Exception as e:
        logger.error(f"PDF merge error: {str(e)}")
        raise Exception(f"PDF merge error: {str(e)}")

def images_to_pdf(image_paths, output_path):
    """
    Convert multiple images to a single PDF
    """
    try:
        logger.info(f"Starting image to PDF conversion: {len(image_paths)} images -> {output_path}")
        
        c = canvas.Canvas(output_path, pagesize=letter)
        page_width, page_height = letter
        
        processed_images = 0
        
        for i, image_path in enumerate(image_paths):
            try:
                logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
                
                if not os.path.exists(image_path):
                    logger.warning(f"Image file does not exist: {image_path}")
                    continue
                
                # Open and process the image
                with Image.open(image_path) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        logger.info(f"Converting image mode from {img.mode} to RGB")
                        img = img.convert('RGB')
                    
                    # Calculate scaling to fit page while maintaining aspect ratio
                    img_width, img_height = img.size
                    logger.info(f"Image dimensions: {img_width}x{img_height}")
                    
                    # Leave margins (50 points on each side)
                    max_width = page_width - 100
                    max_height = page_height - 100
                    
                    # Calculate scale factor
                    scale_x = max_width / img_width
                    scale_y = max_height / img_height
                    scale = min(scale_x, scale_y)
                    
                    # Calculate new dimensions
                    new_width = img_width * scale
                    new_height = img_height * scale
                    
                    # Center the image on the page
                    x = (page_width - new_width) / 2
                    y = (page_height - new_height) / 2
                    
                    logger.info(f"Scaled dimensions: {new_width:.1f}x{new_height:.1f} at ({x:.1f}, {y:.1f})")
                    
                    # Save image to bytes for reportlab
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='JPEG', quality=85)
                    img_buffer.seek(0)
                    
                    # Draw image on PDF
                    c.drawImage(ImageReader(img_buffer), x, y, new_width, new_height)
                    c.showPage()  # Start new page for next image
                    processed_images += 1
                    
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
                continue
        
        if processed_images == 0:
            raise Exception("No images could be processed")
        
        c.save()
        
        # Verify the output file
        if not os.path.exists(output_path):
            raise Exception("Failed to create PDF file")
        
        if os.path.getsize(output_path) == 0:
            raise Exception("Generated PDF file is empty")
        
        logger.info(f"Image to PDF conversion successful: {processed_images} images processed, output: {output_path} (size: {os.path.getsize(output_path)} bytes)")
        return output_path
        
    except Exception as e:
        logger.error(f"Image to PDF conversion error: {str(e)}")
        raise Exception(f"Image to PDF conversion error: {str(e)}")

def cleanup_files_after_response(file_paths):
    """Clean up files after the response is sent"""
    def cleanup():
        time.sleep(3)  # Wait 3 seconds to ensure download completes
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {file_path}: {e}")
    
    return cleanup

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    libreoffice_ok = check_libreoffice_installation()
    
    return jsonify({
        'status': 'healthy' if (PDF2DOCX_AVAILABLE and libreoffice_ok) else 'degraded',
        'message': 'Multi-Tool Document Converter API is running',
        'pdf2docx_available': PDF2DOCX_AVAILABLE,
        'libreoffice_available': libreoffice_ok,
        'supported_tools': ['pdf-to-word', 'word-to-pdf', 'merge-pdf', 'image-to-pdf']
    })

@app.route('/api/convert/pdf-to-word', methods=['POST'])
def convert_pdf_to_word():
    """Convert PDF to Word document using pdf2docx library"""
    uploaded_files = []
    converted_files = []
    
    try:
        logger.info("=== PDF to Word Conversion Request ===")
        
        # Check pdf2docx availability
        if not PDF2DOCX_AVAILABLE:
            return jsonify({'error': 'pdf2docx library is not available. Please install it: pip install pdf2docx'}), 500
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save uploaded file with unique name
        unique_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        pdf_filename = f"{unique_id}_{filename}"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        logger.info(f"Saving uploaded PDF: {pdf_path}")
        file.save(pdf_path)
        uploaded_files.append(pdf_path)
        
        # Verify file was saved correctly
        if not os.path.exists(pdf_path):
            raise Exception("Failed to save uploaded file")
        
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            raise Exception("Uploaded file is empty")
        
        logger.info(f"✅ File saved successfully (size: {file_size} bytes)")
        
        # Generate output path
        original_name = Path(filename).stem
        docx_filename = f"{unique_id}_{original_name}.docx"
        docx_path = os.path.join(app.config['CONVERTED_FOLDER'], docx_filename)
        
        # Convert PDF to DOCX using pdf2docx
        logger.info("Starting PDF to DOCX conversion with pdf2docx...")
        convert_pdf_to_docx_with_pdf2docx(pdf_path, docx_path)
        converted_files.append(docx_path)
        
        # Final validation
        if not os.path.exists(docx_path):
            raise Exception("Conversion completed but output file not found")
        
        docx_size = os.path.getsize(docx_path)
        if docx_size == 0:
            raise Exception("Conversion completed but output file is empty")
        
        # Generate download filename
        download_filename = f"{original_name}.docx"
        
        logger.info(f"✅ Sending DOCX file: {download_filename} (size: {docx_size} bytes)")
        
        # Schedule cleanup after response is sent
        @after_this_request
        def cleanup_files(response):
            cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
            threading.Thread(target=cleanup_func, daemon=True).start()
            return response
        
        # Send the file with proper headers
        return send_file(
            docx_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        logger.error(f"❌ PDF to Word conversion error: {str(e)}")
        
        # Clean up files immediately on error
        cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
        cleanup_func()
        
        return jsonify({'error': f'Conversion error: {str(e)}'}), 500

@app.route('/api/convert/word-to-pdf', methods=['POST'])
def convert_word_to_pdf():
    """Convert Word document to PDF"""
    uploaded_files = []
    converted_files = []
    
    try:
        logger.info("=== Word to PDF Conversion Request ===")
        
        # Check LibreOffice availability
        if not check_libreoffice_installation():
            return jsonify({'error': 'LibreOffice is not available. Please install LibreOffice for document conversion.'}), 500
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'word'):
            return jsonify({'error': 'Only Word documents (.doc, .docx) are allowed'}), 400
        
        # Save uploaded file
        unique_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        word_filename = f"{unique_id}_{filename}"
        word_path = os.path.join(app.config['UPLOAD_FOLDER'], word_filename)
        
        logger.info(f"Saving uploaded Word file: {word_path}")
        file.save(word_path)
        uploaded_files.append(word_path)
        
        # Verify file was saved correctly
        if not os.path.exists(word_path):
            raise Exception("Failed to save uploaded file")
        
        file_size = os.path.getsize(word_path)
        if file_size == 0:
            raise Exception("Uploaded file is empty")
        
        logger.info(f"✅ File saved successfully (size: {file_size} bytes)")
        
        # Convert Word to PDF
        logger.info("Starting Word to PDF conversion...")
        pdf_path = convert_with_libreoffice(word_path, app.config['CONVERTED_FOLDER'], 'pdf')
        converted_files.append(pdf_path)
        
        # Generate download filename
        original_name = Path(filename).stem
        download_filename = f"{original_name}.pdf"
        
        logger.info(f"✅ Sending PDF file: {download_filename}")
        
        # Schedule cleanup after response is sent
        @after_this_request
        def cleanup_files(response):
            cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
            threading.Thread(target=cleanup_func, daemon=True).start()
            return response
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"❌ Word to PDF conversion error: {str(e)}")
        
        # Clean up files immediately on error
        cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
        cleanup_func()
        
        return jsonify({'error': f'Conversion error: {str(e)}'}), 500

@app.route('/api/convert/merge-pdf', methods=['POST'])
def merge_pdf_files():
    """Merge multiple PDF files into one"""
    uploaded_files = []
    converted_files = []
    
    try:
        logger.info("=== PDF Merge Request ===")
        
        # Get file count
        file_count = int(request.form.get('file_count', 0))
        
        if file_count < 2:
            return jsonify({'error': 'At least 2 PDF files are required for merging'}), 400
        
        if file_count > 10:
            return jsonify({'error': 'Maximum 10 PDF files allowed for merging'}), 400
        
        logger.info(f"Merging {file_count} PDF files")
        
        # Collect uploaded files
        pdf_paths = []
        
        for i in range(file_count):
            file_key = f'file_{i}'
            if file_key not in request.files:
                return jsonify({'error': f'Missing file {i+1}'}), 400
            
            file = request.files[file_key]
            
            if file.filename == '':
                return jsonify({'error': f'File {i+1} is empty'}), 400
            
            if not allowed_file(file.filename, 'pdf'):
                return jsonify({'error': f'File {i+1} must be a PDF'}), 400
            
            # Save uploaded file
            unique_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            pdf_filename = f"{unique_id}_{filename}"
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            
            logger.info(f"Saving file {i+1}: {pdf_path}")
            file.save(pdf_path)
            uploaded_files.append(pdf_path)
            pdf_paths.append(pdf_path)
            
            # Verify file was saved correctly
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                raise Exception(f"Failed to save file {i+1}")
            
            logger.info(f"✅ File {i+1} saved (size: {os.path.getsize(pdf_path)} bytes)")
        
        # Merge PDFs
        merged_filename = f"merged_{str(uuid.uuid4())}.pdf"
        merged_path = os.path.join(app.config['CONVERTED_FOLDER'], merged_filename)
        
        merge_pdfs(pdf_paths, merged_path)
        converted_files.append(merged_path)
        
        logger.info(f"✅ Sending merged PDF file")
        
        # Schedule cleanup after response is sent
        @after_this_request
        def cleanup_files(response):
            cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
            threading.Thread(target=cleanup_func, daemon=True).start()
            return response
        
        return send_file(
            merged_path,
            as_attachment=True,
            download_name='merged_document.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"❌ PDF merge error: {str(e)}")
        
        # Clean up files immediately on error
        cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
        cleanup_func()
        
        return jsonify({'error': f'Merge error: {str(e)}'}), 500

@app.route('/api/convert/image-to-pdf', methods=['POST'])
def convert_images_to_pdf():
    """Convert images to PDF"""
    uploaded_files = []
    converted_files = []
    
    try:
        logger.info("=== Image to PDF Conversion Request ===")
        
        # Check if single file or multiple files
        if 'file' in request.files:
            # Single file
            files = [request.files['file']]
        else:
            # Multiple files
            file_count = int(request.form.get('file_count', 0))
            
            if file_count == 0:
                return jsonify({'error': 'No files uploaded'}), 400
            
            if file_count > 20:
                return jsonify({'error': 'Maximum 20 images allowed'}), 400
            
            files = []
            for i in range(file_count):
                file_key = f'file_{i}'
                if file_key in request.files:
                    files.append(request.files[file_key])
        
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        logger.info(f"Converting {len(files)} images to PDF")
        
        # Validate and save files
        image_paths = []
        
        for i, file in enumerate(files):
            if file.filename == '':
                return jsonify({'error': f'File {i+1} is empty'}), 400
            
            if not allowed_file(file.filename, 'image'):
                return jsonify({'error': f'File {i+1} must be an image (JPG, JPEG, PNG)'}), 400
            
            # Save uploaded file
            unique_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            image_filename = f"{unique_id}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            
            logger.info(f"Saving image {i+1}: {image_path}")
            file.save(image_path)
            uploaded_files.append(image_path)
            image_paths.append(image_path)
            
            # Verify file was saved correctly
            if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
                raise Exception(f"Failed to save image {i+1}")
            
            logger.info(f"✅ Image {i+1} saved (size: {os.path.getsize(image_path)} bytes)")
        
        # Convert images to PDF
        pdf_filename = f"images_{str(uuid.uuid4())}.pdf"
        pdf_path = os.path.join(app.config['CONVERTED_FOLDER'], pdf_filename)
        
        images_to_pdf(image_paths, pdf_path)
        converted_files.append(pdf_path)
        
        # Generate download filename
        if len(files) == 1:
            original_name = Path(files[0].filename).stem
            download_filename = f"{original_name}.pdf"
        else:
            download_filename = 'images_combined.pdf'
        
        logger.info(f"✅ Sending PDF file: {download_filename}")
        
        # Schedule cleanup after response is sent
        @after_this_request
        def cleanup_files(response):
            cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
            threading.Thread(target=cleanup_func, daemon=True).start()
            return response
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"❌ Image to PDF conversion error: {str(e)}")
        
        # Clean up files immediately on error
        cleanup_func = cleanup_files_after_response(uploaded_files + converted_files)
        cleanup_func()
        
        return jsonify({'error': f'Image conversion error: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    logger.warning("File too large error")
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
    cleanup_thread.start()
    
    # Create directories if they don't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CONVERTED_FOLDER, exist_ok=True)
    
    logger.info("=== Multi-Tool Document Converter API Starting ===")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Converted folder: {CONVERTED_FOLDER}")
    logger.info("Supported conversions:")
    logger.info("  - PDF to Word (.docx) using pdf2docx")
    logger.info("  - Word to PDF using LibreOffice")
    logger.info("  - Merge multiple PDFs")
    logger.info("  - Images (JPG/PNG) to PDF")
    
    # Check dependencies
    if PDF2DOCX_AVAILABLE:
        logger.info("✅ pdf2docx is available for PDF to Word conversion")
    else:
        logger.warning("⚠️  pdf2docx not found - PDF to Word conversion will not work")
        logger.warning("   Please run: pip install pdf2docx")
    
    if check_libreoffice_installation():
        logger.info("✅ LibreOffice is available for Word to PDF conversion")
    else:
        logger.warning("⚠️  LibreOffice not found - Word to PDF conversion will not work")
        logger.warning("   Please run: sudo apt-get install libreoffice")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)