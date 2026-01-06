import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { X, Download, Loader2, CheckCircle, AlertCircle, Link2, Music, User, Folder, FolderOpen } from 'lucide-react';
import { downloadYouTube, downloadSpotify, downloadTikTok, getTaskStatus, downloadFile, getPreview } from '../services/api';

function DownloadModal({ platform, onClose, onDownloadComplete }) {
    const [url, setUrl] = useState('');
    const [format, setFormat] = useState(platform.formats[0]);
    const [quality, setQuality] = useState('320k');
    const [status, setStatus] = useState('idle'); // idle, previewing, loading, polling, completed, error
    const [progress, setProgress] = useState(0);
    const [error, setError] = useState('');
    const [taskId, setTaskId] = useState(null);
    const [result, setResult] = useState(null);
    const [preview, setPreview] = useState(null);
    const [saveFolder, setSaveFolder] = useState(null);
    const [saveFolderName, setSaveFolderName] = useState('Carpeta de Descargas');
    const [isPickerOpen, setIsPickerOpen] = useState(false);

    const qualities = ['128k', '192k', '320k'];

    // Verificar si File System Access API está disponible
    const hasFileSystemAccess = 'showDirectoryPicker' in window;

    // Función para seleccionar carpeta de destino
    const selectFolder = async () => {
        if (!hasFileSystemAccess) {
            alert("Tu navegador no soporta la selección de carpetas directamente. Se usará la carpeta de descargas predeterminada.");
            return;
        }

        if (isPickerOpen) return;

        setIsPickerOpen(true);
        try {
            const dirHandle = await window.showDirectoryPicker({
                mode: 'readwrite',
                startIn: 'downloads'
            });

            // Solicitar explícitamente permisos si es necesario
            if ((await dirHandle.queryPermission({ mode: 'readwrite' })) !== 'granted') {
                if ((await dirHandle.requestPermission({ mode: 'readwrite' })) !== 'granted') {
                    throw new Error('Permiso de escritura denegado');
                }
            }

            setSaveFolder(dirHandle);
            setSaveFolderName(dirHandle.name);
            setError('');
            console.log('[DownloadModal] Carpeta seleccionada:', dirHandle.name);
        } catch (err) {
            if (err.name === 'AbortError') {
                console.log('[DownloadModal] Selección cancelada');
            } else if (err.name === 'NotAllowedError') {
                setError('El navegador bloqueó el acceso a la carpeta por seguridad.');
            } else {
                console.error('[DownloadModal] Error selecting folder:', err);
                setError('Error al seleccionar carpeta: ' + err.message);
            }
        } finally {
            setIsPickerOpen(false);
        }
    };

    // Función para obtener preview automáticamente
    const fetchPreview = useCallback(async (inputUrl) => {
        if (!inputUrl.trim() || inputUrl.length < 15) {
            setPreview(null);
            return;
        }

        const patterns = {
            youtube: /youtube\.com|youtu\.be/,
            spotify: /spotify\.com/,
            tiktok: /tiktok\.com/
        };

        if (!patterns[platform.id]?.test(inputUrl)) {
            return;
        }

        setStatus('previewing');
        setError('');

        try {
            console.log('[DownloadModal] Obteniendo preview para:', inputUrl);
            const previewData = await getPreview(inputUrl, platform.id);
            if (previewData.success) {
                setPreview(previewData);
                setStatus('idle');
            } else {
                setPreview(null);
                setStatus('idle');
                if (previewData.error) setError(previewData.error);
            }
        } catch (err) {
            console.error('[DownloadModal] Preview error:', err);
            setPreview(null);
            setStatus('idle');
        }
    }, [platform.id]);

    // Debounce para el preview más rápido (500ms)
    useEffect(() => {
        const timer = setTimeout(() => {
            if (url.length > 15) {
                fetchPreview(url);
            }
        }, 500);

        return () => clearTimeout(timer);
    }, [url, fetchPreview]);

    const startDownload = async () => {
        if (!url.trim()) {
            setError('Por favor ingresa una URL');
            return;
        }

        setStatus('loading');
        setError('');
        setProgress(0);

        try {
            let response;
            switch (platform.id) {
                case 'youtube':
                    response = await downloadYouTube(url, format, quality);
                    break;
                case 'spotify':
                    response = await downloadSpotify(url, format);
                    break;
                case 'tiktok':
                    response = await downloadTikTok(url, format);
                    break;
                default:
                    throw new Error('Plataforma no soportada');
            }

            if (response.task_id) {
                setTaskId(response.task_id);
                setStatus('polling');
            }
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Error al iniciar descarga');
            setStatus('error');
        }
    };

    // Poll for status
    useEffect(() => {
        if (!taskId || status !== 'polling') return;

        const pollInterval = setInterval(async () => {
            try {
                const taskStatus = await getTaskStatus(taskId);
                console.log('[DownloadModal] Task status:', taskStatus);
                setProgress(taskStatus.progress || 0);

                if (taskStatus.status === 'completed') {
                    clearInterval(pollInterval);
                    setStatus('completed');
                    setResult(taskStatus);

                    onDownloadComplete({
                        id: taskId,
                        platform: platform.id,
                        filename: taskStatus.filename,
                        fileId: taskStatus.file_id,
                        timestamp: new Date().toISOString(),
                    });
                } else if (taskStatus.status === 'error') {
                    clearInterval(pollInterval);
                    const errorMessage = taskStatus.error || taskStatus.message || 'Error en la descarga';
                    console.error('[DownloadModal] Error:', errorMessage);
                    setError(errorMessage);
                    setStatus('error');
                }
            } catch (err) {
                console.error('[DownloadModal] Error polling:', err);
            }
        }, 2000);

        return () => clearInterval(pollInterval);
    }, [taskId, status, platform.id, onDownloadComplete]);

    // Función para guardar archivo en carpeta seleccionada
    const handleDownloadFile = useCallback(async (fileId, filename) => {
        const id = fileId || result?.file_id;
        const name = filename || result?.filename;
        if (!id) {
            console.error('[DownloadModal] No file_id available for download');
            setStatus('saved'); // Still show saved so user can use manual button
            return;
        }

        try {
            setStatus('saving');
            console.log('[DownloadModal] Starting download for file:', id, name);
            
            // Descargar el archivo del servidor
            const fileUrl = downloadFile(id);
            console.log('[DownloadModal] Fetching from URL:', fileUrl);
            
            const response = await fetch(fileUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            console.log('[DownloadModal] Blob received, size:', blob.size);

            if (saveFolder && hasFileSystemAccess) {
                // Guardar en la carpeta seleccionada
                const finalFilename = name || `download.${format}`;
                const fileHandle = await saveFolder.getFileHandle(finalFilename, { create: true });
                const writable = await fileHandle.createWritable();
                await writable.write(blob);
                await writable.close();

                // Mostrar mensaje de éxito
                setError('');
                setStatus('saved');
                console.log(`✅ Archivo guardado en: ${saveFolderName}/${finalFilename}`);
            } else {
                // Descarga del navegador - simplemente marcar como listo
                // El usuario usará el botón explícito de descarga
                console.log('[DownloadModal] No folder selected, user will download manually');
                setStatus('saved');
            }
        } catch (err) {
            console.error('[DownloadModal] Error saving file:', err);
            // No mostrar error crítico, solo permitir descarga manual
            setStatus('saved');
        }
    }, [result, saveFolder, hasFileSystemAccess, saveFolderName, format]);

    // Auto-save cuando se completa la descarga
    useEffect(() => {
        if (status === 'completed' && result?.file_id) {
            // Guardar automáticamente
            handleDownloadFile(result.file_id, result.filename);
        }
    }, [status, result, handleDownloadFile]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="w-full max-w-lg glass-dark rounded-3xl p-8 relative max-h-[90vh] overflow-y-auto"
            >
                {/* Close button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-2 rounded-full hover:bg-purple-900/30 transition-colors"
                >
                    <X className="w-5 h-5 text-gray-400" />
                </button>

                {/* Header */}
                <div className="flex items-center gap-4 mb-6">
                    <span className="text-4xl">{platform.icon}</span>
                    <div>
                        <h2 className="text-2xl font-bold text-white">{platform.name}</h2>
                        <p className="text-gray-400 text-sm">{platform.description}</p>
                    </div>
                </div>

                {/* URL Input */}
                <div className="mb-5">
                    <label className="block text-sm text-gray-400 mb-2">
                        <Link2 className="w-4 h-4 inline mr-2" />
                        URL del contenido
                    </label>
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder={`Pega aquí el link de ${platform.name}...`}
                        className="w-full px-4 py-3 rounded-xl text-white placeholder-gray-500"
                        disabled={status === 'loading' || status === 'polling'}
                    />
                </div>

                {/* Preview Card - Mostrar cuando hay preview */}
                {status === 'previewing' && (
                    <div className="mb-5 p-4 rounded-xl bg-purple-900/20 border border-purple-700/30">
                        <div className="flex items-center gap-3">
                            <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                            <p className="text-purple-300 text-sm">Obteniendo información...</p>
                        </div>
                    </div>
                )}

                {preview && status !== 'previewing' && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-5 p-5 rounded-2xl bg-gradient-to-br from-purple-800/30 via-purple-900/40 to-pink-900/30 border border-purple-500/40 shadow-lg shadow-purple-900/20"
                    >
                        <div className="flex items-center gap-5">
                            {preview.thumbnail ? (
                                <img
                                    src={preview.thumbnail}
                                    alt="Cover"
                                    className="w-20 h-20 rounded-xl object-cover shadow-lg ring-2 ring-purple-500/30"
                                />
                            ) : (
                                <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-purple-700 to-pink-600 flex items-center justify-center shadow-lg">
                                    <Music className="w-10 h-10 text-white" />
                                </div>
                            )}
                            <div className="flex-1 min-w-0">
                                <h3 className="text-white font-bold text-lg truncate">
                                    {preview.title || 'Sin título'}
                                </h3>
                                {preview.artist && (
                                    <p className="text-purple-200 text-sm flex items-center gap-2 mt-2">
                                        <User className="w-4 h-4 text-purple-400" />
                                        <span className="font-medium">{preview.artist}</span>
                                    </p>
                                )}
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* Selector de carpeta de destino */}
                {hasFileSystemAccess && (
                    <div className="mb-5">
                        <label className="block text-sm text-gray-400 mb-2">
                            <Folder className="w-4 h-4 inline mr-2" />
                            Guardar en
                        </label>
                        <button
                            onClick={selectFolder}
                            disabled={status === 'loading' || status === 'polling'}
                            className="w-full px-4 py-3 rounded-xl bg-purple-900/30 border border-purple-700/30
                                     text-left flex items-center gap-3 hover:bg-purple-800/40 transition-colors
                                     disabled:opacity-50"
                        >
                            <FolderOpen className="w-5 h-5 text-purple-400" />
                            <span className="text-white flex-1 truncate">{saveFolderName}</span>
                            <span className="text-purple-400 text-sm">Cambiar</span>
                        </button>
                        {saveFolder && (
                            <p className="text-green-400 text-xs mt-1 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Carpeta seleccionada
                            </p>
                        )}
                    </div>
                )}

                {/* Format selector */}
                <div className="mb-5">
                    <label className="block text-sm text-gray-400 mb-2">Formato</label>
                    <div className="flex flex-wrap gap-2">
                        {platform.formats.map((f) => (
                            <button
                                key={f}
                                onClick={() => setFormat(f)}
                                disabled={status === 'loading' || status === 'polling'}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all
                  ${format === f
                                        ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/30'
                                        : 'bg-purple-900/30 text-gray-300 hover:bg-purple-800/40'
                                    }`}
                            >
                                {f.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Quality selector (for audio formats) */}
                {['mp3', 'm4a', 'flac', 'wav'].includes(format) && platform.id === 'youtube' && (
                    <div className="mb-5">
                        <label className="block text-sm text-gray-400 mb-2">Calidad de Audio</label>
                        <div className="flex gap-2">
                            {qualities.map((q) => (
                                <button
                                    key={q}
                                    onClick={() => setQuality(q)}
                                    disabled={status === 'loading' || status === 'polling'}
                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${quality === q
                                            ? 'bg-purple-600 text-white'
                                            : 'bg-purple-900/30 text-gray-300 hover:bg-purple-800/40'
                                        }`}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Progress bar */}
                {(status === 'loading' || status === 'polling') && (
                    <div className="mb-5">
                        <div className="flex justify-between text-sm text-gray-400 mb-2">
                            <span>Descargando...</span>
                            <span>{progress}%</span>
                        </div>
                        <div className="h-3 bg-purple-900/30 rounded-full overflow-hidden">
                            <motion.div
                                className="h-full progress-bar rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* Error message */}
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-5 p-4 rounded-xl bg-red-900/30 border border-red-700/30 flex items-center gap-3"
                    >
                        <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                        <p className="text-red-400 text-sm">{error}</p>
                    </motion.div>
                )}

                {/* Success message */}
                {(status === 'completed' || status === 'saving') && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-5 p-4 rounded-xl bg-purple-900/30 border border-purple-700/30 flex items-center gap-3"
                    >
                        <Loader2 className="w-5 h-5 text-purple-400 animate-spin flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-purple-400 text-sm">Guardando archivo...</p>
                            <p className="text-gray-400 text-xs mt-1">{result?.filename}</p>
                        </div>
                    </motion.div>
                )}

                {status === 'saved' && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-5 p-4 rounded-xl bg-green-900/30 border border-green-700/30"
                    >
                        <div className="flex items-center gap-3">
                            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                            <div className="flex-1">
                                <p className="text-green-400 text-sm">¡Descarga completada!</p>
                                <p className="text-gray-400 text-xs mt-1">{result?.filename}</p>
                            </div>
                        </div>
                        {/* Botón de descarga explícito */}
                        <button
                            onClick={() => {
                                const fileUrl = downloadFile(result?.file_id);
                                window.open(fileUrl, '_blank');
                            }}
                            className="w-full mt-3 py-3 px-4 rounded-xl bg-green-600 hover:bg-green-500 
                                     text-white font-semibold flex items-center justify-center gap-2 transition-colors"
                        >
                            <Download className="w-5 h-5" />
                            Guardar en mi computadora
                        </button>
                    </motion.div>
                )}

                {/* Action buttons */}
                <div className="flex gap-3">
                    {status === 'saved' ? (
                        <button
                            onClick={onClose}
                            className="flex-1 btn-primary py-4 rounded-xl text-white font-semibold 
                flex items-center justify-center gap-2"
                        >
                            <CheckCircle className="w-5 h-5" />
                            ¡Listo! Cerrar
                        </button>
                    ) : status === 'saving' ? (
                        <button
                            disabled
                            className="flex-1 btn-primary py-4 rounded-xl text-white font-semibold 
                flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Guardando...
                        </button>
                    ) : (
                        <button
                            onClick={startDownload}
                            disabled={status === 'loading' || status === 'polling' || status === 'previewing' || status === 'completed'}
                            className="flex-1 btn-primary py-4 rounded-xl text-white font-semibold 
                flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {status === 'loading' || status === 'polling' ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Procesando...
                                </>
                            ) : (
                                <>
                                    <Download className="w-5 h-5" />
                                    Descargar
                                </>
                            )}
                        </button>
                    )}
                </div>
            </motion.div>
        </motion.div>
    );
}

export default DownloadModal;
