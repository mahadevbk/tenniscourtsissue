import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
from PIL import Image
import io
import uuid
import sys
import logging
import numpy as np
import pytz
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define court names
COURTS = [
    "AL MAHRA", "AL REEM 1", "AL REEM 2", "AL REEM 3", "ALMA",
    "ALVORADA 1", "ALVORADA 2", "HATTAN", "MIRADOR", "MIRADOR LA COLLECCION",
    "PALMERA 2", "PALMERA 4", "SAHEEL", "MIRA 2", "MIRA 4",
    "MIRA 5 A", "MIRA 5 B", "MIRA OASIS 1", "MIRA OASIS 2",
    "MIRA OASIS 3 A", "MIRA OASIS 3 B", "MIRA OASIS 3 C",
    "AR2 ROSA", "AR2 PALMA", "AR2 FITNESS FIRST"
]

# Path to the SQLite database
DATA_FILE = "issues.db"

# Initialize SQLite database
def init_db():
    try:
        conn = sqlite3.connect(DATA_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS issues
                     (id TEXT, date TEXT, court TEXT, problem TEXT, photo_path TEXT, reporter TEXT)''')
        conn.commit()
        logger.info(f"Initialized SQLite database at {DATA_FILE}")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        st.error(f"Failed to initialize database: {str(e)}")
    finally:
        conn.close()

# Function to load issues from SQLite
def load_issues():
    try:
        conn = sqlite3.connect(DATA_FILE)
        df = pd.read_sql_query("SELECT * FROM issues", conn)
        df['photo_path'] = df['photo_path'].replace({np.nan: None})
        conn.close()
        if df.empty:
            logger.info(f"No issues found in {DATA_FILE}, returning empty DataFrame")
        else:
            logger.info(f"Loaded {len(df)} issues from {DATA_FILE}")
        return df
    except Exception as e:
        logger.error(f"Error loading issues from {DATA_FILE}: {str(e)}")
        st.error(f"Failed to load issues: {str(e)}")
        return pd.DataFrame(columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter'])

# Function to save issues to SQLite
def save_issues(df):
    try:
        conn = sqlite3.connect(DATA_FILE)
        df['photo_path'] = df['photo_path'].replace({np.nan: None})
        df.to_sql('issues', conn, if_exists='replace', index=False)
        conn.close()
        logger.info(f"Saved {len(df)} issues to {DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving issues to {DATA_FILE}: {str(e)}")
        st.error(f"Failed to save issues: {str(e)}")

# Initialize session state for storing issues
if 'issues' not in st.session_state:
    st.session_state.issues = load_issues()
    logger.debug(f"Initialized session state with {len(st.session_state.issues)} issues")

# Function to save uploaded photo
def save_photo(uploaded_file):
    if uploaded_file is not None:
        try:
            photo_id = str(uuid.uuid4())
            photo_path = f"photos/{photo_id}_{uploaded_file.name}"
            os.makedirs("photos", exist_ok=True)
            with open(photo_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            logger.info(f"Saved photo to {photo_path}")
            return photo_path
        except Exception as e:
            logger.error(f"Error saving photo: {str(e)}")
            st.error(f"Failed to save photo: {str(e)}")
            return None
    return None

# Function to get thumbnail
def get_thumbnail(photo_path, size=(100, 100)):
    if photo_path and isinstance(photo_path, str) and os.path.exists(photo_path):
        try:
            img = Image.open(photo_path)
            img.thumbnail(size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.error(f"Error generating thumbnail for {photo_path}: {str(e)}")
            return None
    logger.debug(f"No thumbnail generated for {photo_path}: invalid path or file does not exist")
    return None

# Function to generate PDF from issues
def generate_pdf(issues_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Tennis Court Issues Report", styles['Title']))
    elements.append(Paragraph(f"Generated on {datetime.now(pytz.timezone('Asia/Dubai')).strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    
    # Table data
    data = [['ID', 'Date', 'Court', 'Problem', 'Photo Path', 'Reporter']]
    for _, row in issues_df.iterrows():
        data.append([
            row['id'][:8] + '...' if isinstance(row['id'], str) else '',
            row['date'],
            row['court'],
            row['problem'][:50] + '...' if isinstance(row['problem'], str) and len(row['problem']) > 50 else row['problem'],
            row['photo_path'] if row['photo_path'] else 'None',
            row['reporter']
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1
