import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 60000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const downloadYouTube = async (url, format = 'mp3', quality = '320k') => {
    const response = await api.post('/api/download/youtube', { url, format, quality });
    return response.data;
};

export const downloadSpotify = async (url, format = 'mp3') => {
    const response = await api.post('/api/download/spotify', { url, format });
    return response.data;
};

export const downloadTikTok = async (url, format = 'mp4') => {
    const response = await api.post('/api/download/tiktok', { url, format });
    return response.data;
};

export const getTaskStatus = async (taskId) => {
    const response = await api.get(`/api/tasks/${taskId}`);
    return response.data;
};

export const getFormats = async () => {
    const response = await api.get('/api/formats');
    return response.data;
};

export const downloadFile = (fileId) => {
    return `${API_BASE_URL}/api/files/${fileId}`;
};

export const getPreview = async (url, platform) => {
    const response = await api.post('/api/preview', { url, platform });
    return response.data;
};

export const checkHealth = async () => {
    const response = await api.get('/health');
    return response.data;
};

export const agentChat = async (message) => {
    const response = await api.post('/api/agent/chat', { message });
    return response.data;
};

export default api;
