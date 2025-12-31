import os
import re
import json
import subprocess
from typing import List, Dict, Optional
from groq import Groq
from pydantic import BaseModel

class SongIntention(BaseModel):
    query: str
    format: str = "mp3"
    quality: str = "320k"
    platform: str = "youtube"
    url: Optional[str] = None  # URL directa si se detectó

class AgentResponse(BaseModel):
    message: str
    intentions: List[SongIntention] = []
    requires_folder: bool = False
    search_results: Optional[List[Dict]] = None  # Resultados de búsqueda

class MediaAgent:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        
        # Patrones de URL
        self.url_patterns = {
            'youtube': re.compile(r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+', re.IGNORECASE),
            'spotify': re.compile(r'(https?://)?(open\.)?spotify\.com/(track|album|playlist)/[\w]+', re.IGNORECASE),
            'tiktok': re.compile(r'(https?://)?(www\.|vm\.)?tiktok\.com/[@\w./]+', re.IGNORECASE)
        }
        
        self.system_prompt = """
        Eres el asistente inteligente de MediaGrab. Tu objetivo es ayudar al usuario a descargar música y videos.
        
        CAPACIDADES:
        1. Puedes descargar de YouTube, Spotify y TikTok.
        2. Si el usuario menciona una canción/artista, búscala en YouTube.
        3. Si el usuario pega un link, detéctalo y prepáralo para descarga.
        4. Puedes procesar listas de múltiples canciones.
        
        REGLAS:
        1. Si el usuario envía una lista de canciones (nombres o links), identifícalas TODAS.
        2. Siempre asume formato 'mp3' y calidad '320k' a menos que el usuario pida algo diferente.
        3. Si detectas URLs, ponlas directamente en "url" del intention.
        4. Si es un nombre de canción, ponlo en "query" para búsqueda.
        5. Para Spotify usa platform="spotify", para TikTok usa platform="tiktok", para YouTube o búsquedas usa platform="youtube".
        
        RESPONDE SIEMPRE en JSON con esta estructura:
        {
            "message": "<mensaje amigable al usuario>",
            "intentions": [
                {"query": "nombre o descripción", "url": "URL si existe", "format": "mp3", "quality": "320k", "platform": "youtube|spotify|tiktok"}
            ],
            "requires_folder": true,
            "needs_search": false
        }
        
        EJEMPLOS:
        - Usuario: "descarga Bohemian Rhapsody de Queen"
          Respuesta: {"message": "¡Perfecto! Buscaré Bohemian Rhapsody de Queen en YouTube.", "intentions": [{"query": "Bohemian Rhapsody Queen", "format": "mp3", "quality": "320k", "platform": "youtube"}], "requires_folder": true}
        
        - Usuario: "https://youtu.be/xyz123"
          Respuesta: {"message": "¡Link de YouTube detectado! Preparando descarga...", "intentions": [{"query": "YouTube Video", "url": "https://youtu.be/xyz123", "format": "mp3", "quality": "320k", "platform": "youtube"}], "requires_folder": true}
        
        - Usuario: "quiero estas canciones:\n1. Despacito\n2. Shape of You\n3. Blinding Lights"
          Respuesta: {"message": "¡Encontré 3 canciones en tu lista! Las buscaré en YouTube.", "intentions": [{"query": "Despacito Luis Fonsi", ...}, {"query": "Shape of You Ed Sheeran", ...}, {"query": "Blinding Lights The Weeknd", ...}], "requires_folder": true}
        
        IMPORTANTE: Solo responde con JSON válido. Sé conciso y amigable.
        """

    def detect_urls(self, text: str) -> List[Dict]:
        """Detectar URLs de plataformas conocidas en el texto"""
        found_urls = []
        
        for platform, pattern in self.url_patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                # Reconstruir URL completa
                if isinstance(match, tuple):
                    url = ''.join(match)
                else:
                    url = match
                
                # Asegurar que tenga https
                if not url.startswith('http'):
                    url = 'https://' + url
                    
                found_urls.append({
                    'url': url,
                    'platform': platform
                })
        
        return found_urls

    def search_youtube(self, query: str, max_results: int = 1) -> List[Dict]:
        """Buscar en YouTube usando yt-dlp"""
        try:
            cmd = [
                "yt-dlp",
                f"ytsearch{max_results}:{query}",
                "--dump-json",
                "--no-download",
                "--no-warnings",
                "--flat-playlist"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout:
                results = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            video = json.loads(line)
                            results.append({
                                'title': video.get('title', 'Sin título'),
                                'url': f"https://youtube.com/watch?v={video.get('id')}",
                                'channel': video.get('channel') or video.get('uploader', 'Desconocido'),
                                'duration': video.get('duration'),
                                'thumbnail': video.get('thumbnail')
                            })
                        except json.JSONDecodeError:
                            continue
                return results
            return []
        except Exception as e:
            print(f"[Agent] Error buscando en YouTube: {e}")
            return []

    async def chat(self, user_prompt: str) -> Dict:
        try:
            # Paso 1: Detectar URLs directamente en el input
            detected_urls = self.detect_urls(user_prompt)
            
            # Si hay URLs directas, procesarlas inmediatamente
            if detected_urls:
                intentions = []
                for url_info in detected_urls:
                    intentions.append({
                        "query": f"{url_info['platform'].title()} - Link directo",
                        "url": url_info['url'],
                        "format": "mp3",
                        "quality": "320k",
                        "platform": url_info['platform']
                    })
                
                platform_names = set([u['platform'].title() for u in detected_urls])
                message = f"🔗 ¡{'Links' if len(detected_urls) > 1 else 'Link'} de {', '.join(platform_names)} detectado{'s' if len(detected_urls) > 1 else ''}! Iniciando descarga..."
                
                return {
                    "message": message,
                    "intentions": intentions,
                    "requires_folder": True,
                    "auto_download": True  # Flag para descargar automáticamente
                }
            
            # Paso 2: Llamar al LLM para procesar consultas de texto
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            response_content = completion.choices[0].message.content
            ai_response = json.loads(response_content)
            
            # Paso 3: Si hay queries sin URL, buscar en YouTube
            enhanced_intentions = []
            for intention in ai_response.get("intentions", []):
                if intention.get("url"):
                    # Ya tiene URL, usar directamente
                    enhanced_intentions.append(intention)
                elif intention.get("query") and intention.get("platform", "youtube") == "youtube":
                    # Buscar en YouTube
                    search_results = self.search_youtube(intention["query"])
                    if search_results:
                        intention["url"] = search_results[0]["url"]
                        intention["query"] = search_results[0]["title"]
                        intention["search_result"] = search_results[0]
                    enhanced_intentions.append(intention)
                else:
                    enhanced_intentions.append(intention)
            
            ai_response["intentions"] = enhanced_intentions
            
            # Actualizar mensaje si encontramos resultados
            if enhanced_intentions and any(i.get("search_result") for i in enhanced_intentions):
                found_songs = [i.get("query", "Canción") for i in enhanced_intentions if i.get("search_result")]
                ai_response["message"] = f"🎵 ¡Encontré: {', '.join(found_songs[:3])}{'...' if len(found_songs) > 3 else ''}! Listo para descargar."
            
            return ai_response
            
        except Exception as e:
            print(f"[Agent] Error: {str(e)}")
            return {
                "message": f"Lo siento, hubo un error al procesar tu solicitud: {str(e)}",
                "intentions": [],
                "requires_folder": False
            }

