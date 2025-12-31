"""
Audio/Video Converter Service using FFmpeg
Convierte entre diferentes formatos de audio y video
"""

import asyncio
import os
from pathlib import Path
from typing import Optional


class AudioConverter:
    """Servicio de conversión de audio usando FFmpeg"""
    
    SUPPORTED_FORMATS = ["mp3", "m4a", "wav", "flac", "ogg", "aac"]
    
    QUALITY_PRESETS = {
        "low": {"bitrate": "128k", "sample_rate": "44100"},
        "medium": {"bitrate": "192k", "sample_rate": "44100"},
        "high": {"bitrate": "320k", "sample_rate": "48000"},
        "lossless": {"bitrate": None, "sample_rate": "48000"},
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("./converted")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def convert(
        self,
        input_path: str,
        output_format: str,
        quality: str = "high",
        output_path: Optional[str] = None
    ) -> dict:
        """
        Convertir archivo de audio a otro formato
        
        Args:
            input_path: Ruta al archivo de entrada
            output_format: Formato de salida
            quality: Preset de calidad (low, medium, high, lossless)
            output_path: Ruta de salida opcional
        
        Returns:
            dict con success, output_path, error
        """
        try:
            input_file = Path(input_path)
            
            if not input_file.exists():
                return {
                    "success": False,
                    "error": f"Archivo no encontrado: {input_path}"
                }
            
            if output_format not in self.SUPPORTED_FORMATS:
                return {
                    "success": False,
                    "error": f"Formato no soportado: {output_format}"
                }
            
            # Generar ruta de salida
            if output_path:
                out_file = Path(output_path)
            else:
                out_file = self.output_dir / f"{input_file.stem}.{output_format}"
            
            # Obtener configuración de calidad
            preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS["high"])
            
            # Construir comando FFmpeg
            cmd = ["ffmpeg", "-i", str(input_file), "-y"]
            
            # Agregar opciones según formato
            if output_format == "mp3":
                cmd.extend(["-codec:a", "libmp3lame"])
                if preset["bitrate"]:
                    cmd.extend(["-b:a", preset["bitrate"]])
                    
            elif output_format == "m4a":
                cmd.extend(["-codec:a", "aac"])
                if preset["bitrate"]:
                    cmd.extend(["-b:a", preset["bitrate"]])
                    
            elif output_format == "flac":
                cmd.extend(["-codec:a", "flac"])
                
            elif output_format == "wav":
                cmd.extend(["-codec:a", "pcm_s16le"])
                
            elif output_format == "ogg":
                cmd.extend(["-codec:a", "libvorbis"])
                if preset["bitrate"]:
                    cmd.extend(["-b:a", preset["bitrate"]])
            
            # Sample rate
            if preset["sample_rate"]:
                cmd.extend(["-ar", preset["sample_rate"]])
            
            cmd.append(str(out_file))
            
            # Ejecutar FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and out_file.exists():
                return {
                    "success": True,
                    "output_path": str(out_file),
                    "filename": out_file.name,
                    "size": out_file.stat().st_size
                }
            
            return {
                "success": False,
                "error": stderr.decode('utf-8', errors='ignore')
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "FFmpeg no está instalado"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def extract_audio(
        self,
        video_path: str,
        output_format: str = "mp3",
        quality: str = "high"
    ) -> dict:
        """Extraer audio de un video"""
        return await self.convert(video_path, output_format, quality)
    
    async def get_duration(self, file_path: str) -> Optional[float]:
        """Obtener duración de un archivo de audio/video en segundos"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return float(stdout.decode().strip())
            
            return None
            
        except Exception:
            return None
    
    async def get_metadata(self, file_path: str) -> dict:
        """Obtener metadatos de un archivo de audio"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                import json
                data = json.loads(stdout.decode())
                format_info = data.get("format", {})
                tags = format_info.get("tags", {})
                
                return {
                    "success": True,
                    "duration": float(format_info.get("duration", 0)),
                    "bitrate": int(format_info.get("bit_rate", 0)),
                    "format": format_info.get("format_name"),
                    "title": tags.get("title"),
                    "artist": tags.get("artist"),
                    "album": tags.get("album")
                }
            
            return {"success": False, "error": "Could not read metadata"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
