#####For local Dev#####
# from dotenv import load_dotenv
# load_dotenv('./.env')
#####For local Dev#####

import os
import signal
import logging
import requests
import cv2
import tempfile
import gc
from json import load
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from ultralytics import YOLO

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Graceful shutdown handler
terminate = False

def signal_handler(signal, frame):
    global terminate
    logger.info("Termination signal received.")
    terminate = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Check required environment variables
required_env_vars = ['ID']
missing_vars = [var for var in required_env_vars if var not in os.environ]
if missing_vars:
    raise ValueError(f"Missing environment variables: {missing_vars}")

# Load RTSP URLs from JSON
try:
    with open('rtsp.json', 'r') as file:
        rtsp_list = load(file)
        RTSP = rtsp_list["RTSP_URL"].get(os.environ['ID'])
    logger.info("Successfully loaded RTSP URL.")
except Exception as e:
    logger.error(f"Error loading RTSP URL from JSON: {e}")
    raise

# Load the model
try:
    model = YOLO('best.engine', task='detect')
    headers = {'Authorization': 'Bearer ' + os.environ['ID']}
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading the model: {e}")
    raise

# Locks for controlling file writing state
img_lock = Lock()
vid_lock = Lock()

# Function to post files to the server
def post_file_to_server(file_data: bytes, file_name: str, content_type: str):
    try:
        files = {'fileToUpload': (file_name, file_data, content_type)}
        response = requests.post('http://api:8000/logs', files=files, headers=headers)
        if response.status_code == 200:
            logger.info(f"Successfully uploaded {file_name} to server.")
        else:
            logger.warning(f"File upload failed with status code {response.status_code} for {file_name}")
    except Exception as e:
        logger.error(f"An error occurred while uploading {file_name}: {e}")

# Function to write images directly to memory and upload
def write_img(frame):
    with img_lock:
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            img_data = img_encoded.tobytes()
            logger.info("Image prepared in-memory.")
            post_file_to_server(img_data, 'tmp.jpg', 'image/jpeg')
        except Exception as e:
            logger.error(f"Error preparing image: {e}")

# Function to write and post videos using separate cap
def write_vid(rtsp_url, fps, width, height):
    with vid_lock:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video_file:
                local_cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                if not local_cap.isOpened():
                    logger.error("Unable to open RTSP stream for video recording.")
                    return
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(temp_video_file.name, fourcc, fps, (width, height), True)

                count = 0
                while count < 10 * fps:  # Record 10 seconds of video
                    ret, frame = local_cap.read()
                    if ret:
                        out.write(frame)
                        count += 1
                    else:
                        logger.error("Failed to read frame from RTSP stream.")
                        break

                out.release()
                local_cap.release()

                # Upload the video file
                with open(temp_video_file.name, 'rb') as f:
                    video_data = f.read()
                    if video_data:
                        post_file_to_server(video_data, 'temp_video.mp4', 'video/mp4')
        except Exception as e:
            logger.error(f"Error preparing video: {e}")
        finally:
            if 'out' in locals():
                out.release()
            if os.path.exists(temp_video_file.name):
                os.unlink(temp_video_file.name)  # Ensure temporary file is deleted

# Main video processing loop
def process_stream():
    cap = cv2.VideoCapture(RTSP, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        logger.error("Unable to connect to the RTSP stream.")
        return  # Exit if we cannot connect to the RTSP stream

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = 0

    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            while not terminate:
                ret, frame = cap.read()
                if ret:
                    frame_count += 1
                    if frame_count % fps == 0:  # Trigger every 1 seconds
                        result = model.predict(
                            frame,
                            device=0,
                            conf=0.75,
                            verbose=False
                        )[0]

                        if len(result.boxes):
                            executor.submit(write_img, frame)
                            executor.submit(write_vid, RTSP, fps, width, height)

                        n_gc = gc.collect()
                        if n_gc:
                            logger.info(f"{n_gc} objects garbage collected.")
                else:
                    logger.warning("Lost connection to RTSP stream. Attempting to reconnect...")
                    cap.release()
                    cap = cv2.VideoCapture(RTSP, cv2.CAP_FFMPEG)
                    if not cap.isOpened():
                        logger.error("Unable to reconnect to the RTSP stream.")
                        break  # Exit loop if reconnecting fails
        except Exception as e:
            logger.error(f"Error during video processing: {e}")
        finally:
            if cap:
                cap.release()
            logger.info("Video capture released.")

if __name__ == "__main__":
    process_stream()
