# 🎬 MediaGrab - Media Downloader

Descargador de medios para YouTube, Spotify y TikTok con un asistente de IA integrado.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Características

- 📺 **YouTube**: Videos y música en MP3, MP4, FLAC, WAV
- 🎵 **Spotify**: Canciones y playlists en alta calidad
- 📱 **TikTok**: Videos sin marca de agua
- 🤖 **Asistente IA**: Busca y descarga canciones con lenguaje natural
- 🔗 **Auto-detección**: Pega un link y se detecta automáticamente
- 📁 **Guardado directo**: Elige tu carpeta de destino

---

## 🚀 Instalación

### Desarrollo Local

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd media-downloader

# 2. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu GROQ_API_KEY

# 3. Frontend
cd ../web
npm install
cp .env.example .env

# 4. Ejecutar
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd web
npm run dev
```

### 🐳 Docker (Producción)

```bash
# 1. Configurar variables de entorno
cp backend/.env.example backend/.env
# Editar backend/.env con tu GROQ_API_KEY

# 2. Construir y ejecutar
docker-compose up -d --build

# 3. Ver logs
docker-compose logs -f

# 4. Acceder
# Frontend: http://localhost
# API: http://localhost:8000
```

---

## ⚙️ Configuración

### Backend (`backend/.env`)

```env
GROQ_API_KEY=tu_api_key_de_groq
DOWNLOADS_DIR=/downloads
ENVIRONMENT=production
CORS_ORIGINS=https://tu-dominio.com
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### Frontend (`web/.env`)

```env
VITE_API_URL=http://localhost:8000
```

---

## 📚 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/download/youtube` | Descargar de YouTube |
| POST | `/api/download/spotify` | Descargar de Spotify |
| POST | `/api/download/tiktok` | Descargar de TikTok |
| GET | `/api/tasks/{id}` | Estado de tarea |
| POST | `/api/agent/chat` | Chat con IA |

---

## 🔒 Seguridad

- ✅ API Keys en variables de entorno
- ✅ Rate limiting (100 req/min por IP)
- ✅ CORS configurable
- ✅ Headers de seguridad en nginx

---

## 📦 Estructura del Proyecto

```
media-downloader/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── downloaders/         # YouTube, Spotify, TikTok
│   ├── services/            # Agente IA
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── web/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API client
│   │   └── App.jsx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .env
├── docker-compose.yml
└── README.md
```

---

## 📝 Licencia

MIT © 2024 MediaGrab
