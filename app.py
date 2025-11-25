import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import PyPDF2
import pdf2image
import io
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'gif', 'bmp', 'tiff'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# def extract_text_from_image(image_path):
#     """Extract text from image using pytesseract"""
#     try:
#         image = Image.open(image_path)
#         text = pytesseract.image_to_string(image)
#         return text.strip()
#     except Exception as e:
#         return f"Error extracting text: {str(e)}"
    

def extract_text_from_image(image_path):
    """Extract text from image using pytesseract with optimized settings"""
    try:
        image = Image.open(image_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Use pytesseract with optimized configuration
        custom_config = r'--oem 3 --psm 6 -c tessedit_do_invert=0'
        text = pytesseract.image_to_string(image, config=custom_config)
        
        return text.strip()
    except Exception as e:
        return f"Error extracting text: {str(e)}"


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using multiple methods"""
    text = ""
    
    try:
        # Method 1: Try direct text extraction
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        # Method 2: If direct extraction fails, use OCR
        if not text.strip():
            images = pdf2image.convert_from_path(pdf_path)
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
                
    except Exception as e:
        return f"Error processing PDF: {str(e)}"
    
    return text.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files selected'}), 400
    
    files = request.files.getlist('files[]')
    results = []
    
    for file in files:
        if file and file.filename != '' and allowed_file(file.filename):
            try:
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                
                # Extract text based on file type
                if filename.lower().endswith('.pdf'):
                    extracted_text = extract_text_from_pdf(filepath)
                else:
                    extracted_text = extract_text_from_image(filepath)
                
                results.append({
                    'filename': filename,
                    'text': extracted_text,
                    'success': True
                })
                
                # Clean up uploaded file
                os.remove(filepath)
                
            except Exception as e:
                results.append({
                    'filename': file.filename,
                    'text': f"Error processing file: {str(e)}",
                    'success': False
                })
        else:
            results.append({
                'filename': file.filename,
                'text': "Invalid file type",
                'success': False
            })
    
    return jsonify({'results': results})

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True)