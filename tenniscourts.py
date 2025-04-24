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

    # Initialize database
    init_db()

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
                save_issues(st.session_state.issues)  # Save to SQLite
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
            mime="text/csv",
            disabled=False
        )

        # Excel Download
        excel_buffer = io.BytesIO()
        st.session_state.issues.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button(
            label="Download as Excel",
            data=excel_buffer,
            file_name="tennis_court_issues.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=False
        )

        # PDF Download
        pdf_buffer = generate_pdf(st.session_state.issues)
        st.download_button(
            label="Download as PDF",
            data=pdf_buffer,
            file_name="tennis_court_issues.pdf",
            mime="application/pdf",
            disabled=False
        )
    else:
        st.download_button(
            label="Download as CSV",
            data="",
            file_name="tennis_court_issues.csv",
            mime="text/csv",
            disabled=True
        )
        st.download_button(
            label="Download as Excel",
            data="",
            file_name="tennis_court_issues.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=True
        )
        st.download_button(
            label="Download as PDF",
            data="",
            file_name="tennis_court_issues.pdf",
            mime="application/pdf",
            disabled=True
        )
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
                    if st.button("View Full Size", key=f"view_{row['id']}"):
                        st.image(row['photo_path'], use_container_width=True)
            
            with col5:
                st.write(row['reporter'])
                col5_1, col5_2 = st.columns(2)
                with col5_1:
                    if st.button("Edit", key=f"edit_{row['id']}"):
                        st.session_state[f"edit_mode_{row['id']}"] = True
                with col5_2:
                    if st.button("Delete", key=f"delete_{row['id']}"):
                        # Remove photo file if exists
                        if row['photo_path'] and isinstance(row['photo_path'], str) and os.path.exists(row['photo_path']):
                            try:
                                os.remove(row['photo_path'])
                                logger.info(f"Deleted photo {row['photo_path']}")
                            except Exception as e:
                                logger.error(f"Error deleting photo {row['photo_path']}: {str(e)}")
                        # Remove issue from dataframe
                        st.session_state.issues = st.session_state.issues[
                            st.session_state.issues['id'] != row['id']
                        ]
                        save_issues(st.session_state.issues)  # Save to SQLite
                        logger.debug(f"Deleted issue, total issues: {len(st.session_state.issues)}")
                        st.rerun()

            # Edit form in an expander
            if st.session_state.get(f"edit_mode_{row['id']}", False):
                with st.expander("Edit Issue", expanded=True):
                    with st.form(f"edit_form_{row['id']}"):
                        edit_court = st.selectbox("Court Name", COURTS, index=COURTS.index(row['court']))
                        edit_problem = st.text_area("Problem Description", value=row['problem'])
                        edit_photo = st.file_uploader("Upload New Photo (optional)", type=['png', 'jpg', 'jpeg'], key=f"edit_photo_{row['id']}")
                        edit_reporter = st.text_input("Your Name", value=row['reporter'])
                        save_button = st.form_submit_button("Save Changes")

                        if save_button:
                            if edit_court and edit_problem and edit_reporter:
                                # Handle photo update
                                new_photo_path = save_photo(edit_photo) if edit_photo else row['photo_path']
                                if edit_photo and row['photo_path'] and isinstance(row['photo_path'], str) and os.path.exists(row['photo_path']):
                                    try:
                                        os.remove(row['photo_path'])
                                        logger.info(f"Deleted old photo {row['photo_path']}")
                                    except Exception as e:
                                        logger.error(f"Error deleting old photo {row['photo_path']}: {str(e)}")
                                
                                # Update the issue in the DataFrame
                                st.session_state.issues.loc[
                                    st.session_state.issues['id'] == row['id'],
                                    ['date', 'court', 'problem', 'photo_path', 'reporter']
                                ] = [
                                    datetime.now(dubai_tz).strftime("%Y-%m-%d %H:%M:%S"),
                                    edit_court,
                                    edit_problem,
                                    new_photo_path,
                                    edit_reporter
                                ]
                                save_issues(st.session_state.issues)  # Save to SQLite
                                st.session_state[f"edit_mode_{row['id']}"] = False
                                logger.debug(f"Updated issue, total issues: {len(st.session_state.issues)}")
                                st.success("Issue updated successfully!")
                                st.rerun()
                            else:
                                st.error("Please fill in all required fields (Court, Problem, Name)")
            
            st.markdown("---")
    else:
        st.info("No issues reported yet.")

if __name__ == "__main__":
    if 'streamlit' not in sys.modules or not hasattr(sys.modules['streamlit'], 'runtime'):
        logger.error("This is a Streamlit app. Run it with: streamlit run tenniscourts.py")
        print("Error: This is a Streamlit app. Please run it using the command:")
        print("    streamlit run tenniscourts.py")
        print("Do NOT run it directly with 'python tenniscourts.py'.")
        sys.exit(1)
    main()
