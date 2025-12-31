import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, X, Bot, User, Loader2, List, Trash2, FolderSync } from 'lucide-react';
import { agentChat, downloadYouTube, downloadSpotify, downloadTikTok } from '../services/api';

function AIChatPanel({ isOpen, onClose, onDownloadComplete }) {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: '¡Hola! Soy tu asistente de MediaGrab. Puedes pegarme una lista de canciones o pedirme que busque algo y lo descargaré por ti. ¿Qué quieres bajar hoy?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsLoading(true);

        try {
            const response = await agentChat(userMsg);

            // Si hay intenciones de descarga, procesarlas
            if (response.intentions && response.intentions.length > 0) {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: response.message,
                    intentions: response.intentions,
                    requires_folder: response.requires_folder,
                    auto_download: response.auto_download
                }]);

                // Si es auto_download (URL detectada), iniciar descarga automáticamente
                if (response.auto_download) {
                    setTimeout(() => {
                        handleBatchDownload(response.intentions);
                    }, 500);
                }
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: response.message }]);
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: "Hubo un error al conectar con el cerebro de IA. Verifica tu conexión." }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleBatchDownload = async (intentions) => {
        try {
            // 1. Pedir carpeta de destino (opcional)
            if ('showDirectoryPicker' in window) {
                try {
                    await window.showDirectoryPicker({ mode: 'readwrite' });
                } catch (e) {
                    console.log("Folder picker cancelled, using default");
                }
            }

            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `⏳ Iniciando descarga de ${intentions.length} elemento${intentions.length > 1 ? 's' : ''}...`
            }]);

            // 2. Iniciar descargas una por una
            for (const item of intentions) {
                // Usar URL directa si está disponible, sino usar query
                const downloadUrl = item.url || item.query;
                console.log(`[Batch] Descargando: ${downloadUrl} (${item.platform})`);

                let response;
                try {
                    if (item.platform === 'spotify') {
                        response = await downloadSpotify(downloadUrl, item.format || 'mp3');
                    } else if (item.platform === 'tiktok') {
                        response = await downloadTikTok(downloadUrl, item.format || 'mp4');
                    } else {
                        response = await downloadYouTube(downloadUrl, item.format || 'mp3', item.quality || '320k');
                    }

                    // Notificar al historial inmediatamente
                    if (response && response.task_id) {
                        onDownloadComplete({
                            id: response.task_id,
                            platform: item.platform || 'youtube',
                            filename: item.query || downloadUrl,
                            fileId: null, // Estado pendiente
                            timestamp: new Date().toISOString(),
                        });
                    }
                } catch (downloadError) {
                    console.error(`[Batch] Error descargando ${item.query}:`, downloadError);
                }
            }

            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "✅ ¡Descargas iniciadas! Puedes ver el progreso en el historial. Los archivos se guardarán automáticamente en tu carpeta seleccionada."
            }]);
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "❌ Hubo un error al procesar las descargas. Intenta de nuevo."
            }]);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ x: 400, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 400, opacity: 0 }}
                    className="fixed right-0 top-0 h-full w-full max-w-md bg-gray-900 shadow-2xl z-50 border-l border-white/10 flex flex-col"
                >
                    {/* Header */}
                    <div className="p-4 border-b border-white/10 flex justify-between items-center bg-gray-800">
                        <div className="flex items-center gap-2">
                            <Bot className="text-purple-400 w-6 h-6" />
                            <h2 className="text-white font-bold text-lg">Asistente IA</h2>
                        </div>
                        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Messages Container */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-purple-500/20">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[85%] p-3 rounded-2xl ${msg.role === 'user'
                                    ? 'bg-purple-600 text-white rounded-tr-none'
                                    : 'bg-gray-800 text-gray-200 border border-white/5 rounded-tl-noneShadow-lg'
                                    }`}>
                                    <p className="text-sm leading-relaxed">{msg.content}</p>

                                    {/* Lista de intenciones */}
                                    {msg.intentions && msg.intentions.length > 0 && (
                                        <div className="mt-3 p-3 bg-black/40 rounded-xl space-y-2">
                                            <div className="flex items-center gap-2 text-xs font-bold text-purple-400 mb-2 uppercase tracking-wider">
                                                <List className="w-3 h-3" />
                                                Lista Detectada ({msg.intentions.length})
                                            </div>
                                            {msg.intentions.map((intent, i) => (
                                                <div key={i} className="text-xs text-gray-400 border-l-2 border-purple-500/30 pl-2 py-1 truncate">
                                                    {intent.query} <span className="text-[10px] opacity-40">[{intent.format}]</span>
                                                </div>
                                            ))}
                                            <button
                                                onClick={() => handleBatchDownload(msg.intentions)}
                                                className="w-full mt-2 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white text-xs font-bold rounded-lg transition-all shadow-lg hover:shadow-purple-500/20 flex items-center justify-center gap-2"
                                            >
                                                <FolderSync className="w-4 h-4" />
                                                Descargar Lote Completo
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-gray-800 flex items-center gap-2 p-3 rounded-2xl rounded-tl-none border border-white/5">
                                    <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                                    <span className="text-xs text-gray-400">Pensando...</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="p-4 border-t border-white/10 bg-gray-800/50">
                        <div className="relative">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                placeholder="Escribe el nombre de las canciones o pega links..."
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 pr-12 text-sm text-white focus:outline-none focus:border-purple-500/50 resize-none max-h-32 transition-all"
                                rows="2"
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                className="absolute right-3 bottom-3 p-2 text-purple-400 hover:text-purple-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                <Send className="w-5 h-5" />
                            </button>
                        </div>
                        <p className="mt-2 text-[10px] text-gray-500 text-center">
                            Shift + Enter para nueva línea. Pulsa Intro para enviar.
                        </p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

export default AIChatPanel;
