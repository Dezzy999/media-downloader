"""
YouTube Downloader using yt-dlp
Soporta videos individuales y playlists
Corregido para Windows: usa subprocess.run en lugar de asyncio.create_subprocess_exec
"""

import os
import subprocess
import json
import traceback
from pathlib import Path
from typing import Optional
from datetime import datetime
import re


import httpx

class YouTubeDownloader:
    """Descargador de YouTube usando yt-dlp"""
    
    def __init__(self, downloads_dir: Path):
        self.downloads_dir = downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def get_info(self, url: str) -> dict:
        """Obtener información del video de forma instantánea usando oEmbed"""
        try:
            # YouTube oEmbed API
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            print(f"[YouTube] Consultando oEmbed: {oembed_url}")
            
            response = await self.client.get(oembed_url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "title": data.get("title"),
                    "thumbnail": data.get("thumbnail_url"),
                    "uploader": data.get("author_name"),
                    "author": data.get("author_name")
                }
            
            # Fallback a yt-dlp si oEmbed falla
            print(f"[YouTube] oEmbed falló ({response.status_code}), usando fallback yt-dlp...")
            return await self._get_info_fallback(url)
            
        except Exception as e:
            print(f"[YouTube] Error en oEmbed: {str(e)}, usando fallback...")
            return await self._get_info_fallback(url)

    async def _get_info_fallback(self, url: str) -> dict:
        """Método de respaldo usando yt-dlp"""
        try:
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                "--no-warnings",
                "--flat-playlist",
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0 and result.stdout:
                info = json.loads(result.stdout)
                return {
                    "success": True,
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                    "author": info.get("uploader")
                }
            return {"success": False, "error": "No se pudo obtener información"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    def _get_format_options(self, format: str, quality: str) -> list:
        """Obtener opciones de yt-dlp según formato y calidad"""
        
        quality_map = {
            "128k": "128",
            "192k": "192", 
            "320k": "320",
            "best": "0"
        }
        
        audio_quality = quality_map.get(quality, "192")
        
        if format in ["mp3", "m4a", "wav", "flac"]:
            return [
                "-x",  # Extraer audio
                "--audio-format", format,
                "--audio-quality", audio_quality,
                "--postprocessor-args", "ffmpeg:-threads 4",
            ]
        elif format == "mp4":
            return [
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "--postprocessor-args", "ffmpeg:-threads 4",
            ]
        else:
            return [
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192",
            ]
    
    async def download(self, url: str, format: str = "mp3", quality: str = "320k") -> dict:
        """
        Descargar video/audio de YouTube
        
        Args:
            url: URL del video o playlist de YouTube
            format: Formato de salida (mp3, m4a, wav, flac, mp4)
            quality: Calidad de audio (128k, 192k, 320k)
        
        Returns:
            dict con success, file_path, filename, title, duration
        """
        try:
            print(f"[YouTube] Iniciando descarga: {url}")
            
            # Generar nombre único para evitar conflictos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = str(self.downloads_dir / f"%(title)s_{timestamp}.%(ext)s")
            
            format_opts = self._get_format_options(format, quality)
            
            cmd = [
                "yt-dlp",
                "--no-playlist",
                "-o", output_template,
                "--restrict-filenames",
                "--no-overwrites",
                "--no-warnings",
                "--concurrent-fragments", "10",  # Descarga multihilo
                "--no-check-certificate",
                "--buffer-size", "16K",
                "--geo-bypass",
                "--extractor-args", "youtube:player_client=android",  # Bypass 403
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ] + format_opts + [url]
            
            print(f"[YouTube] Comando: {' '.join(cmd)}")
            
            # Ejecutar yt-dlp con subprocess.run (síncrono pero confiable en Windows)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos max
            )
            
            print(f"[YouTube] Return code: {result.returncode}")
            print(f"[YouTube] stdout: {result.stdout[:500] if result.stdout else 'empty'}")
            print(f"[YouTube] stderr: {result.stderr[:500] if result.stderr else 'empty'}")
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Error desconocido"
                return {
                    "success": False,
                    "error": f"Error de yt-dlp: {error_msg[:300]}"
                }
            
            # Buscar el archivo descargado más reciente
            pattern = f"*_{timestamp}.*"
            downloaded_files = list(self.downloads_dir.glob(pattern))
            
            if not downloaded_files:
                # Buscar cualquier archivo reciente
                all_files = list(self.downloads_dir.glob(f"*.{format}"))
                if all_files:
                    downloaded_files = [max(all_files, key=os.path.getctime)]
            
            if downloaded_files:
                latest_file = downloaded_files[0]
                print(f"[YouTube] Archivo descargado: {latest_file}")
                
                return {
                    "success": True,
                    "file_path": str(latest_file),
                    "filename": latest_file.name,
                    "title": latest_file.stem.replace(f"_{timestamp}", ""),
                    "duration": None
                }
            
            return {
                "success": False,
                "error": "No se encontró el archivo descargado"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout: la descarga tardó demasiado (más de 5 minutos)"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "yt-dlp no está instalado. Instálalo con: pip install yt-dlp"
            }
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[YouTube] Error: {str(e)}")
            print(f"[YouTube] Traceback: {tb}")
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}"
            }
    
    async def download_playlist(self, url: str, format: str = "mp3", quality: str = "320k") -> dict:
        """Descargar playlist completa de YouTube"""
        try:
            output_template = str(self.downloads_dir / "%(playlist_title)s/%(title)s.%(ext)s")
            
            format_opts = self._get_format_options(format, quality)
            
            cmd = [
                "yt-dlp",
                "--yes-playlist",
                "-o", output_template,
                "--restrict-filenames",
                "--no-overwrites",
            ] + format_opts + [url]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos para playlists
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Error desconocido"
                }
            
            return {
                "success": True,
                "message": "Playlist descargada correctamente"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
