import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
from PIL import Image
import io
import uuid
import sys

# Define court names
COURTS = [
    "AL MAHRA", "AL REEM 1", "AL REEM 2", "AL REEM 3", "ALMA",
    "ALVORADA 1", "ALVORADA 2", "HATTAN", "MIRADOR", "MIRADOR LA COLLECCION",
    "PALMERA 2", "PALMERA 4", "SAHEEL", "MIRA 2", "MIRA 4",
    "MIRA 5 A", "MIRA 5 B", "MIRA OASIS 1", "MIRA OASIS 2",
    "MIRA OASIS 3 A", "MIRA OASIS 3 B", "MIRA OASIS 3 C",
    "AR2 ROSA", "AR2 PALMA", "AR2 FITNESS FIRST"
]

# Initialize session state for storing issues
if 'issues' not in st.session_state:
    st.session_state.issues = pd.DataFrame(
        columns=['id', 'date', 'court', 'problem', 'photo_path', 'reporter']
    )

# Function to save uploaded photo
def save_photo(uploaded_file):
    if uploaded_file is not None:
        photo_id = str(uuid.uuid4())
        photo_path = f"photos/{photo_id}_{uploaded_file.name}"
        os.makedirs("photos", exist_ok=True)
        with open(photo_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return photo_path
    return None

# Function to get thumbnail
def get_thumbnail(photo_path, size=(100, 100)):
    if photo_path and os.path.exists(photo_path):
        img = Image.open(photo_path)
        img.thumbnail(size)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# Main app function
def main():
    st.title("Tennis Court Issue Tracker")

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
                    'date': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    'court': [court],
                    'problem': [problem],
                    'photo_path': [photo_path],
                    'reporter': [reporter]
                })
                st.session_state.issues = pd.concat(
                    [st.session_state.issues, new_issue], 
                    ignore_index=True
                )
                st.success("Issue reported successfully!")
            else:
                st.error("Please fill in all required fields (Court, Problem, Name)")

    # Display reported issues
    st.subheader("Reported Issues")
    # Apply custom CSS for small buttons
    st.markdown(
        """
        <style>
        .small-button > button {
            padding: 2px 8px;
            font-size: 12px;
            min-height: 30px;
            margin: 2px 0;
            width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

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
                if row['photo_path']:
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
                # Compact buttons in a vertical layout
                with st.container():
                    if st.button("Edit", key=f"edit_{row['id']}", help="Edit this issue", type="secondary", use_container_width=True):
                        st.session_state[f"edit_mode_{row['id']}"] = True
                    if st.button("Delete", key=f"delete_{row['id']}", help="Delete this issue", type="secondary", use_container_width=True):
                        # Remove photo file if exists
                        if row['photo_path'] and os.path.exists(row['photo_path']):
                            os.remove(row['photo_path'])
                        # Remove issue from dataframe
                        st.session_state.issues = st.session_state.issues[
                            st.session_state.issues['id'] != row['id']
                        ]
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
                                if edit_photo and row['photo_path'] and os.path.exists(row['photo_path']):
                                    os.remove(row['photo_path'])  # Remove old photo if new one is uploaded
                                
                                # Update the issue in the DataFrame
                                st.session_state.issues.loc[
                                    st.session_state.issues['id'] == row['id'],
                                    ['date', 'court', 'problem', 'photo_path', 'reporter']
                                ] = [
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    edit_court,
                                    edit_problem,
                                    new_photo_path,
                                    edit_reporter
                                ]
                                st.session_state[f"edit_mode_{row['id']}"] = False
                                st.success("Issue updated successfully!")
                                st.rerun()
                            else:
                                st.error("Please fill in all required fields (Court, Problem, Name)")
            
            st.markdown("---")
    else:
        st.info("No issues reported yet.")

if __name__ == "__main__":
    if 'streamlit' not in sys.modules or not hasattr(sys.modules['streamlit'], 'runtime'):
        print("Error: This is a Streamlit app. Please run it using the command:")
        print("    streamlit run tennis_court_issue_tracker.py")
        print("Do NOT run it directly with 'python tennis_court_issue_tracker.py'.")
        sys.exit(1)
    main()
