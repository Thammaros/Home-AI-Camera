from json import load
import httpx, cv2, os, aiofiles
import numpy as np
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
from fastapi import HTTPException, Header
from fastapi.concurrency import run_in_threadpool

# Load RTSP URLs from JSON file
with open('rtsp.json', 'r') as file:
    rtsp_list = load(file)

# Environment variables and headers
line_headers = {'Authorization': 'Bearer ' + os.getenv('LINE_TOKEN', '')}
notification_rate = float(os.getenv('NOTIFICATION_RATE', 30))  # Default to 30 minutes if not set
last_send = dict()

# Verify if the user is authorized
def verify_user(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Bearer"})
    camera_id = authorization.split("Bearer ")[1]
    if camera_id not in rtsp_list['RTSP_URL'].keys():
        raise HTTPException(status_code=401, detail=f"{camera_id} Unauthorized", headers={"WWW-Authenticate": "Bearer"})
    return camera_id

# Send notification with an image to LINE Notify
async def line_notify_with_image_array(message="", image_array=None):
    payload = {'message': message}
    success, image_encoded = cv2.imencode('.jpg', image_array)
    if success:
        image_bytes = image_encoded.tobytes()
        image_file = {'imageFile': image_bytes}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://notify-api.line.me/api/notify",
                    headers=line_headers,
                    data=payload,
                    files=image_file
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                print(f"Failed to send LINE notification: {e}")

# Process an image and return the processed frame
def process_image_block(camera_id, time_now, content):
    pil_image = Image.open(BytesIO(content))
    frame = np.array(pil_image)
    frame_stream = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    frame_stream = cv2.putText(
        frame_stream,
        time_now + f" {camera_id}",
        (int(frame_stream.shape[1] * 0.02), int(frame_stream.shape[0] * 0.06)),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
        3
    )

    # Create directory if not exists
    os.makedirs(f'static/{camera_id}', exist_ok=True)

    if camera_id not in last_send:
        last_send[camera_id] = "2000-01-01 00:00:00"

    cv2.imwrite(f"./static/{camera_id}/{time_now}.jpg".replace(' ', '_'), frame_stream)
    return frame_stream

# Asynchronous wrapper for process_image_block
async def process_image(camera_id, time_now, content):
    frame_stream = await run_in_threadpool(process_image_block, camera_id, time_now, content)
    if (datetime.strptime(time_now, '%Y-%m-%d %H:%M:%S') - datetime.strptime(last_send[camera_id], '%Y-%m-%d %H:%M:%S')) >= timedelta(minutes=notification_rate):
        last_send[camera_id] = time_now
        await line_notify_with_image_array(image_array=frame_stream, message=f'{camera_id} Alert.')

# Asynchronously write bytes to a file
async def write_file(filename: str, data: bytes):
    async with aiofiles.open(filename, mode='wb') as file:
        await file.write(data)

# Process a video and save it to the logs
async def process_video(camera_id, time_now, content, file_type):
    os.makedirs(f'static/{camera_id}', exist_ok=True)
    await write_file(f"static/{camera_id}/{time_now}.{file_type}".replace(' ', '_'), content)
