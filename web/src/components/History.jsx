import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Trash2, Download, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { downloadFile } from '../services/api';

function History({ downloads, setDownloads }) {
    const [isExpanded, setIsExpanded] = useState(false);

    const clearHistory = () => {
        setDownloads([]);
        localStorage.removeItem('downloadHistory');
    };

    const getPlatformIcon = (platform) => {
        const icons = { youtube: '🎬', spotify: '🎵', tiktok: '📱' };
        return icons[platform] || '📥';
    };

    const formatDate = (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleDateString('es-MX', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    if (downloads.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="glass rounded-2xl overflow-hidden"
        >
            {/* Header */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-purple-900/20 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <Clock className="w-5 h-5 text-purple-400" />
                    <span className="font-semibold text-white">Historial de Descargas</span>
                    <span className="px-2 py-0.5 text-xs rounded-full bg-purple-600/50 text-purple-200">
                        {downloads.length}
                    </span>
                </div>
                {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
            </button>

            {/* Content */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                    >
                        {/* Clear button */}
                        <div className="px-6 pb-3">
                            <button
                                onClick={clearHistory}
                                className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
                            >
                                <Trash2 className="w-4 h-4" />
                                Limpiar historial
                            </button>
                        </div>

                        {/* Downloads list */}
                        <div className="max-h-64 overflow-y-auto px-6 pb-4 space-y-2">
                            {downloads.map((item, index) => (
                                <motion.div
                                    key={item.id}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                    className="flex items-center gap-3 p-3 rounded-xl bg-purple-900/20 
                    hover:bg-purple-900/30 transition-colors group"
                                >
                                    <span className="text-2xl">{getPlatformIcon(item.platform)}</span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-white truncate">{item.filename}</p>
                                        <div className="flex items-center gap-2">
                                            <p className="text-xs text-gray-500">{formatDate(item.timestamp)}</p>
                                            {!item.fileId && (
                                                <span className="flex items-center gap-1 text-[10px] text-purple-400 font-medium animate-pulse">
                                                    <Loader2 className="w-3 h-3 animate-spin" />
                                                    Procesando...
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {item.fileId ? (
                                        <a
                                            href={downloadFile(item.fileId)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="p-2 rounded-lg bg-white/10 text-white opacity-0 
                        group-hover:opacity-100 transition-opacity hover:bg-purple-600"
                                        >
                                            <Download className="w-4 h-4" />
                                        </a>
                                    ) : (
                                        <div className="p-2 text-gray-600">
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

export default History;
