UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class TranslationJob(BaseModel):
    job_id: str
    status: str
    filename: str
    target_lang: str
    output_location: Optional[str] = None
    error: Optional[str] = None

# Mock database for now
# In a real app, use a proper DB (Supabase/Postgres)
jobs = {}

@router.post("/upload", response_model=TranslationJob)
async def upload_file(
    target_lang: str,
    background_tasks: BackgroundTasks,
    model: str = "gpt-4o",
    tone: str = "formal",
    file: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    file_location = f"{UPLOAD_DIR}/{job_id}_{file.filename}"
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "filename": file.filename,
        "location": file_location,
        "target_lang": target_lang,
        "output_location": None,
        "error": None
    }
    
    # Trigger background translation
    background_tasks.add_task(
        process_translation, 
        job_id, 
        file_location, 
        target_lang, 
        jobs,
        model,
        tone
    )
    
    return jobs[job_id]

@router.get("/download/{job_id}")
async def download_translation(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Translation not ready")
        
    output_path = job.get("output_location")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        output_path, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
        filename=os.path.basename(output_path)
    )

@router.get("/jobs/{job_id}", response_model=TranslationJob)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Optional: Delete files associated with the job
    job = jobs[job_id]
    if job.get("location") and os.path.exists(job["location"]):
        try:
            os.remove(job["location"])
        except:
            pass
    if job.get("output_location") and os.path.exists(job["output_location"]):
        try:
            os.remove(job["output_location"])
        except:
            pass
            
    del jobs[job_id]
    return {"status": "success"}
