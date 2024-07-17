from utils import *
import os
import gc
import streamlit as st

@st.cache_resource(ttl=60)
def fetch_files(static_dir, extensions):
    """Fetch files from the static directory based on given extensions using caching."""
    return [
        os.path.join(static_dir, x) for x in os.listdir(static_dir)
        if x.split('.')[-1].lower() in extensions
    ]

def render_file(file_path, col):
    """Render a single file (image/video) into the provided Streamlit column."""
    extension = os.path.splitext(file_path)[1].lower()
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        col.error(f"File not found: {file_path}")
        return
    file_title = os.path.basename(file_path).split('.')[0].replace('_', ' ')
    if extension in ['.jpg', '.jpeg', '.png']:
        col.image(file_path)
    elif extension in ['.mp4', '.mov']:
        col.video(file_path)
    col.markdown(f"<p style='font-size:20px;'>{file_title}</p>", unsafe_allow_html=True)


def render_files(file_paths, num_columns=5):
    """Render a list of files using Streamlit columns."""
    columns = st.columns(num_columns)
    for i, file_path in enumerate(file_paths):
        render_file(file_path, columns[i % num_columns])

def event_report():
    """Generate and display the event report."""
    flex1, flex2, flex3 = st.columns([8, 1, 1])
    flex1.title("📋 Event Report")
    log_img = flex2.checkbox('Image', True)
    log_vid = flex3.checkbox('Video')

    static_dir = os.path.join('static', target_camera)
    if os.path.exists(static_dir):
        extensions = []
        if log_img:
            extensions.extend(['jpg', 'jpeg', 'png'])
        if log_vid:
            extensions.extend(['mp4', 'mov'])

        display_list = sorted(fetch_files(static_dir, extensions), reverse=True)
        render_files(display_list[:50])
    else:
        st.warning(f"No data found for camera: {target_camera}")
    gc.collect()

# Initialize the page config and sidebar
init_page_config()
with st.sidebar:
    st.write('#')
    my_logo = add_logo('./logo/logo.png')
    if my_logo:
        st.sidebar.image(my_logo)
    target_camera = st.sidebar.selectbox("Select Camera", sorted(rtsp_list["RTSP_URL"].keys()), label_visibility="collapsed")

event_report()
