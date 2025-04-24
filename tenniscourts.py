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

# Path to the CSV file for persistent storage
DATA_FILE = "issues.csv"

# Function to load issues from CSV
def load_issues():
    try:
        if os.path.exists(DATA_FILE):
            # Check if file is empty
            if os.path.getsize(DATA_FILE) == 0:
                logger.warning(f"{DATA_FILE} exists but is empty")
                return pd.DataFrame(columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter'])
            # Read CSV and convert photo_path NaN to None
            df = pd.read_csv(DATA_FILE)
            df['photo_path'] = df['photo_path'].replace({np.nan: None})
            if df.empty and not os.path.getsize(DATA_FILE) == 0:
                logger.warning(f"{DATA_FILE} has no valid data, initializing empty DataFrame")
                return pd.DataFrame(columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter'])
            logger.info(f"Loaded {len(df)} issues from {DATA_FILE}")
            # Ensure all required columns exist
            required_columns = ['id', 'date', 'court', 'problem', 'photo_path', 'reporter']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            return df
        else:
            logger.info(f"No {DATA_FILE} found, initializing empty DataFrame")
            return pd.DataFrame(columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter'])
    except pd.errors.EmptyDataError:
        logger.warning(f"{DATA_FILE} is empty or malformed, returning empty DataFrame")
        return pd.DataFrame(columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter'])
    except Exception as e:
        logger.error(f"Error loading issues from {DATA_FILE}: {str(e)}")
        st.error(f"Failed to load issues: {str(e)}")
        return pd.DataFrame(columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter'])

# Function to save issues to CSV
def save_issues(df):
    try:
        os.makedirs(os.path.dirname(DATA_FILE) or '.', exist_ok=True)  # Ensure directory exists
        # Validate DataFrame before saving
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Input is not a pandas DataFrame")
        if not all(col in df.columns for col in ['id', 'date', 'court', 'problem', 'photo_path', 'reporter']):
            raise ValueError("DataFrame missing required columns")
        # Ensure photo_path is string or None
        df['photo_path'] = df['photo_path'].replace({np.nan: None})
        df.to_csv(DATA_FILE, index=False)
        # Verify file was written
        if os.path.exists(DATA_FILE):
            file_size = os.path.getsize(DATA_FILE)
            logger.info(f"Saved {len(df)} issues to {DATA_FILE} (size: {file_size} bytes)")
            # Read back to ensure it's valid
            pd.read_csv(DATA_FILE)
        else:
            raise FileNotFoundError(f"{DATA_FILE} was not created")
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
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main app function
def main():
    st.title("Tennis Court Issue Tracker")

    # Dubai timezone
    dubai_tz = pytz.timezone('Asia/Dubai')

    # Form for reporting new issues
    with st.form("issue_form"):
        st.subheader("Report a New Issue")
        court = st.selectbox("Court Name", COURTS)
        problem = st.text_area("Problem Description")
        photo = st.file_uploader("Upload Photo (optional)", type=['png', 'jpg', 'jpeg'])
        reporter = st.text_input("Your Name")
        submit_button = st.form_submit_button("Submit Issue")

        if submit_button:
            if court and problem and reporter:
                photo_path = save_photo(photo)
                new_issue = pd.DataFrame({
                    'id': [str(uuid.uuid4())],
                    'date': [datetime.now(dubai_tz).strftime("%Y-%m-%d %H:%M:%S")],
                    'court': [court],
                    'problem': [problem],
                    'photo_path': [photo_path],
                    'reporter': [reporter]
                })
                st.session_state.issues = pd.concat(
                    [st.session_state.issues, new_issue], 
                    ignore_index=True
                )
                save_issues(st.session_state.issues)  # Save to CSV
                logger.debug(f"Added new issue, total issues: {len(st.session_state.issues)}")
                st.success("Issue reported successfully!")
            else:
                st.error("Please fill in all required fields (Court, Problem, Name)")

    # Download options
    st.subheader("Download Issues")
    if not st.session_state.issues.empty:
        # CSV Download
        csv = st.session_state.issues.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="tennis_court_issues.csv",
            mime="text/csv"
        )

        # Excel Download
        excel_buffer = io.BytesIO()
        st.session_state.issues.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button(
            label="Download as Excel",
            data=excel_buffer,
            file_name="tennis_court_issues.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # PDF Download
        pdf_buffer = generate_pdf(st.session_state.issues)
        st.download_button(
            label="Download as PDF",
            data=pdf_buffer,
            file_name="tennis_court_issues.pdf",
            mime="application/pdf"
        )
    else:
        st.info("No issues to download.")

    # Display reported issues
    st.subheader("Reported Issues")
    if not st.session_state.issues.empty:
        for idx, row in st.session_state.issues.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
            
            with col1:
                st.write(row['date'])
            
            with col2:
                st.write(row['court'])
            
            with col3:
                st.write(row['problem'])
            
            with col4:
                thumbnail = get_thumbnail(row['photo_path'])
                if thumbnail:
                    st.image(
                        f"data:image/png;base64,{thumbnail}",
                        caption="Click to view full size",
                        use_container_width=True
                    )
                    if st.button("View Full Size", key=f"view
