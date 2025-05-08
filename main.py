from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import httpx
from typing import List, Optional
import os

app = FastAPI()

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Placeholder for conversation context
conversation_history: List[dict] = []

# Configuration for LLM APIs (replace with actual endpoints and keys)
LLM_API_1_URL = "https://api.example.com/llm1"
LLM_API_2_URL = "https://api.example.com/llm2"
API_KEY_1 = "your_api_key_llm1"
API_KEY_2 = "your_api_key_llm2"

async def call_llm(api_url: str, api_key: str, prompt: str) -> str:
    """
    Call an LLM API with the given prompt.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "max_tokens": 150
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def get_home():
    """
    Serve the main HTML page.
    """
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/chat/")
async def chat_endpoint(request: Request):
    """
    Handle chat messages from the frontend.
    """
    data = await request.json()
    user_message: str = data.get("message", "")
    theme: Optional[str] = data.get("theme", "default")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required.")
    # Append user message to history
    conversation_history.append({"role": "user", "content": user_message})
    # Prepare prompt with context
    prompt = f"Theme: {theme}\n"
    for msg in conversation_history:
        role = msg["role"]
        content = msg["content"]
        prompt += f"{role.capitalize()}: {content}\n"
    # Call LLMs
    try:
        response_llm1 = await call_llm(LLM_API_1_URL, API_KEY_1, prompt)
        response_llm2 = await call_llm(LLM_API_2_URL, API_KEY_2, prompt)
    except HTTPException as e:
        return JSONResponse(status_code=500, content={"error": str(e.detail)})
    # Append assistant responses
    conversation_history.append({"role": "assistant", "content": response_llm1})
    conversation_history.append({"role": "assistant", "content": response_llm2})
    return {
        "response_llm1": response_llm1,
        "response_llm2": response_llm2
    }

@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Handle file uploads (text or images).
    """
    saved_files = []
    for file in files:
        try:
            filename = file.filename
            save_path = os.path.join("uploads", filename)
            os.makedirs("uploads", exist_ok=True)
            with open(save_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            saved_files.append(filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save {file.filename}: {str(e)}")
    return {"uploaded_files": saved_files}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)