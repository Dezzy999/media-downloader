import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, Music, Video, Sparkles, CheckCircle, AlertCircle, Loader2, Bot } from 'lucide-react';
import PlatformCard from './components/PlatformCard';
import DownloadModal from './components/DownloadModal';
import AIChatPanel from './components/AIChatPanel';
import History from './components/History';
import { YouTubeIcon, SpotifyIcon, TikTokFullIcon } from './components/PlatformIcons';
import LiquidEther from './components/LiquidEther';
import AIBubble from './components/AIBubble';
import { checkHealth, getTaskStatus } from './services/api';

function App() {
    const [selectedPlatform, setSelectedPlatform] = useState(null);
    const [serverStatus, setServerStatus] = useState('checking');
    const [downloads, setDownloads] = useState(() => {
        const saved = localStorage.getItem('downloadHistory');
        return saved ? JSON.parse(saved) : [];
    });
    const [isChatOpen, setIsChatOpen] = useState(false);

    useEffect(() => {
        const checkServer = async () => {
            try {
                await checkHealth();
                setServerStatus('online');
            } catch {
                setServerStatus('offline');
            }
        };
        checkServer();
        const interval = setInterval(checkServer, 30000);
        return () => clearInterval(interval);
    }, []);

    // Polling global para actualizar tareas pendientes en el historial
    useEffect(() => {
        const hasPending = downloads.some(d => d.fileId === null);
        if (!hasPending) return;

        const interval = setInterval(async () => {
            let needsUpdate = false;
            const updatedDownloads = await Promise.all(downloads.map(async (d) => {
                if (d.fileId === null) {
                    try {
                        const status = await getTaskStatus(d.id);
                        if (status.status === 'completed') {
                            needsUpdate = true;
                            return { ...d, fileId: status.file_id, filename: status.filename };
                        } else if (status.status === 'error') {
                            needsUpdate = true;
                            return { ...d, fileId: 'error' };
                        }
                    } catch (err) {
                        console.error('Error polling history task:', err);
                    }
                }
                return d;
            }));

            if (needsUpdate) {
                setDownloads(updatedDownloads);
                localStorage.setItem('downloadHistory', JSON.stringify(updatedDownloads));
            }
        }, 5000);

        return () => clearInterval(interval);
    }, [downloads]);

    const addToHistory = (download) => {
        const newDownloads = [download, ...downloads].slice(0, 20);
        setDownloads(newDownloads);
        localStorage.setItem('downloadHistory', JSON.stringify(newDownloads));
    };

    const platforms = [
        {
            id: 'youtube',
            name: 'YouTube',
            description: 'Videos y música en MP3, MP4, FLAC y más',
            icon: <YouTubeIcon className="w-14 h-14" />,
            gradient: 'from-red-500 via-red-600 to-red-700',
            hoverGlow: 'hover:shadow-red-500/30',
            formats: ['mp3', 'mp4', 'm4a', 'flac', 'wav'],
        },
        {
            id: 'spotify',
            name: 'Spotify',
            description: 'Canciones y playlists en alta calidad',
            icon: <SpotifyIcon className="w-14 h-14" />,
            gradient: 'from-green-500 via-green-600 to-emerald-600',
            hoverGlow: 'hover:shadow-green-500/30',
            formats: ['mp3', 'flac', 'm4a'],
        },
        {
            id: 'tiktok',
            name: 'TikTok',
            description: 'Videos sin marca de agua',
            icon: <TikTokFullIcon className="w-14 h-14" />,
            gradient: 'from-pink-500 via-purple-500 to-cyan-400',
            hoverGlow: 'hover:shadow-pink-500/30',
            formats: ['mp4', 'mp3'],
            badge: 'Sin Watermark',
        },
    ];

    return (
        <div className="min-h-screen relative overflow-hidden">
            {/* LiquidEther Background */}
            <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0 }}>
                <LiquidEther
                    colors={['#5227FF', '#FF9FFC', '#B19EEF']}
                    mouseForce={20}
                    cursorSize={100}
                    isViscous={false}
                    viscous={30}
                    iterationsViscous={32}
                    iterationsPoisson={32}
                    resolution={0.5}
                    isBounce={false}
                    autoDemo={true}
                    autoSpeed={0.5}
                    autoIntensity={2.2}
                    takeoverDuration={0.25}
                    autoResumeDelay={3000}
                    autoRampDuration={0.6}
                />
            </div>

            {/* Header */}
            <header className="relative z-10 pt-8 pb-6 px-4">
                <motion.div
                    initial={{ opacity: 0, y: -30 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-6xl mx-auto text-center"
                >
                    <div className="flex items-center justify-center gap-3 mb-4">
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                            className="w-14 h-14 rounded-2xl gradient-bg flex items-center justify-center glow"
                        >
                            <Download className="w-7 h-7 text-white" />
                        </motion.div>
                        <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-purple-300 bg-clip-text text-transparent glow-text">
                            MediaGrab
                        </h1>
                    </div>
                    <p className="text-gray-400 text-lg max-w-lg mx-auto">
                        Descarga videos y música de tus plataformas favoritas en segundos
                    </p>

                    {/* Server status */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                        className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm"
                    >
                        {serverStatus === 'checking' && (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                                <span className="text-gray-400">Verificando servidor...</span>
                            </>
                        )}
                        {serverStatus === 'online' && (
                            <>
                                <CheckCircle className="w-4 h-4 text-green-400" />
                                <span className="text-green-400">Servidor listo</span>
                            </>
                        )}
                        {serverStatus === 'offline' && (
                            <>
                                <AlertCircle className="w-4 h-4 text-red-400" />
                                <span className="text-red-400">Servidor desconectado</span>
                            </>
                        )}
                    </motion.div>
                </motion.div>
            </header>

            {/* Platform cards */}
            <main className="relative z-10 px-4 pb-12">
                <div className="max-w-6xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12"
                    >
                        {platforms.map((platform, index) => (
                            <PlatformCard
                                key={platform.id}
                                platform={platform}
                                index={index}
                                onClick={() => setSelectedPlatform(platform)}
                                disabled={serverStatus !== 'online'}
                            />
                        ))}
                    </motion.div>

                    {/* Features */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12"
                    >
                        {[
                            { icon: <Music className="w-5 h-5" />, text: 'Múltiples formatos' },
                            { icon: <Video className="w-5 h-5" />, text: 'Alta calidad' },
                            { icon: <Sparkles className="w-5 h-5" />, text: 'Sin marcas de agua' },
                            { icon: <Download className="w-5 h-5" />, text: 'Descarga rápida' },
                        ].map((feature, i) => (
                            <div
                                key={i}
                                className="glass rounded-xl p-4 text-center flex flex-col items-center gap-2"
                            >
                                <div className="text-purple-400">{feature.icon}</div>
                                <span className="text-sm text-gray-300">{feature.text}</span>
                            </div>
                        ))}
                    </motion.div>

                    {/* History */}
                    <History downloads={downloads} setDownloads={setDownloads} />
                </div>
            </main>

            {/* Download Modal */}
            <AnimatePresence>
                {selectedPlatform && (
                    <DownloadModal
                        platform={selectedPlatform}
                        onClose={() => setSelectedPlatform(null)}
                        onDownloadComplete={addToHistory}
                    />
                )}
            </AnimatePresence>

            {/* AIChatPanel */}
            <AIChatPanel
                isOpen={isChatOpen}
                onClose={() => setIsChatOpen(false)}
                onDownloadComplete={addToHistory}
            />

            {/* Floating AI Button */}
            {!isChatOpen && (
                <AIBubble onClick={() => setIsChatOpen(true)} />
            )}

            {/* Footer */}
            <footer className="relative z-10 py-6 text-center text-gray-500 text-sm">
                <p>
                    MediaGrab © {new Date().getFullYear()} — Uso personal únicamente
                </p>
            </footer>
        </div>
    );
}

export default App;
