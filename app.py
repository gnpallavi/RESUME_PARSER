"""
AI Resume Parser - Flask Web Application
This application parses resumes (PDF, DOCX, and PNG) and extracts:
- Email addresses
- Phone numbers
- Skills from a predefined list
"""

import os
import re
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pdfplumber
from docx import Document
import pytesseract
from PIL import Image
import database

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'resume_parser_secret_key'  # Required for flash messages

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max upload size: 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Predefined skill list
SKILL_LIST = [
    'python', 'java', 'c', 'c++', 'c#', 'html', 'css', 'javascript',
    'typescript', 'sql', 'mysql', 'postgresql', 'mongodb', 'machine learning',
    'ai', 'artificial intelligence', 'data science', 'flask', 'django',
    'git', 'github', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
    'react', 'angular', 'vue', 'node.js', 'express', 'spring', 'hibernate',
    'rest api', 'graphql', 'linux', 'unix', 'powershell', 'bash',
    'excel', 'power bi', 'tableau', 'pandas', 'numpy', 'tensorflow',
    'pytorch', 'keras', 'scikit-learn', 'nlp', 'computer vision',
    'agile', 'scrum', 'jira', 'jenkins', 'ci/cd', 'devops'
]

# Section keywords for detection (exact match as per requirements)
SECTION_KEYWORDS = [
    "Education", "Skills", "Projects", "Certifications", "Experience"
]


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    # Clean the extracted text
    return clean_text(text)


def extract_text_from_docx(docx_path):
    """Extract text from DOCX using python-docx"""
    text = ""
    doc = Document(docx_path)
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    # Also extract text from tables if any
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += cell.text + "\n"
    # Clean the extracted text
    return clean_text(text)


def extract_text_from_png(png_path):
    """Extract text from PNG using OCR (pytesseract)"""
    try:
        # Open the image
        image = Image.open(png_path)
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode == 'RGBA':
            # Create a white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            # Paste the image on the background
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use pytesseract to extract text
        text = pytesseract.image_to_string(image)
        
        # Clean the extracted text
        return clean_text(text)
    except Exception as e:
        print(f"Error extracting text from PNG: {e}")
        return ""


def clean_text(text):
    """Clean and normalize extracted text for better parsing accuracy"""
    if not text:
        return ""
    
    # Step 1: Replace various types of whitespace with single space
    text = re.sub(r'[\t\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000]+', ' ', text)
    
    # Step 2: Remove common PDF extraction artifacts and symbols
    text = re.sub(r'[\u2500-\u25FF\u2600-\u26FF\u2700-\u27BF\uFE0F]', '', text)
    
    # Step 3: Fix hyphenation at line breaks (merge broken lines)
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # Step 4: Fix common OCR/PDF extraction errors
    text = re.sub(r'(.)\1{3,}', r'\1\1', text)
    
    # Step 5: Normalize multiple newlines to double newline (paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Step 6: Normalize multiple spaces to single space
    text = re.sub(r' {2,}', ' ', text)
    
    # Step 7: Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Step 8: Fix common email/phone artifacts in text
    text = re.sub(r'_+', '', text)
    
    # Step 9: Handle common resume formatting issues
    text = re.sub(r'^[-=_*]{3,}$', '', text, flags=re.MULTILINE)
    
    # Step 10: Final cleanup - remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Step 11: Restore proper paragraph breaks
    text = re.sub(r'(?<=[.!?])\s+([A-Z])', r'\n\1', text)
    
    return text


def extract_name(text):
    """
    Extract candidate name from resume text.
    
    Strategy:
    1. Use direct regex to find "Name:" label anywhere in text
    2. Extract value after "Name:" until next keyword (Email, Phone, etc.)
    3. If no "Name:" label, use fallback logic with first 200 characters
    
    Validation:
    - Only alphabets and spaces allowed
    - 2 to 4 words
    - No numbers
    - No special characters
    """
    # Debug: Show extracted text
    print("\n" + "="*50)
    print("NAME EXTRACTION DEBUG")
    print("="*50)
    print(f"Extracted text (first 500 chars): {text[:500]}")
    
    if not text:
        print("Text is empty!")
        return "Not Found"
    
    # Strategy 1: Direct regex extraction - find "Name:" anywhere in text
    # Pattern to find Name: followed by name until next keyword like Email, Phone, etc.
    name_label_pattern = r'Name\s*:\s*([A-Za-z\s]+?)(?=\s*(?:Email|Phone|Mobile|Address|Location|Resume|CV|$))'
    match = re.search(name_label_pattern, text, re.IGNORECASE)
    
    if match:
        name = match.group(1).strip()
        # Clean the name - remove extra spaces
        name = clean_name_candidate(name)
        print(f"\nFound 'Name:' label via regex. Extracted: '{name}'")
        
        if is_valid_name(name):
            print(f"Name validated successfully: '{name}'")
            return name
        else:
            print(f"Name from label failed validation: '{name}'")
    
    # Strategy 2: Look for "Name:" at the start of a line (case insensitive)
    # This handles cases where text might have newlines
    lines = text.split('\n')
    for line in lines:
        line_match = re.search(r'^Name\s*:\s*(.+)$', line, re.IGNORECASE)
        if line_match:
            name = line_match.group(1).strip()
            name = clean_name_candidate(name)
            print(f"\nFound 'Name:' label at line start. Extracted: '{name}'")
            if is_valid_name(name):
                print(f"Name validated successfully: '{name}'")
                return name
    
    # Strategy 3: Fallback - use first 200 characters
    print("\nNo 'Name:' label found. Using fallback with first 200 characters...")
    first_200 = text[:200]
    print(f"First 200 chars: '{first_200}'")
    
    # Try to find name pattern in first 200 characters
    # Look for common patterns like "Name: Name" or just the first valid name
    first_lines = [line.strip() for line in first_200.split('\n') if line.strip()]
    
    # If no newlines, try to extract name from the beginning
    if not first_lines:
        # Extract first few words and check if they form a valid name
        words = first_200.split()[:5]  # Get first 5 words
        for i in range(len(words), 1, -1):  # Try from 5 words down to 2
            candidate = ' '.join(words[:i])
            cleaned = clean_name_candidate(candidate)
            if is_valid_name(cleaned):
                print(f"Valid name found from first words: '{cleaned}'")
                return cleaned
    
    # Check first few lines
    for line in first_lines[:5]:
        cleaned_line = clean_name_candidate(line)
        
        # Skip if it's a section header
        if is_section_header(cleaned_line):
            print(f"  Skipping section header: '{cleaned_line}'")
            continue
        
        # Skip if it's an email
        if is_email(cleaned_line):
            print(f"  Skipping email: '{cleaned_line}'")
            continue
        
        # Skip if it's a phone number
        if is_phone_number(cleaned_line):
            print(f"  Skipping phone: '{cleaned_line}'")
            continue
        
        # Validate as name
        if is_valid_name(cleaned_line):
            print(f"  Valid name found: '{cleaned_line}'")
            return cleaned_line
    
    print("\nNo valid name found!")
    return "Not Found"


def clean_name_candidate(name):
    """
    Clean a potential name by removing extra spaces and special characters.
    
    - Removes extra whitespace
    - Keeps only alphabets and spaces
    """
    if not name:
        return ""
    
    # Remove extra spaces
    name = ' '.join(name.split())
    
    # Keep only alphabets and spaces
    cleaned = re.sub(r'[^A-Za-z\s]', '', name)
    
    # Remove extra spaces again after cleaning
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()


def is_valid_name(name):
    """
    Validate if the extracted text is a valid name.
    
    Rules:
    - Should be 2-4 words
    - Should not contain numbers
    - Should not contain special symbols (only letters and spaces)
    """
    if not name or len(name) < 2:
        return False
    
    # Strip whitespace
    name = name.strip()
    
    # Must have at least 2 characters after stripping
    if len(name) < 2:
        return False
    
    # Check for numbers - should NOT have any
    if any(char.isdigit() for char in name):
        return False
    
    # Check for special symbols - only allow letters and spaces
    if re.search(r'[^A-Za-z\s]', name):
        return False
    
    # Split into words
    words = name.split()
    
    # Check word count (2-4 words)
    if len(words) < 2 or len(words) > 4:
        return False
    
    # Each word should have at least 1 character
    for word in words:
        if len(word) < 1:
            return False
    
    return True


def is_section_header(line):
    """
    Check if a line is a section header.
    
    Section headers to exclude:
    - Education
    - Skills
    - Projects
    - Certifications
    - Experience
    """
    section_headers = [
        "education", "skills", "projects", "certifications", "experience"
    ]
    
    line_lower = line.lower().strip()
    
    # Exact match
    if line_lower in section_headers:
        return True
    
    # Check for headers with punctuation like "Education:", "Skills -", etc.
    for header in section_headers:
        if (line_lower == header or 
            line_lower.startswith(header + ':') or
            line_lower.startswith(header + ' -') or
            line_lower.startswith(header + ' ')):
            return True
    
    return False


def is_email(text):
    """
    Check if the text is an email address.
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, text.strip()) is not None


def is_phone_number(text):
    """
    Check if the text is a phone number.
    
    Various phone formats:
    - +91 1234567890
    - +91 123 456 7890
    - 1234567890
    - 123-456-7890
    - (123) 456-7890
    """
    # Remove spaces for checking
    cleaned = text.replace(' ', '')
    
    # Phone patterns
    phone_patterns = [
        r'^\+91\d{10}$',           # +911234567890
        r'^\+91\d{3}\d{3}\d{4}$',  # +911234567890 (with grouping)
        r'^\d{10}$',                # 1234567890
        r'^\d{3}-\d{3}-\d{4}$',    # 123-456-7890
        r'^\(\d{3}\)\d{3}-\d{4}$', # (123)456-7890
        r'^\+\d{10,12}$',          # Generic international format
    ]
    
    for pattern in phone_patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False


def extract_email(text):
    """
    Extract email address from text using regex.
    
    Pattern: r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+.[A-Za-z]{2,}'
    """
    # Use the specified regex pattern (with proper dot escaping)
    email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    match = re.search(email_pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


def extract_phone(text):
    """
    Extract phone number from text.
    
    Detects:
    - 10-digit numbers
    - Formats with spaces or +91
    - Various formats: (123) 456-7890, 123-456-7890, +91 123 456 7890, etc.
    """
    if not text:
        return None
    
    # Pattern to match various phone formats
    # Matches: +91 1234567890, +91 123 456 7890, 1234567890, 123-456-7890, (123) 456-7890
    phone_patterns = [
        r'\+91[\s\-]?\d{10}',  # +91 followed by 10 digits
        r'\+91[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}',  # +91 with spaces
        r'(?:\+?91)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}',  # Optional +91 with various formats
        r'\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}',  # Standard 10-digit formats
        r'\d{10}',  # Plain 10 digits
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(0)
            # Clean up the phone number (remove extra spaces)
            phone = re.sub(r'\s+', ' ', phone).strip()
            return phone
    
    return None


def extract_skills(text):
    """
    Extract skills from text based on predefined skill list.
    
    Features:
    - Case insensitive matching
    - Avoid duplicates
    - Use word boundaries to avoid partial matches
    """
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = set()  # Use set to avoid duplicates
    
    for skill in SKILL_LIST:
        # Use word boundary to avoid partial matches
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)
    
    # Return as sorted list
    return sorted(list(found_skills))


def detect_sections(text):
    """
    Identify sections by keywords and extract content under each heading.
    
    Sections detected:
    - Education, Skills, Projects, Certifications, Experience
    
    Returns:
    - Dictionary with section names as keys and content as values
    """
    if not text:
        return {}
    
    sections = {}
    lines = text.split('\n')
    
    current_section = None
    current_content = []
    
    # Create lowercase version of keywords for matching
    keywords_lower = [kw.lower() for kw in SECTION_KEYWORDS]
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Remove common prefixes like "1.", "2.", "-", "*" from section detection
        clean_line = re.sub(r'^[\d\.\-\*\•]+\s*', '', line_stripped).strip()
        clean_line_lower = clean_line.lower()
        
        # Check if this is a section keyword (case-insensitive matching)
        is_section = False
        matched_keyword = None
        
        for i, keyword_lower in enumerate(keywords_lower):
            # Match exact keyword or keyword followed by colon, dash, or space
            if (clean_line_lower == keyword_lower or 
                clean_line_lower.startswith(keyword_lower + ':') or
                clean_line_lower.startswith(keyword_lower + ' -') or
                clean_line_lower.startswith(keyword_lower + ' ')):
                is_section = True
                matched_keyword = SECTION_KEYWORDS[i]  # Use original casing
                break
        
        if is_section:
            # Save previous section if exists
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)
            # Start new section with proper casing
            current_section = matched_keyword
            current_content = []
        elif current_section:
            # Add line to current section
            current_content.append(line_stripped)
    
    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content)
    
    return sections


def parse_resume(filepath, filename):
    """Main function to parse resume and extract information"""
    # Extract text based on file extension
    if filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(filepath)
    elif filename.lower().endswith('.docx'):
        text = extract_text_from_docx(filepath)
    elif filename.lower().endswith('.png'):
        text = extract_text_from_png(filepath)
    else:
        return None
    
    # Extract structured data
    name = extract_name(text)
    email = extract_email(text)
    phone = extract_phone(text)
    skills = extract_skills(text)
    
    # Detect sections (optional - can be used for more detailed parsing)
    sections = detect_sections(text)
    
    return {
        'filename': filename,
        'name': name,
        'email': email,
        'phone': phone,
        'skills': skills,
        'sections': sections,
        'text_preview': text[:500] + "..." if len(text) > 500 else text
    }


def create_upload_folder():
    """Create uploads folder if it doesn't exist"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)


@app.route('/')
def index():
    """Render the home page"""
    return render_template('home.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Render the upload page or handle file upload"""
    if request.method == 'POST':
        return upload_file()
    return render_template('upload.html')


@app.route('/search')
def search():
    """Search candidates by name/email or skill filter
    
    - If no search input: Display all candidates
    - If searching by name or email: Use case-insensitive partial matching
    - If filtering by skill: Use case-insensitive matching
    - If both are applied: Combine conditions with AND logic
    """
    # Get search query and selected skill from URL parameters
    query = request.args.get('query', '').strip()
    selected_skill = request.args.get('skill', '').strip()
    
    # Debug print statements
    print("Selected Skill:", selected_skill)
    
    # Get all candidates from database with search and skill filter
    # If no search input is given, it will return all candidates
    candidates_list, total_count = database.get_all_candidates(
        search=query,
        skill=selected_skill,
        sort_by='upload_date',
        order='desc',
        page=1,
        per_page=50
    )
    
    # Debug print statement to check number of results
    print("Results count:", len(candidates_list))
    
    return render_template(
        'search.html',
        candidates=candidates_list,
        search_query=query,
        skill_filter=selected_skill,
        total_count=total_count
    )


@app.route('/analytics')
def analytics():
    """Render the analytics page with candidate statistics and HR recommendations"""
    
    # Job requirements for HR matching
    job_requirements = ["python", "sql", "machine learning", "flask"]
    
    # Get all candidates from database
    all_candidates, total_candidates = database.get_all_candidates(
        search='',
        sort_by='upload_date',
        order='desc',
        page=1,
        per_page=1000
    )
    
    # Calculate total unique skills
    all_skills = set()
    skill_counts = {}
    
    for candidate in all_candidates:
        if candidate.get('skills'):
            skills = candidate['skills'].split(',')
            for skill in skills:
                skill = skill.strip().lower()
                if skill:
                    all_skills.add(skill)
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    total_unique_skills = len(all_skills)
    
    # Find most common skill
    most_common_skill = None
    if skill_counts:
        most_common_skill = max(skill_counts.items(), key=lambda x: x[1])
    
    # Skill distribution for chart (top 10) - as a sorted list for template
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    top_skills = sorted_skills[:10]
    skill_distribution = dict(top_skills)
    
    # HR Recommendation - Calculate matching scores
    hr_recommendations = []
    
    for candidate in all_candidates:
        if candidate.get('skills'):
            candidate_skills = set(s.strip().lower() for s in candidate['skills'].split(',') if s.strip())
            matching_skills = candidate_skills.intersection(set(job_requirements))
            match_percentage = (len(matching_skills) / len(job_requirements)) * 100
            
            hr_recommendations.append({
                'name': candidate.get('name', 'Unknown'),
                'match_percentage': round(match_percentage, 1),
                'matching_skills': list(matching_skills)
            })
    
    # Sort by match percentage and get top 3
    hr_recommendations.sort(key=lambda x: x['match_percentage'], reverse=True)
    top_recommendations = hr_recommendations[:3]
    
    # Prepare chart data
    chart_labels = list(skill_distribution.keys())
    chart_data = list(skill_distribution.values())
    
    return render_template(
        'analytics.html',
        total_candidates=total_candidates,
        total_unique_skills=total_unique_skills,
        most_common_skill=most_common_skill,
        skill_distribution=skill_distribution,
        top_skills=top_skills,
        chart_labels=chart_labels,
        chart_data=chart_data,
        job_requirements=job_requirements,
        top_recommendations=top_recommendations
    )


def upload_file():
    """Handle file upload and parsing with comprehensive error handling"""
    # Ensure upload folder exists
    create_upload_folder()
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected. Please choose a file to upload.', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            flash('No file selected. Please choose a file to upload.', 'error')
            return redirect(url_for('index'))
        
        # Get original filename and sanitize it for security (prevent path traversal)
        original_filename = file.filename
        filename = os.path.basename(original_filename)
        
        # Check file extension (allow pdf, docx, and png)
        if not allowed_file(filename):
            flash('Invalid file type! Only PDF, DOCX, and PNG files are allowed.', 'error')
            return redirect(url_for('index'))
        
        # Check file size before saving (large file handling)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()  # Get file size
        file.seek(0)  # Reset to beginning
        
        max_size = 16 * 1024 * 1024  # 16MB
        if file_size > max_size:
            flash(f'File too large! Maximum file size is 16MB. Your file is {file_size / (1024*1024):.2f}MB.', 'error')
            return redirect(url_for('index'))
        
        if file_size == 0:
            flash('Empty file uploaded. Please upload a valid resume.', 'error')
            return redirect(url_for('index'))
        
        # Create safe filepath
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the uploaded file
        file.save(filepath)
        
        # Parse the resume
        result = parse_resume(filepath, filename)
        
        if result is None:
            flash('Error: Could not extract text from file. Please ensure the file is not corrupted.', 'error')
            return redirect(url_for('index'))
        
        # Clean up - remove uploaded file after processing
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Render result page
        return render_template('result.html', result=result)
        
    except IOError as e:
        flash(f'Error reading file: {str(e)}', 'error')
        return redirect(url_for('index'))
    except MemoryError as e:
        flash('File is too large to process. Please upload a smaller file.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files (if needed for viewing)"""
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================
# Candidates Routes
# ============================================

@app.route('/candidates')
def candidates():
    """Display all candidates with pagination, sorting, and search"""
    # Get query parameters
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'upload_date')
    order = request.args.get('order', 'desc')
    page = int(request.args.get('page', 1))
    per_page = 10
    
    # Validate sort parameters
    if sort_by not in ['name', 'upload_date']:
        sort_by = 'upload_date'
    if order not in ['asc', 'desc']:
        order = 'desc'
    
    # Get candidates from database
    candidates_list, total_count = database.get_all_candidates(
        search=search, 
        sort_by=sort_by, 
        order=order, 
        page=page, 
        per_page=per_page
    )
    
    # Calculate pagination
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template(
        'candidates.html',
        candidates=candidates_list,
        search=search,
        sort_by=sort_by,
        order=order,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@app.route('/candidate/<int:candidate_id>')
def candidate_detail(candidate_id):
    """Display detailed candidate profile"""
    candidate = database.get_candidate_by_id(candidate_id)
    
    if candidate is None:
        flash('Candidate not found!', 'error')
        return redirect(url_for('candidates'))
    
    # Convert skills string to list
    skills_list = candidate['skills'].split(',') if candidate['skills'] else []
    
    return render_template(
        'candidate_detail.html',
        candidate=candidate,
        skills_list=skills_list
    )


@app.route('/candidate/edit/<int:candidate_id>', methods=['GET', 'POST'])
def candidate_edit(candidate_id):
    """Edit candidate details"""
    candidate = database.get_candidate_by_id(candidate_id)
    
    if candidate is None:
        flash('Candidate not found!', 'error')
        return redirect(url_for('candidates'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        skills = request.form.get('skills', '')
        
        # Convert skills string to list
        skills_list = [s.strip() for s in skills.split(',') if s.strip()]
        
        # Update candidate
        database.update_candidate(candidate_id, name, email, phone, skills_list)
        
        flash('Candidate updated successfully!', 'success')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    
    # Convert skills string to list for display
    skills_list = candidate['skills'].split(',') if candidate['skills'] else []
    
    return render_template(
        'candidate_form.html',
        candidate=candidate,
        skills_list=skills_list,
        action='edit'
    )


@app.route('/candidate/delete/<int:candidate_id>', methods=['POST'])
def candidate_delete(candidate_id):
    """Delete a candidate"""
    candidate = database.get_candidate_by_id(candidate_id)
    
    if candidate is None:
        flash('Candidate not found!', 'error')
        return redirect(url_for('candidates'))
    
    # Delete candidate
    database.delete_candidate(candidate_id)
    
    flash('Candidate deleted successfully!', 'success')
    return redirect(url_for('candidates'))


@app.route('/save_candidate', methods=['POST'])
def save_candidate():
    """Save a candidate from the result page"""
    # Get data from form
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    skills = request.form.get('skills', '')
    filename = request.form.get('filename', '')
    text_preview = request.form.get('text_preview', '')
    
    # Convert skills string to list
    skills_list = skills.split(',') if skills else []
    
    # Save to database
    candidate_id = database.add_candidate(
        name=name,
        email=email,
        phone=phone,
        skills=skills_list,
        filename=filename,
        text_preview=text_preview
    )
    
    flash(f'Candidate saved successfully!', 'success')
    return redirect(url_for('candidate_detail', candidate_id=candidate_id))


if __name__ == '__main__':
    # Create uploads folder
    create_upload_folder()
    
    # Initialize database
    database.init_database()
    
    # Run the Flask application
    print("=" * 50)
    print("AI Resume Parser Application")
    print("=" * 50)
    print("Server running at: http://127.0.0.1:5000")
    print("Open this URL in your browser to use the application")
    print("=" * 50)
    
    app.run(debug=True)
