import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Inventory Item Explorer", layout="wide")

st.title("Inventory Item Explorer")

# File selection
DATA_DIR = os.path.join(os.path.dirname(__file__),'..', 'data')
files = [f for f in os.listdir(DATA_DIR) if f.endswith('modified.csv')]

    # --- Centered Start Button and Persistent Activity Log Table ---
import datetime

# Initialize activity log in session state if not present
if 'activity_log' not in st.session_state:
    st.session_state['activity_log'] = []


# --- Start/Restart Button in Sidebar ---
import streamlit as st
import datetime

def clear_all():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.cache_resource.clear()

with st.sidebar:
    st.write("")  # Spacer
    st.write("")
    st.write("")
    # Place button at bottom
    st.markdown("<div style='height:300px'></div>", unsafe_allow_html=True)
    if st.session_state.get('started', False):
        if st.button("Restart", key="restart_btn", use_container_width=True):
            clear_all()
            st.rerun()
    else:
        if st.button("Start", key="start_btn", use_container_width=True):
            job_function = "Main Page"
            if 'activity_log' not in st.session_state:
                st.session_state['activity_log'] = []
            st.session_state['activity_log'].append({
                "job function": job_function,
                "date time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "activity": "Started session",
                "number": len(st.session_state['activity_log']) + 1
            })
            # Duplicate selected logistics dataset file with _user suffix
            import shutil
            selected_file = None
            try:
                # Try to get selected_file from session state or fallback
                if 'selected_file' in st.session_state:
                    selected_file = st.session_state['selected_file']
                else:
                    DATA_DIR = os.path.join(os.path.dirname(__file__),'..', 'data')
                    files = [f for f in os.listdir(DATA_DIR) if f.endswith('modified.csv')]
                    if files:
                        selected_file = files[0]
                if selected_file:
                    src_path = os.path.join(DATA_DIR, selected_file)
                    base, ext = os.path.splitext(selected_file)
                    dst_path = os.path.join(DATA_DIR, f"{base}_user{ext}")
                    shutil.copy(src_path, dst_path)
            except Exception as ex:
                st.warning(f"Could not duplicate file: {ex}")
            st.session_state['started'] = True
            st.rerun()

if st.session_state.get('activity_log'):
    st.markdown("<h3 style='text-align: center;'>User Activity Log</h3>", unsafe_allow_html=True)
    activity_data = pd.DataFrame(st.session_state['activity_log'])
    st.dataframe(activity_data)


st.write(st.session_state)