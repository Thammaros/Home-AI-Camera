from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
from utils import verify_user, process_video, process_image 

app = FastAPI(
    redoc_url=None,
    docs_url=None
)

# CORS settings - Adjust the allow_origins list as per your requirements
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST"],
)

@app.post("/logs")
async def upload_file(fileToUpload: UploadFile, background_tasks: BackgroundTasks, camera_id=Depends(verify_user, use_cache=False)):
    # Log the current time in a specific timezone
    time_now = datetime.now(tz=timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S')

    # Allowed file extensions
    allowed_extensions = {'mp4', 'mov', 'jpg', 'png', 'jpeg'}
    file_type = fileToUpload.filename.split(".")[-1].lower()

    # Check if the file extension is allowed
    if file_type in allowed_extensions:
        # Read the uploaded file's content
        content = await fileToUpload.read()

        # Process based on the file type
        if file_type in {'mp4', 'mov'}:
            await process_video(camera_id, time_now, content, file_type)
        elif file_type in {'jpg', 'png', 'jpeg'}:
            background_tasks.add_task(process_image, camera_id, time_now, content)
        return {"message": f"File {fileToUpload.filename} uploaded successfully"}

    # Raise an HTTP exception if the file type is not supported
    raise HTTPException(status_code=415, detail=f"{camera_id}: Unsupported file type ({file_type})")
