"""
Spotify Downloader - Alternativa usando yt-dlp
Busca la canción en YouTube y la descarga
"""

import os
import subprocess
import re
import httpx
import traceback
from pathlib import Path
from typing import Optional
from datetime import datetime


class SpotifyDownloader:
    """Descargador de Spotify usando yt-dlp (busca en YouTube)"""
    
    def __init__(self, downloads_dir: Path):
        self.downloads_dir = downloads_dir
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
    
    async def _extract_track_info(self, url: str) -> dict:
        """Extraer información del track de Spotify via embed"""
        try:
            # Extraer ID del track - soporta varios formatos de URL
            patterns = [
                r'track/([a-zA-Z0-9]{22})',  # ID completo de 22 caracteres
                r'track/([a-zA-Z0-9]+)',      # Cualquier ID
            ]
            
            track_id = None
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    track_id = match.group(1)
                    break
            
            if not track_id:
                return {"success": False, "error": f"URL de Spotify inválida. No se encontró ID de track en: {url}"}
            
            print(f"[Spotify] Track ID encontrado: {track_id}")
            
            # Usar oembed de Spotify para obtener info completa
            oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
            print(f"[Spotify] Consultando oembed: {oembed_url}")
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(oembed_url)
                
                print(f"[Spotify] Respuesta oembed: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # El título viene como "Canción by Artista"
                    raw_title = data.get("title", "")
                    thumbnail = data.get("thumbnail_url", "")
                    
                    print(f"[Spotify] Raw title: {raw_title}")
                    print(f"[Spotify] Thumbnail: {thumbnail}")
                    
                    # Parsear título y artista (formato: "Canción by Artista")
                    song_title = raw_title
                    artist = ""
                    
                    if " by " in raw_title:
                        parts = raw_title.split(" by ", 1)
                        song_title = parts[0].strip()
                        artist = parts[1].strip()
                    
                    return {
                        "success": True,
                        "title": song_title,
                        "artist": artist,
                        "thumbnail": thumbnail,
                        "search_query": raw_title.replace(" by ", " - ")  # Para buscar en YouTube
                    }
                else:
                    return {"success": False, "error": f"Spotify API error: {response.status_code}. Verifica que el link sea válido."}
            
        except httpx.TimeoutException:
            return {"success": False, "error": "Timeout al conectar con Spotify. Intenta de nuevo."}
        except Exception as e:
            print(f"[Spotify] Error: {str(e)}")
            return {"success": False, "error": f"Error: {str(e)}"}
    
    def _get_format_options(self, format: str) -> list:
        """Obtener opciones de yt-dlp según formato"""
        quality_map = {
            "mp3": ["--audio-format", "mp3", "--audio-quality", "0", "--postprocessor-args", "ffmpeg:-threads 4"],
            "m4a": ["--audio-format", "m4a", "--audio-quality", "0", "--postprocessor-args", "ffmpeg:-threads 4"],
            "flac": ["--audio-format", "flac", "--postprocessor-args", "ffmpeg:-threads 4"],
            "wav": ["--audio-format", "wav", "--postprocessor-args", "ffmpeg:-threads 4"],
            "ogg": ["--audio-format", "vorbis", "--audio-quality", "0", "--postprocessor-args", "ffmpeg:-threads 4"],
        }
        return quality_map.get(format, ["--audio-format", "mp3", "--audio-quality", "0", "--postprocessor-args", "ffmpeg:-threads 4"])
    
    async def download(self, url: str, format: str = "mp3") -> dict:
        """
        Descargar track de Spotify (via YouTube search)
        """
        try:
            print(f"[Spotify] Iniciando descarga: {url}")
            
            # Obtener info del track de Spotify
            track_info = await self._extract_track_info(url)
            
            if not track_info["success"]:
                print(f"[Spotify] Error obteniendo info: {track_info.get('error')}")
                return track_info
            
            search_query = track_info["search_query"]
            print(f"[Spotify] Buscando en YouTube: {search_query}")
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\s-]', '', search_query)[:50]
            safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_')
            
            if not safe_title:
                safe_title = f"spotify_track_{timestamp}"
            
            output_template = str(self.downloads_dir / f"{safe_title}_{timestamp}.%(ext)s")
            print(f"[Spotify] Output template: {output_template}")
            
            format_opts = self._get_format_options(format)
            
            # Buscar y descargar usando yt-dlp con ytsearch
            cmd = [
                "yt-dlp",
                f"ytsearch1:{search_query}",
                "-x",
                *format_opts,
                "-o", output_template,
                "--no-playlist",
                "--no-warnings",
                "--concurrent-fragments", "10",
                "--no-call-home",
                "--no-check-certificate",
                "--buffer-size", "16K",
            ]
            
            print(f"[Spotify] Ejecutando: {' '.join(cmd)}")
            
            # Ejecutar yt-dlp con subprocess.run (sincrono pero confiable en Windows)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutos max
            )
            
            stdout_text = result.stdout
            stderr_text = result.stderr
            
            print(f"[Spotify] yt-dlp returncode: {result.returncode}")
            print(f"[Spotify] stdout: {stdout_text[:500] if stdout_text else 'empty'}")
            print(f"[Spotify] stderr: {stderr_text[:500] if stderr_text else 'empty'}")
            
            if result.returncode != 0:
                error_msg = stderr_text or stdout_text or "Error desconocido en yt-dlp"
                return {
                    "success": False,
                    "error": f"Error al descargar: {error_msg[:200]}"
                }
            
            # Buscar archivo descargado
            downloaded_files = list(self.downloads_dir.glob(f"{safe_title}_{timestamp}.*"))
            
            if not downloaded_files:
                # Buscar cualquier archivo reciente del formato
                all_files = list(self.downloads_dir.glob(f"*.{format}"))
                if all_files:
                    downloaded_files = [max(all_files, key=os.path.getctime)]
            
            if downloaded_files:
                downloaded_file = downloaded_files[0]
                print(f"[Spotify] Archivo descargado: {downloaded_file}")
                
                parts = search_query.split(" - ", 1) if " - " in search_query else [search_query, "Unknown"]
                
                return {
                    "success": True,
                    "file_path": str(downloaded_file),
                    "filename": downloaded_file.name,
                    "title": parts[0] if len(parts) > 1 else search_query,
                    "artist": parts[1] if len(parts) > 1 else "Unknown"
                }
            
            return {
                "success": False,
                "error": "No se encontró el archivo descargado después de la conversión"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout: la descarga tardó demasiado"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "yt-dlp no está instalado. Instálalo con: pip install yt-dlp"
            }
        except Exception as e:
            tb = traceback.format_exc()
            print(f"[Spotify] Excepción tipo: {type(e).__name__}")
            print(f"[Spotify] Excepción mensaje: {str(e)}")
            print(f"[Spotify] Traceback: {tb}")
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            return {
                "success": False,
                "error": f"Error inesperado: {error_msg}"
            }
    
    async def get_info(self, url: str) -> dict:
        """Obtener información del track sin descargar"""
        return await self._extract_track_info(url)
