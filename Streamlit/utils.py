# utils.py
import streamlit as st
import cv2
from PIL import Image
from json import load
import base64
import logging
import gc
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load RTSP URLs
try:
    with open('./rtsp.json', 'r') as file:
        rtsp_list = load(file)
except FileNotFoundError as fnf_error:
    logger.error(f"RTSP file not found: {fnf_error}")
    st.error("Error: The RTSP configuration file was not found.")
except Exception as e:
    logger.error(f"Error loading RTSP file: {e}")
    st.error(f"Error loading RTSP configuration file: {e}")

@st.cache_resource
def add_gif(gif_path):
    """Read a GIF file and return as a base64 encoded string."""
    try:
        with open(gif_path, "rb") as file_:
            contents = file_.read()
            data_url = base64.b64encode(contents).decode("utf-8")
        return f'data:image/gif;base64,{data_url}'
    except Exception as e:
        st.error(f"Error loading GIF: {e}")
        return None

def init_page_config():
    """Initialize the Streamlit page configuration."""
    st.set_page_config(
        page_title="AI Smart Camera",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}

        [data-testid="stSidebarNav"] {
            position: absolute;
            width: 100%;
            margin-top: 220px;
        }

        [data-testid="stSidebarNav"] ul {
            padding-top: 10px;
        }
        </style>
    """
    st.markdown(init_style, unsafe_allow_html=True)

@st.cache_resource
def add_logo(logo_path):
    """Load a logo image."""
    try:
        logo = Image.open(logo_path)
        return logo
    except Exception as e:
        st.error(f"Error loading logo: {e}")
        return None

def rtsp_connect(url):
    """Attempt to connect to an RTSP stream with retries."""
    attempts = 0
    cap = None
    while attempts < 5 and (cap is None or not cap.isOpened()):
        cap = cv2.VideoCapture(url.replace('subtype=00','subtype=01'), cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
        if not cap.isOpened():
            logger.warning(f"RTSP connection attempt {attempts + 1} failed. Retrying...")
            st.warning(f"Attempt {attempts + 1}: Unable to connect to RTSP stream. Retrying...")
            attempts += 1
            time.sleep(5)
        else:
            logger.info("Connected to RTSP stream.")
            return cap
    return cap

def rtsp_live(url):
    """Display live video stream from an RTSP source."""
    st_frame = st.empty()
    loading_gif = add_gif('./logo/loading.gif')
    if loading_gif:
        st_frame.markdown(
            f'<img src="{loading_gif}" alt="loading gif">',
            unsafe_allow_html=True
        )

    cap = rtsp_connect(url)
    if cap is None or not cap.isOpened():
        st.error("Error: Unable to connect to the RTSP stream.")
        return

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                st_frame.image(
                    frame,
                    caption='RTSP Live',
                    channels="BGR",
                    use_column_width=True
                )
            else:
                logger.warning("Failed to read frame. Retrying...")
                cap.release()
                cap = rtsp_connect(url)
                continue

    except cv2.error as cv_error:
        st.error(f"OpenCV error: {cv_error}")
        logger.error(f"OpenCV error: {cv_error}")
    except Exception as e:
        st.error(f"Error loading video: {str(e)}")
        logger.error(f"Error loading video: {str(e)}")
    finally:
        if cap:
            cap.release()
        n_gc = gc.collect()
        logger.info(f"Video capture released and {n_gc} garbage collected.")

