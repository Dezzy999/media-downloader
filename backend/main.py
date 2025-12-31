"""
Media Downloader API - FastAPI Backend
Soporta: YouTube, Spotify, TikTok (sin watermark)
Production-ready with environment variables and rate limiting
"""

import os
import uuid
import asyncio
import traceback
import time
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
from collections import defaultdict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables
load_dotenv()

from downloaders.youtube import YouTubeDownloader
from downloaders.spotify import SpotifyDownloader
from downloaders.tiktok import TikTokDownloader
from services.agent import MediaAgent

# ==================== CONFIGURATION ====================

# Downloads Directory
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", str(Path(__file__).parent.parent / "downloads")))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Groq API Key (from environment)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    print("⚠️ WARNING: GROQ_API_KEY not set in environment variables!")
media_agent = MediaAgent(GROQ_API_KEY)

# CORS Origins
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS_STR == "*":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]

# Rate Limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


# ==================== RATE LIMITING MIDDLEWARE ====================

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_limit: int = 100, window: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window = window
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        now = time.time()
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        # Add current request
        self.requests[client_ip].append(now)
        
        return await call_next(request)


# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title="Media Downloader API",
    description="API para descargar medios de YouTube, Spotify y TikTok",
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,  # Disable docs in production
    redoc_url="/redoc" if not IS_PRODUCTION else None
)

# Add Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware, requests_limit=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Task storage (in production, use Redis or database)
tasks_db: dict = {}

# Modelos de datos
class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "320k"
    language: str = "es"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    progress: int = 0
    file_id: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

class FormatInfo(BaseModel):
    id: str
    name: str
    extension: str
    description: str

# Instancias de downloaders
youtube_dl = YouTubeDownloader(DOWNLOADS_DIR)
spotify_dl = SpotifyDownloader(DOWNLOADS_DIR)
tiktok_dl = TikTokDownloader(DOWNLOADS_DIR)

# ==================== ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check del servidor"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/formats")
async def get_formats():
    """Obtener formatos de audio/video disponibles"""
    formats = [
        FormatInfo(id="mp3_128", name="MP3 128kbps", extension="mp3", description="Calidad estándar, archivos pequeños"),
        FormatInfo(id="mp3_192", name="MP3 192kbps", extension="mp3", description="Buena calidad"),
        FormatInfo(id="mp3_320", name="MP3 320kbps", extension="mp3", description="Alta calidad"),
        FormatInfo(id="flac", name="FLAC", extension="flac", description="Sin pérdida (lossless)"),
        FormatInfo(id="wav", name="WAV", extension="wav", description="Sin compresión"),
        FormatInfo(id="m4a", name="M4A (AAC)", extension="m4a", description="Buena calidad, compatible con Apple"),
        FormatInfo(id="mp4", name="MP4 Video", extension="mp4", description="Video con audio"),
    ]
    return {"formats": [f.model_dump() for f in formats]}

@app.post("/api/agent/chat")
async def agent_chat(request: ChatRequest):
    """Chat con el Agente de IA"""
    return await media_agent.chat(request.message)

class PreviewRequest(BaseModel):
    url: str
    platform: str  # youtube, spotify, tiktok

class PreviewResponse(BaseModel):
    success: bool
    title: Optional[str] = None
    artist: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    error: Optional[str] = None

@app.post("/api/preview", response_model=PreviewResponse)
async def get_preview(request: PreviewRequest):
    """Obtener información del contenido antes de descargar"""
    try:
        if request.platform == "youtube":
            info = await youtube_dl.get_info(request.url)
            if info.get("success"):
                return PreviewResponse(
                    success=True,
                    title=info.get("title"),
                    thumbnail=info.get("thumbnail"),
                    duration=str(info.get("duration", "")) if info.get("duration") else None
                )
            return PreviewResponse(success=False, error=info.get("error"))
            
        elif request.platform == "spotify":
            info = await spotify_dl.get_info(request.url)
            if info.get("success"):
                return PreviewResponse(
                    success=True,
                    title=info.get("title", "Sin título"),
                    artist=info.get("artist", ""),
                    thumbnail=info.get("thumbnail")
                )
            return PreviewResponse(success=False, error=info.get("error"))
            
        elif request.platform == "tiktok":
            info = await tiktok_dl.get_info(request.url)
            if info.get("success"):
                return PreviewResponse(
                    success=True,
                    title=info.get("title"),
                    artist=info.get("author"),
                    thumbnail=info.get("cover"),
                    duration=str(info.get("duration", "")) if info.get("duration") else None
                )
            return PreviewResponse(success=False, error=info.get("error"))
        
        return PreviewResponse(success=False, error="Plataforma no soportada")
        
    except Exception as e:
        return PreviewResponse(success=False, error=str(e))

@app.post("/api/download/youtube", response_model=TaskResponse)
async def download_youtube(request: DownloadRequest):
    """Iniciar descarga de YouTube"""
    task_id = str(uuid.uuid4())
    
    tasks_db[task_id] = {
        "status": "pending",
        "message": "Iniciando descarga de YouTube...",
        "progress": 0,
        "platform": "youtube",
        "url": request.url,
        "format": request.format,
        "quality": request.quality,
        "created_at": datetime.now().isoformat()
    }
    
    asyncio.create_task(process_youtube_download(task_id, request.url, request.format, request.quality))
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Descarga iniciada"
    )

@app.post("/api/download/spotify", response_model=TaskResponse)
async def download_spotify(request: DownloadRequest):
    """Iniciar descarga de Spotify"""
    task_id = str(uuid.uuid4())
    
    tasks_db[task_id] = {
        "status": "pending",
        "message": "Iniciando descarga de Spotify...",
        "progress": 0,
        "platform": "spotify",
        "url": request.url,
        "format": request.format,
        "created_at": datetime.now().isoformat()
    }
    
    # Usar get_running_loop para obtener el loop actual (Python 3.10+)
    loop = asyncio.get_running_loop()
    loop.create_task(process_spotify_download(task_id, request.url, request.format))
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Descarga de Spotify iniciada"
    )

@app.post("/api/download/tiktok", response_model=TaskResponse)
async def download_tiktok(request: DownloadRequest):
    """Iniciar descarga de TikTok (sin watermark)"""
    task_id = str(uuid.uuid4())
    
    tasks_db[task_id] = {
        "status": "pending",
        "message": "Iniciando descarga de TikTok...",
        "progress": 0,
        "platform": "tiktok",
        "url": request.url,
        "format": request.format,
        "created_at": datetime.now().isoformat()
    }
    
    asyncio.create_task(process_tiktok_download(task_id, request.url, request.format))
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Descarga de TikTok iniciada"
    )

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Obtener estado de una tarea de descarga"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    task = tasks_db[task_id]
    return TaskResponse(
        task_id=task_id,
        status=task["status"],
        message=task["message"],
        progress=task.get("progress", 0),
        file_id=task.get("file_id"),
        filename=task.get("filename"),
        error=task.get("error")
    )

@app.get("/api/files/{file_id}")
async def download_file(file_id: str):
    """Descargar archivo completado"""
    # Buscar archivo en tareas
    for task_id, task in tasks_db.items():
        if task.get("file_id") == file_id:
            file_path = task.get("file_path")
            if file_path and os.path.exists(file_path):
                filename = task.get("filename", "download")
                return FileResponse(
                    path=file_path,
                    filename=filename,
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"'
                    }
                )
    
    raise HTTPException(status_code=404, detail="Archivo no encontrado")

# ==================== BACKGROUND TASKS ====================

async def process_youtube_download(task_id: str, url: str, format: str, quality: str):
    """Procesar descarga de YouTube en background"""
    try:
        tasks_db[task_id]["status"] = "downloading"
        tasks_db[task_id]["message"] = "Descargando de YouTube..."
        tasks_db[task_id]["progress"] = 10
        
        result = await youtube_dl.download(url, format, quality)
        
        if result["success"]:
            file_id = str(uuid.uuid4())
            tasks_db[task_id].update({
                "status": "completed",
                "message": "Descarga completada",
                "progress": 100,
                "file_id": file_id,
                "file_path": result["file_path"],
                "filename": result["filename"],
                "title": result.get("title"),
                "duration": result.get("duration")
            })
        else:
            tasks_db[task_id].update({
                "status": "error",
                "message": "Error en la descarga",
                "error": result.get("error", "Error desconocido")
            })
    except Exception as e:
        tasks_db[task_id].update({
            "status": "error",
            "message": "Error en la descarga",
            "error": str(e)
        })

async def process_spotify_download(task_id: str, url: str, format: str):
    """Procesar descarga de Spotify en background"""
    try:
        print(f"[Main] Iniciando descarga Spotify: {url}")
        tasks_db[task_id]["status"] = "downloading"
        tasks_db[task_id]["message"] = "Descargando de Spotify..."
        tasks_db[task_id]["progress"] = 10
        
        result = await spotify_dl.download(url, format)
        print(f"[Main] Resultado Spotify: {result}")
        
        if result["success"]:
            file_id = str(uuid.uuid4())
            tasks_db[task_id].update({
                "status": "completed",
                "message": "Descarga completada",
                "progress": 100,
                "file_id": file_id,
                "file_path": result["file_path"],
                "filename": result["filename"],
                "title": result.get("title"),
                "artist": result.get("artist")
            })
        else:
            error_msg = result.get("error", "Error desconocido")
            print(f"[Main] Error en resultado Spotify: {error_msg}")
            tasks_db[task_id].update({
                "status": "error",
                "message": "Error en la descarga",
                "error": error_msg
            })
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"[Main] Excepción en Spotify: {error_detail}")
        tasks_db[task_id].update({
            "status": "error",
            "message": "Error en la descarga",
            "error": f"Error: {type(e).__name__}: {str(e)}"
        })

async def process_tiktok_download(task_id: str, url: str, format: str):
    """Procesar descarga de TikTok en background"""
    try:
        tasks_db[task_id]["status"] = "downloading"
        tasks_db[task_id]["message"] = "Descargando de TikTok (sin watermark)..."
        tasks_db[task_id]["progress"] = 10
        
        result = await tiktok_dl.download(url, format)
        
        if result["success"]:
            file_id = str(uuid.uuid4())
            tasks_db[task_id].update({
                "status": "completed",
                "message": "Descarga completada",
                "progress": 100,
                "file_id": file_id,
                "file_path": result["file_path"],
                "filename": result["filename"]
            })
        else:
            tasks_db[task_id].update({
                "status": "error",
                "message": "Error en la descarga",
                "error": result.get("error", "Error desconocido")
            })
    except Exception as e:
        tasks_db[task_id].update({
            "status": "error",
            "message": "Error en la descarga",
            "error": str(e)
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
