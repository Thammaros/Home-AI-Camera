import streamlit as st
from utils import *
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Main function for the Streamlit app."""
    try:
        st.title("Interactive Interface for AI Smart Camera")
        rtsp_live(rtsp_list["RTSP_URL"][target_camera])
    except Exception as e:
        st.error(f"Error in main function: {str(e)}")
        logger.error(f"Error in main function: {str(e)}")

# Initialize page configuration
init_page_config()

# Sidebar settings
with st.sidebar:
    st.write('#')
    my_logo = add_logo('./logo/logo.png')
    if my_logo:
        st.sidebar.image(my_logo)
    target_camera = st.sidebar.selectbox(
        "Select Camera",
        sorted(rtsp_list["RTSP_URL"].keys()),
        label_visibility="collapsed"
    )

# Execute main function
if __name__ == '__main__':
    main()
