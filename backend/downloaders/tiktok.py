"""
TikTok Downloader - Sin Watermark
Descarga videos de TikTok sin marca de agua
"""

import os
import asyncio
import httpx
import re
import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class TikTokDownloader:
    """Descargador de TikTok sin watermark"""
    
    def __init__(self, downloads_dir: Path):
        self.downloads_dir = downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # APIs públicas para descarga sin watermark
        self.api_endpoints = [
            "https://www.tikwm.com/api/",
            "https://api.tikmate.app/api/lookup",
        ]
        
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extraer ID del video de una URL de TikTok"""
        patterns = [
            r'tiktok\.com/@[\w.-]+/video/(\d+)',
            r'tiktok\.com/t/(\w+)',
            r'vm\.tiktok\.com/(\w+)',
            r'/video/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _get_video_info_tikwm(self, url: str) -> dict:
        """Obtener info del video usando tikwm API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://www.tikwm.com/api/",
                    data={"url": url, "hd": 1}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        video_data = data.get("data", {})
                        return {
                            "success": True,
                            "video_url": video_data.get("play"),  # Sin watermark
                            "audio_url": video_data.get("music"),
                            "title": video_data.get("title", "TikTok Video"),
                            "author": video_data.get("author", {}).get("nickname"),
                            "cover": video_data.get("cover"),
                            "duration": video_data.get("duration")
                        }
                
                return {"success": False, "error": "API tikwm no respondió correctamente"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _download_file(self, url: str, output_path: Path) -> bool:
        """Descargar archivo desde URL de forma optimizada con streaming"""
        try:
            print(f"[TikTok] Descargando desde: {url[:50]}...")
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=32768): # Buffer de 32KB
                                if chunk:
                                    f.write(chunk)
                        return True
                    else:
                        print(f"[TikTok] Error en descarga: status {response.status_code}")
                
            return False
        except Exception as e:
            print(f"[TikTok] Exception en descarga: {str(e)}")
            return False
    
    async def download(self, url: str, format: str = "mp4") -> dict:
        """
        Descargar video de TikTok sin watermark
        
        Args:
            url: URL del video de TikTok
            format: Formato de salida (mp4 para video, mp3 para audio)
        
        Returns:
            dict con success, file_path, filename
        """
        try:
            # Obtener información del video
            info = await self._get_video_info_tikwm(url)
            
            if not info["success"]:
                return {
                    "success": False,
                    "error": info.get("error", "No se pudo obtener información del video")
                }
            
            # Determinar qué descargar
            if format in ["mp3", "audio"]:
                download_url = info.get("audio_url")
                extension = "mp3"
            else:
                download_url = info.get("video_url")
                extension = "mp4"
            
            if not download_url:
                return {
                    "success": False,
                    "error": "No se encontró URL de descarga"
                }
            
            # Generar nombre de archivo único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\s-]', '', info.get("title", "tiktok")[:50])
            safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_')
            
            filename = f"tiktok_{safe_title}_{timestamp}.{extension}"
            output_path = self.downloads_dir / filename
            
            # Descargar archivo
            success = await self._download_file(download_url, output_path)
            
            if success and output_path.exists():
                return {
                    "success": True,
                    "file_path": str(output_path),
                    "filename": filename,
                    "title": info.get("title"),
                    "author": info.get("author")
                }
            
            return {
                "success": False,
                "error": "Error al descargar el archivo"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_info(self, url: str) -> dict:
        """Obtener información del video de TikTok vía oEmbed (rápido para previews)"""
        try:
            # TikTok oEmbed API
            oembed_url = f"https://www.tiktok.com/oembed?url={url}"
            print(f"[TikTok] Consultando oEmbed: {oembed_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(oembed_url)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "title": data.get("title", "TikTok Video"),
                        "author": data.get("author_name", "TikTok Creator"),
                        "cover": data.get("thumbnail_url"),
                        "thumbnail": data.get("thumbnail_url"),
                        "duration": None
                    }
            
            # Fallback a tikwm si oEmbed falla
            return await self._get_video_info_tikwm(url)
        except Exception as e:
            print(f"[TikTok] Error en oEmbed: {str(e)}, usando fallback...")
            return await self._get_video_info_tikwm(url)

    async def download_audio_only(self, url: str) -> dict:
        """Descargar solo el audio del TikTok"""
        return await self.download(url, format="mp3")
