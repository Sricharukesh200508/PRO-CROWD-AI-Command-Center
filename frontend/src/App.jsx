import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Camera, Upload, AlertTriangle, Activity, Users, Play, Pause, Loader2, Download, Settings, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const API_URL = `${BASE_URL}/analyze`;
const VIDEO_UPLOAD_URL = `${BASE_URL}/upload_video`;
const VIDEO_FEED_URL = `${BASE_URL}/video_feed`;
const STATS_URL = `${BASE_URL}/current_count`;
const REPORT_URL = `${BASE_URL}/download_report`;
const HISTORY_URL = `${BASE_URL}/history`;
const SESSION_URL = `${BASE_URL}/video_history`;
const CLEAR_HISTORY_URL = `${BASE_URL}/clear_history`;

function App() {
    const [source, setSource] = useState('image'); // 'image' | 'video' | 'history'
    const [threshold, setThreshold] = useState(500);
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [history, setHistory] = useState([]);
    const [dbHistory, setDbHistory] = useState({ images: [], sessions: [] });
    const [isLive, setIsLive] = useState(false);
    const [speed, setSpeed] = useState(1.0);
    const [modelType, setModelType] = useState('CSRNet'); // 'CSRNet' | 'YOLO'
    const [selectedSession, setSelectedSession] = useState(null);
    const [sessionTimeline, setSessionTimeline] = useState([]);

    const intervalRef = useRef(null);

    // Reset state on source change
    useEffect(() => {
        if (source !== 'history') {
            setFile(null);
            setPreview(null);
            setResult(null);
            setHistory([]);
            setIsLive(false);
            if (intervalRef.current) clearInterval(intervalRef.current);
        } else {
            fetchHistory();
        }
    }, [source]);

    // Restart stream when speed changes
    useEffect(() => {
        if (isLive && source === 'video') {
            setPreview(`${VIDEO_FEED_URL}?speed=${speed}&threshold=${threshold}&model_type=${modelType}&t=${Date.now()}`);
        }
    }, [speed, threshold, modelType]);

    const handleFileChange = async (e) => {
        const selected = e.target.files[0];
        if (selected) {
            setFile(selected);
            setResult(null);
            setHistory([]);

            if (source === 'image') {
                setPreview(URL.createObjectURL(selected));
            } else if (source === 'video') {
                setLoading(true);
                const formData = new FormData();
                formData.append('video', selected);
                try {
                    await axios.post(VIDEO_UPLOAD_URL, formData);
                    setPreview(null);
                    alert("Video uploaded! Click 'Start Live Feed' to begin analysis.");
                } catch (err) {
                    console.error(err);
                    alert("Failed to upload video.");
                } finally {
                    setLoading(false);
                }
            }
        }
    };

    const pollStats = async () => {
        try {
            const res = await axios.get(STATS_URL);
            const data = res.data;

            setResult(data);

            setHistory(prev => {
                const newHistory = [...prev, {
                    time: new Date().toLocaleTimeString(),
                    count: data.count,
                    pressure: data.pressure,
                    cpi: data.cpi * 100 // Convert to percentage for the chart
                }];
                return newHistory.slice(-50);
            });

            if (!res.data.is_streaming && isLive) {
                setIsLive(false);
                clearInterval(intervalRef.current);
            }
        } catch (err) {
            console.error("Stats poll error", err);
        }
    };

    const toggleLive = () => {
        if (isLive) {
            setIsLive(false);
            setPreview(null);
            if (intervalRef.current) clearInterval(intervalRef.current);
        } else {
            setIsLive(true);
            const isWebcamStr = source === 'webcam' ? 'true' : 'false';
            setPreview(`${VIDEO_FEED_URL}?speed=${speed}&threshold=${threshold}&webcam=${isWebcamStr}&t=${Date.now()}`);
            intervalRef.current = setInterval(pollStats, 800);
        }
    };

    const analyzeImage = async () => {
        if (!file) return;
        setLoading(true);
        const formData = new FormData();
        formData.append('image', file);
        formData.append('threshold', threshold);
        formData.append('model_type', modelType);

        try {
            const res = await axios.post(API_URL, formData);
            setResult(res.data);
        } catch (err) {
            console.error(err);
            alert("Analysis failed. Ensure backend is running.");
        } finally {
            setLoading(false);
        }
    };

    const downloadReport = () => {
        window.open(REPORT_URL, '_blank');
    };

    const fetchHistory = async () => {
        setLoading(true);
        try {
            const res = await axios.get(HISTORY_URL);
            setDbHistory(res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const fetchSessionTimeline = async (sessionId) => {
        setLoading(true);
        try {
            const res = await axios.get(`${SESSION_URL}/${sessionId}`);
            setSessionTimeline(res.data);
            setSelectedSession(sessionId);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const clearHistory = async () => {
        if (!window.confirm("Are you sure you want to clear all historical data?")) return;
        try {
            await axios.post(CLEAR_HISTORY_URL);
            fetchHistory();
            setSelectedSession(null);
            setSessionTimeline([]);
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="min-h-screen bg-background text-gray-100 font-sans flex">
            {/* Sidebar */}
            <aside className="w-80 bg-card/50 backdrop-blur border-r border-white/5 p-6 flex flex-col gap-8 h-screen sticky top-0 overflow-y-auto custom-scrollbar">
                <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                        PRO-CROWD
                    </h1>
                    <p className="text-xs text-gray-400 mt-1">AI Disaster Prevention</p>
                </div>

                <div className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-400">Input Source</label>
                        <div className="flex bg-black/20 rounded-lg p-1">
                            <button
                                onClick={() => setSource('image')}
                                className={clsx(
                                    "flex-1 py-2 rounded-md text-[10px] font-medium transition-all",
                                    source === 'image' ? "bg-accent text-white shadow-lg shadow-blue-500/20" : "text-gray-400 hover:text-white"
                                )}
                            >
                                Image
                            </button>
                            <button
                                onClick={() => setSource('video')}
                                className={clsx(
                                    "flex-1 py-2 rounded-md text-[10px] font-medium transition-all",
                                    source === 'video' ? "bg-accent text-white shadow-lg shadow-blue-500/20" : "text-gray-400 hover:text-white"
                                )}
                            >
                                Video
                            </button>
                            <button
                                onClick={() => setSource('webcam')}
                                className={clsx(
                                    "flex-1 py-2 rounded-md text-[10px] font-medium transition-all",
                                    source === 'webcam' ? "bg-accent text-white shadow-lg shadow-blue-500/20" : "text-gray-400 hover:text-white"
                                )}
                            >
                                Webcam
                            </button>
                            <button
                                onClick={() => setSource('history')}
                                className={clsx(
                                    "flex-1 py-2 rounded-md text-[10px] font-medium transition-all",
                                    source === 'history' ? "bg-accent text-white shadow-lg shadow-blue-500/20" : "text-gray-400 hover:text-white"
                                )}
                            >
                                History
                            </button>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="flex justify-between">
                            <label className="text-sm font-medium text-gray-400">Risk Threshold</label>
                            <span className="text-sm font-bold text-accent">{threshold}</span>
                        </div>
                        <input
                            type="range"
                            min="50"
                            max="2000"
                            value={threshold}
                            onChange={(e) => setThreshold(Number(e.target.value))}
                            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        />
                    </div>

                    {source === 'video' && (
                        <div className="space-y-4 animate-fade-in">
                            <div className="flex justify-between">
                                <label className="text-sm font-medium text-gray-400 flex items-center gap-2">
                                    <Settings size={14} /> Playback Speed
                                </label>
                                <span className="text-sm font-bold text-green-400">{speed}x</span>
                            </div>
                            <input
                                type="range"
                                min="0.5"
                                max="3.0"
                                step="0.5"
                                value={speed}
                                onChange={(e) => setSpeed(Number(e.target.value))}
                                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                            />
                            <p className="text-xs text-gray-500">Adjust speed for faster/slower analysis</p>
                        </div>
                    )}



                    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                        <h3 className="text-sm font-medium text-gray-400 mb-2">System Status</h3>
                        <div className="flex items-center gap-2 text-green-400 text-sm">
                            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                            Backend Active
                        </div>
                        {isLive && (
                            <div className="mt-2 flex items-center gap-2 text-blue-400 text-xs">
                                <Loader2 className="w-3 h-3 animate-spin" /> Streaming @ {speed}x
                            </div>
                        )}
                    </div>

                    <button
                        onClick={downloadReport}
                        className="w-full py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center gap-2 text-sm font-medium transition-all hover:scale-[1.02]"
                    >
                        <Download size={16} /> Download Report
                    </button>

                    {source === 'history' && (
                        <button
                            onClick={clearHistory}
                            className="w-full py-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 flex items-center justify-center gap-2 text-sm font-medium text-red-400 transition-all hover:scale-[1.02]"
                        >
                            <RefreshCw size={16} /> Clear History
                        </button>
                    )}
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 p-8 overflow-y-auto">
                {source !== 'history' ? (
                    <>
                        {/* Stats Row */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                            <StatsCard
                                icon={<Users className="w-6 h-6 text-blue-400" />}
                                label="Headcount"
                                value={result ? result.count : '--'}
                                subtext={result?.tier === "CRITICAL" ? "OVER CAPACITY" : result?.tier === "WARNING" ? "NEAR CAPACITY" : "NORMAL"}
                                alert={result?.tier === "CRITICAL"}
                            />
                            <StatsCard
                                icon={<Activity className="w-6 h-6 text-orange-400" />}
                                label="Crowd Pressure Index"
                                value={result ? result.cpi.toFixed(2) : '--'}
                                subtext={`${(result?.cpi * 100 || 0).toFixed(0)}% Capacity`}
                                alert={result?.cpi > 0.85}
                                color={result?.cpi > 0.85 ? "text-red-400" : result?.cpi > 0.7 ? "text-yellow-400" : "text-green-400"}
                            />
                            <StatsCard
                                icon={<Activity className="w-6 h-6 text-purple-400" />}
                                label="Safety Tier"
                                value={result ? result.tier : '--'}
                                subtext="Public Safety Model"
                                alert={result?.tier === "CRITICAL" || result?.tier === "WARNING"}
                                color={result?.tier === "CRITICAL" ? "text-red-500" : result?.tier === "WARNING" ? "text-orange-400" : result?.tier === "ELEVATED" ? "text-blue-400" : "text-green-400"}
                            />
                            <StatsCard
                                icon={<AlertTriangle className="w-6 h-6 text-yellow-400" />}
                                label="Recommendation"
                                value={result ? (result.tier === "SAFE" ? "OPTIMAL" : "ACTION REQ.") : '--'}
                                subtext="Protocol Priority"
                                alert={result?.tier !== "SAFE" && result !== null}
                            />
                        </div>

                        {/* Mitigation Banner */}
                        {result?.recommendation && result.tier !== "SAFE" && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className={clsx(
                                    "mb-8 p-4 rounded-xl border flex items-center gap-4",
                                    result.tier === "CRITICAL" ? "bg-red-500/10 border-red-500/50 text-red-200" :
                                        result.tier === "WARNING" ? "bg-orange-500/10 border-orange-500/50 text-orange-200" :
                                            "bg-blue-500/10 border-blue-500/50 text-blue-200"
                                )}
                            >
                                <div className={clsx(
                                    "p-2 rounded-lg",
                                    result.tier === "CRITICAL" ? "bg-red-500 text-white" : "bg-orange-500 text-white"
                                )}>
                                    <AlertTriangle size={20} />
                                </div>
                                <div className="flex-1">
                                    <h4 className="font-bold text-sm uppercase tracking-wider">{result.tier} PROTOCOL ACTIVE</h4>
                                    <p className="text-sm opacity-90">{result.recommendation}</p>
                                </div>
                            </motion.div>
                        )}

                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 h-[600px]">
                            {/* Main Viewport (Spans 2 columns) */}
                            <div className="lg:col-span-2 bg-card/30 backdrop-blur rounded-2xl border border-white/5 overflow-hidden flex flex-col relative group">
                                <div className="absolute top-4 left-4 z-10 flex gap-2">
                                    <span className="bg-black/50 backdrop-blur px-3 py-1 rounded-full text-xs font-medium border border-white/10 uppercase">
                                        {source} Analysis
                                    </span>
                                    {source === 'video' && isLive && (
                                        <span className="bg-red-500/80 backdrop-blur px-3 py-1 rounded-full text-xs font-medium text-white animate-pulse flex items-center gap-1">
                                            <div className="w-2 h-2 bg-white rounded-full animate-ping" /> LIVE
                                        </span>
                                    )}
                                    {result?.model_name && (
                                        <span className={clsx(
                                            "backdrop-blur px-3 py-1 rounded-full text-xs font-bold border border-white/10",
                                            result.model_name.includes('YOLO') ? "bg-orange-500/20 text-orange-400" : "bg-blue-500/20 text-blue-400"
                                        )}>
                                            {result.model_name}
                                        </span>
                                    )}
                                </div>

                                <div className="flex-1 flex items-center justify-center bg-black/40 relative">
                                    {!file && source !== 'webcam' ? (
                                        <label className="cursor-pointer flex flex-col items-center gap-4 text-gray-500 hover:text-white transition-colors">
                                            <Upload className="w-12 h-12" />
                                            <span className="font-medium">Click to Upload {source === 'image' ? 'Image' : 'Video'}</span>
                                            <input type="file" className="hidden" accept={source === 'image' ? "image/*" : "video/mp4,video/avi,video/*"} onChange={handleFileChange} />
                                        </label>
                                    ) : (
                                        source === 'image' ? (
                                            <img src={preview} className="max-w-full max-h-full object-contain" />
                                        ) : (
                                            (isLive || source === 'webcam' && isLive) ? (
                                                <img src={preview} className="max-w-full max-h-full object-contain" />
                                            ) : (
                                                <div className="flex flex-col items-center gap-2 text-gray-400">
                                                    <Play size={48} />
                                                    <span>{source === 'webcam' ? 'Webcam Ready' : 'Video Ready'}. Press Start.</span>
                                                </div>
                                            )
                                        )
                                    )}
                                </div>

                                {/* Controls */}
                                <div className="h-16 bg-card/80 border-t border-white/5 flex items-center justify-between px-6">
                                    <button
                                        onClick={() => setFile(null)}
                                        className="text-sm text-gray-400 hover:text-white transition-colors"
                                    >
                                        Change Input
                                    </button>
                                    {source === 'image' && file && (
                                        <button
                                            onClick={analyzeImage}
                                            disabled={loading}
                                            className="bg-accent hover:bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                                        >
                                            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                                            {loading ? "Analyzing..." : "Run Analysis"}
                                        </button>
                                    )}
                                    {(source === 'video' && file || source === 'webcam') && (
                                        <button
                                            onClick={toggleLive}
                                            disabled={loading}
                                            className={clsx(
                                                "px-6 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2",
                                                isLive ? "bg-red-500 hover:bg-red-600 text-white" : "bg-green-500 hover:bg-green-600 text-white"
                                            )}
                                        >
                                            {isLive ? <Pause size={16} /> : <Play size={16} />}
                                            {isLive ? "Stop Stream" : "Start Live Feed"}
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Right Column: Density Map + Chart */}
                            <div className="flex flex-col gap-6">
                                {/* Density Map / Live Feed Info */}
                                <div className="flex-1 bg-card/30 backdrop-blur rounded-2xl border border-white/5 overflow-hidden flex flex-col relative min-h-[200px]">
                                    <div className="absolute top-4 left-4 z-10">
                                        <span className="bg-black/50 backdrop-blur px-3 py-1 rounded-full text-xs font-medium border border-white/10">
                                            {source === 'video' ? "Stream Output" : "Heatmap Visualization"}
                                        </span>
                                    </div>
                                    <div className="flex-1 flex items-center justify-center bg-black/40">
                                        {source === 'image' && result?.density_map ? (
                                            <img src={`data:image/png;base64,${result.density_map}`} className="max-w-full max-h-full object-contain filter contrast-125 transition-opacity duration-200" />
                                        ) : source === 'video' ? (
                                            <div className="text-center p-6 text-gray-400">
                                                <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                                <p className="text-sm">Live Heatmap is overlaid on the main video stream.</p>
                                            </div>
                                        ) : (
                                            <div className="text-gray-500 text-sm flex flex-col items-center gap-2">
                                                <Activity className="w-8 h-8 opacity-50" />
                                                <span>Awaiting Analysis Data</span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Live Chart */}
                                <div className="flex-1 bg-card/30 backdrop-blur rounded-2xl border border-white/5 p-4 relative flex flex-col min-h-[250px]">
                                    <div className="flex justify-between items-center mb-4">
                                        <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider">Crowd Density - Live Trend</h4>
                                        <span className="text-xs text-green-400 flex items-center gap-1">
                                            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span> UDP Real-time
                                        </span>
                                    </div>
                                    <div className="flex-1 min-h-0">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={history.length > 0 ? history : [{ time: '', count: 0 }]}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                                                <XAxis dataKey="time" hide />
                                                <YAxis domain={[0, 'auto']} stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#fff' }}
                                                    itemStyle={{ color: '#3b82f6' }}
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey="count"
                                                    stroke="#3b82f6"
                                                    strokeWidth={3}
                                                    dot={false}
                                                    isAnimationActive={true}
                                                    animationDuration={500}
                                                    name="Headcount"
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey="pressure"
                                                    stroke="#f97316"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    isAnimationActive={true}
                                                    animationDuration={500}
                                                    name="Pressure Index"
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey={() => threshold}
                                                    stroke="#ef4444"
                                                    strokeDasharray="5 5"
                                                    strokeWidth={2}
                                                    dot={false}
                                                    isAnimationActive={false}
                                                    name="Threshold"
                                                />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    /* History View */
                    <div className="space-y-8 animate-fade-in">
                        <div className="flex justify-between items-end">
                            <div>
                                <h2 className="text-3xl font-bold text-white">Analysis History</h2>
                                <p className="text-gray-400">Review past performance and data trends</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            {/* Image History Table */}
                            <div className="bg-card/30 backdrop-blur rounded-2xl border border-white/5 p-6 h-[400px] flex flex-col">
                                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                                    <Camera size={18} className="text-blue-400" /> Image Analyses
                                </h3>
                                <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
                                    <table className="w-full text-left text-sm">
                                        <thead className="text-gray-500 border-b border-white/5 sticky top-0 bg-background/50 backdrop-blur z-10">
                                            <tr>
                                                <th className="pb-3">Time</th>
                                                <th className="pb-3 text-center">Count</th>
                                                <th className="pb-3 text-center">CPI</th>
                                                <th className="pb-3 text-right">Tier</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {dbHistory.images.map(img => (
                                                <tr key={img.id} className="hover:bg-white/5 transition-colors">
                                                    <td className="py-3 text-gray-300">{new Date(img.timestamp).toLocaleString()}</td>
                                                    <td className="py-3 text-center font-bold text-blue-400">{img.count}</td>
                                                    <td className="py-3 text-center text-orange-400">{img.cpi.toFixed(2)}</td>
                                                    <td className="py-3 text-right">
                                                        <span className={clsx(
                                                            "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                                                            img.tier === 'CRITICAL' ? "bg-red-500/20 text-red-400" :
                                                                img.tier === 'WARNING' ? "bg-orange-500/20 text-orange-400" : "bg-blue-500/20 text-blue-400"
                                                        )}>
                                                            {img.tier}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                            {dbHistory.images.length === 0 && (
                                                <tr><td colSpan="4" className="py-10 text-center text-gray-500">No image history found</td></tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Video Sessions List */}
                            <div className="bg-card/30 backdrop-blur rounded-2xl border border-white/5 p-6 h-[400px] flex flex-col">
                                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                                    <Play size={18} className="text-green-400" /> Video Sessions
                                </h3>
                                <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-3">
                                    {dbHistory.sessions.map(s => (
                                        <div
                                            key={s.id}
                                            onClick={() => fetchSessionTimeline(s.id)}
                                            className={clsx(
                                                "p-4 rounded-xl border transition-all cursor-pointer",
                                                selectedSession === s.id ? "bg-blue-500/10 border-blue-500/30" : "bg-white/5 border-white/5 hover:border-white/10"
                                            )}
                                        >
                                            <div className="flex justify-between items-center">
                                                <span className="text-sm font-medium text-gray-200">Session #{s.id}</span>
                                                <span className="text-xs text-gray-500">{new Date(s.session_start).toLocaleString()}</span>
                                            </div>
                                            <p className="text-[10px] text-gray-400 mt-1 uppercase tracking-widest">{s.filename}</p>
                                        </div>
                                    ))}
                                    {dbHistory.sessions.length === 0 && (
                                        <div className="py-10 text-center text-gray-500">No video sessions found</div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Selected Session Detail Graph */}
                        {selectedSession && (
                            <div className="bg-card/30 backdrop-blur rounded-2xl border border-white/5 p-6 h-[400px] animate-fade-in">
                                <h3 className="text-lg font-bold mb-6">Session #{selectedSession} Timeline Analysis</h3>
                                <div className="h-[280px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={sessionTimeline}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                            <XAxis
                                                dataKey="timestamp_offset"
                                                type="number"
                                                tickFormatter={(val) => val.toFixed(1) + 's'}
                                                stroke="#4b5563"
                                            />
                                            <YAxis stroke="#4b5563" />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                                                labelFormatter={(val) => `Time: ${val.toFixed(1)}s`}
                                            />
                                            <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={3} dot={false} name="Headcount" />
                                            <Line type="monotone" dataKey="cpi" stroke="#f97316" strokeWidth={2} dot={false} name="CPI Index" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </main>

            {/* Alert Overlay */}
            <AnimatePresence>
                {(result?.count > threshold || result?.pressure > 75) && (
                    <motion.div
                        initial={{ opacity: 0, y: -50 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -50 }}
                        className="fixed top-8 right-8 bg-red-500/90 backdrop-blur text-white p-6 rounded-xl shadow-2xl border border-red-400/50 flex items-center gap-4 z-50 max-w-sm"
                    >
                        <AlertTriangle className="w-8 h-8 animate-pulse" />
                        <div>
                            <h4 className="font-bold text-lg">CRITICAL ALERT</h4>
                            <p className="text-sm text-red-100">
                                {result?.pressure > 75 ? "Extreme crowd pressure detected! Crush risk high." : "Crowd density has exceeded safety threshold!"}
                            </p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

function StatsCard({ icon, label, value, subtext, alert, color }) {
    return (
        <div className={clsx(
            "bg-card/30 backdrop-blur p-6 rounded-2xl border transition-all duration-300",
            alert ? "border-red-500/50 shadow-lg shadow-red-500/10" : "border-white/5 hover:border-white/10"
        )}>
            <div className="flex items-start justify-between mb-4">
                <div className={clsx("p-3 rounded-lg", alert ? "bg-red-500/20" : "bg-white/5")}>
                    {icon}
                </div>
                {alert && <span className="animate-ping w-2 h-2 rounded-full bg-red-500"></span>}
            </div>
            <div>
                <h3 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent mb-1">
                    {value}
                </h3>
                <p className="text-sm font-medium text-gray-400 mb-1">{label}</p>
                <p className={clsx("text-xs font-semibold", color ? color : alert ? "text-red-400" : "text-blue-400")}>
                    {subtext}
                </p>
            </div>
        </div>
    );
}

export default App;
