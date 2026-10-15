"""
Database module for AI Resume Parser
Handles SQLite database operations for candidate management
"""

import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = 'candidates.db'


def get_db_connection():
    """Get a database connection with proper error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise


def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create candidates table with exact structure as specified
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            skills TEXT,
            upload_date TEXT,
            filename TEXT,
            text_preview TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def add_candidate(name, email, phone, skills, filename='', text_preview=''):
    """Add a new candidate to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Convert skills list to string
    skills_str = ','.join(skills) if isinstance(skills, list) else skills
    
    # Get current timestamp
    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO candidates (name, email, phone, skills, upload_date, filename, text_preview)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, phone, skills_str, upload_date, filename, text_preview))
    
    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return candidate_id


def get_all_candidates(search='', skill='', sort_by='upload_date', order='desc', page=1, per_page=10):
    """Get all candidates with optional search, skill filter, sorting, and pagination
    
    Args:
        search: Search text for name or email (case-insensitive partial match)
        skill: Filter by skill (case-insensitive partial match)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query based on search filter and skill filter
    query = 'SELECT * FROM candidates WHERE 1=1'
    params = []
    
    # Handle search text (name or email) - case-insensitive partial matching
    if search:
        # Use LIKE with lowercase for case-insensitive matching
        query += ' AND (LOWER(name) LIKE ? OR LOWER(email) LIKE ?)'
        search_param = f'%{search.lower()}%'
        params.extend([search_param, search_param])
    
    # Handle skill filter - case-insensitive partial matching
    if skill:
        # Skills are stored as comma-separated string, use LIKE for partial match
        query += ' AND LOWER(skills) LIKE ?'
        skill_param = f'%{skill.lower()}%'
        params.append(skill_param)
    
    # Add sorting
    if sort_by == 'name':
        query += ' ORDER BY name'
    elif sort_by == 'upload_date':
        query += ' ORDER BY upload_date'
    else:
        query += ' ORDER BY upload_date'
    
    # Add order direction
    if order == 'asc':
        query += ' ASC'
    else:
        query += ' DESC'
    
    # Get total count for pagination
    count_query = query.replace('SELECT *', 'SELECT COUNT(*) as count')
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']
    
    # Add pagination with LIMIT and OFFSET
    offset = (page - 1) * per_page
    query += f' LIMIT {per_page} OFFSET {offset}'
    
    cursor.execute(query, params)
    candidates = cursor.fetchall()
    conn.close()
    
    # Convert rows to dictionaries
    candidates_list = [dict(row) for row in candidates]
    
    return candidates_list, total_count


def get_candidate_by_id(candidate_id):
    """Get a candidate by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    candidate = cursor.fetchone()
    conn.close()
    
    if candidate:
        return dict(candidate)
    return None


def update_candidate(candidate_id, name, email, phone, skills):
    """Update a candidate's information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Convert skills list to string
    skills_str = ','.join(skills) if isinstance(skills, list) else skills
    
    cursor.execute('''
        UPDATE candidates
        SET name = ?, email = ?, phone = ?, skills = ?
        WHERE id = ?
    ''', (name, email, phone, skills_str, candidate_id))
    
    conn.commit()
    conn.close()


def delete_candidate(candidate_id):
    """Delete a candidate from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM candidates WHERE id = ?', (candidate_id,))
    
    conn.commit()
    conn.close()


def get_total_candidates():
    """Get total number of candidates"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM candidates')
    count = cursor.fetchone()['count']
    conn.close()
    
    return count


def get_all_skills():
    """Get all unique skills from candidates"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT skills FROM candidates WHERE skills IS NOT NULL AND skills != ""')
    rows = cursor.fetchall()
    conn.close()
    
    # Extract and deduplicate skills
    all_skills = set()
    for row in rows:
        if row['skills']:
            for skill in row['skills'].split(','):
                skill = skill.strip()
                if skill:
                    all_skills.add(skill)
    
    return sorted(list(all_skills))


def get_skill_distribution():
    """Get distribution of skills across all candidates"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT skills FROM candidates WHERE skills IS NOT NULL AND skills != ""')
    rows = cursor.fetchall()
    conn.close()
    
    # Count skills
    skill_counts = {}
    for row in rows:
        if row['skills']:
            for skill in row['skills'].split(','):
                skill = skill.strip()
                if skill:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    # Sort by count and return
    return dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True))


def get_candidates_by_month(months=6):
    """Get number of candidates uploaded by month for the last N months"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    
    # Get date N months ago
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months*30)
    
    cursor.execute('''
        SELECT strftime('%Y-%m', upload_date) as month, COUNT(*) as count
        FROM candidates
        WHERE upload_date >= ?
        GROUP BY month
        ORDER BY month
    ''', (start_date.strftime('%Y-%m-%d'),))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{'month': row['month'], 'count': row['count']} for row in rows]


def get_top_skills(limit=10):
    """Get top N most common skills"""
    distribution = get_skill_distribution()
    sorted_skills = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
    return sorted_skills[:limit]
