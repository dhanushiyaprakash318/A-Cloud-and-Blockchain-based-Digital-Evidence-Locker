import React, { useState, useCallback } from 'react';
import { Layout } from '@/components/layout/Layout';
import { useDropzone } from 'react-dropzone';
import { Upload, File as FileIcon, AlertTriangle, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import axios from 'axios';
import Lottie from 'lottie-react';
import faceRecognitionData from '../assets/face recognition.json';

// Types for the analysis result
interface AnalysisResult {
    id?: string;
    filename?: string;
    media_type?: string;
    prediction?: string;
    classification?: string;
    confidence: number;
    efficientnet_score?: number;
    swin_score?: number;
    xception_score?: number;
    resnet_score?: number;
    frames_analyzed?: number | null;
    faces_detected?: number;
    source_url?: string;
    uploaded_at?: string;
    processing_time?: number | string;
    risk_score?: number;
    reason?: string;
    hostname?: string;
    is_https?: boolean;
}

const DeepfakeDetector: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'upload' | 'url'>('upload');
    const [urlInput, setUrlInput] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [preview, setPreview] = useState<string | null>(null);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const f = acceptedFiles[0];
        setFile(f);
        setResult(null);
        setError(null);

        // Create preview URL for images/videos
        if (f.type.startsWith('image/') || f.type.startsWith('video/')) {
            const objectUrl = URL.createObjectURL(f);
            setPreview(objectUrl);
        } else {
            setPreview(null);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': [],
            'video/*': []
        }
    });

    const getDeepfakeError = (err: unknown): string => {
        const axiosError = axios.isAxiosError(err) ? err : null;
        if (!axiosError) {
            return 'Deepfake Service Unavailable.';
        }

        if (!axiosError.response) {
            return 'Deepfake Service Unavailable.';
        }

        const detail = axiosError.response.data?.detail || axiosError.response.data?.error || axiosError.response.data?.reason;
        if (detail) {
            return String(detail);
        }

        if (axiosError.response.status >= 500) {
            return 'Deepfake Service Unavailable.';
        }

        return 'Deepfake analysis failed. Please retry.';
    };

    const handleAnalyze = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);
        setResult(null);

        const fileType = file.type;
        let endpoint = '';

        if (fileType.startsWith('image/')) {
            endpoint = 'http://localhost:8001/predict/image';
        } else if (fileType.startsWith('video/')) {
            endpoint = 'http://localhost:8001/predict/video';
        } else {
            setError('Only image and video files are supported for deepfake analysis.');
            setLoading(false);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await axios.post(endpoint, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResult(res.data as AnalysisResult);
        } catch (err) {
            console.error(err);
            setError(getDeepfakeError(err));
        } finally {
            setLoading(false);
        }
    };

    const handleUrlAnalyze = async () => {
        if (!urlInput) return;
        setLoading(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('url', urlInput);

        try {
            const res = await axios.post('http://localhost:8001/predict/url', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResult(res.data as AnalysisResult);
        } catch (err) {
            console.error(err);
            setError(getDeepfakeError(err));
        } finally {
            setLoading(false);
        }
    };

    const getResultAsset = () => {
        if (!result) return null;

        const isWebsite = !!result.classification;
        const isReal = isWebsite
            ? result.classification === 'REAL'
            : result.prediction?.toUpperCase() === 'REAL';

        const label = isWebsite ? result.classification : result.prediction;
        const confidence = result.confidence;

        return (
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-500">
                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold ${isReal ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                    {isReal ? '✔ REAL' : '❌ FAKE'}
                </div>
                <img
                    src={isReal ? '/assets/Videos/man.gif' : '/assets/Videos/ai-assistant.gif'}
                    alt={isReal ? 'Real' : 'Fake'}
                    className={`w-64 h-64 object-contain mb-4 rounded-xl shadow-lg border-4 ${isReal ? 'border-green-500/50' : 'border-red-500/50'}`}
                />
                <div className={`text-3xl font-bold flex items-center gap-2 ${isReal ? 'text-green-500' : 'text-red-500'}`}>
                    {isReal ? <CheckCircle className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />} {label}
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                    {result.media_type ? `Type: ${result.media_type}` : isWebsite ? 'Type: WEBSITE' : 'Type: UNKNOWN'}
                </p>
                <p className="text-muted-foreground mt-2 text-center font-semibold">
                    {isWebsite ? `Risk Score: ${result.risk_score ?? 0}%` : `Confidence: ${confidence.toFixed(1)}%`}
                </p>
                <p className="text-muted-foreground mt-2 text-center">
                    {result.faces_detected !== undefined && result.faces_detected !== null ? `Faces: ${result.faces_detected}` : ''}
                    {result.frames_analyzed ? ` · Frames: ${result.frames_analyzed}` : ''}
                </p>
                <p className="text-muted-foreground mt-2 text-sm">
                    {isWebsite
                        ? `Reason: ${result.reason ?? 'N/A'}`
                        : `Processing Time: ${typeof result.processing_time === 'number' ? result.processing_time.toFixed(2) + 's' : result.processing_time ?? '0s'}`}
                </p>
                {isWebsite && result.hostname && (
                    <p className="text-muted-foreground mt-1 text-sm">Host: {result.hostname} · HTTPS: {result.is_https ? 'Yes' : 'No'}</p>
                )}
            </div>
        );
    };

    return (
        <Layout>
            <div className="container mx-auto py-12 px-4 max-w-5xl">
                <header className="mb-12 text-center space-y-4">
                    <h1 className="text-5xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
                        Deepfake Inspector
                    </h1>
                    <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                        Advanced forensic analysis for digital media. Detect AI-generated content with state-of-the-art neural networks.
                    </p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">

                    {/* Input Section */}
                    <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-8 shadow-2xl">

                        {/* Tabs */}
                        <div className="flex gap-4 mb-6 border-b border-white/10 pb-2">
                            <button
                                onClick={() => setActiveTab('upload')}
                                className={`text-lg font-semibold px-4 py-2 rounded-lg transition-all ${activeTab === 'upload' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-white'}`}
                            >
                                <Upload className="w-5 h-5 inline mr-2" /> Upload File
                            </button>
                            <button
                                onClick={() => setActiveTab('url')}
                                className={`text-lg font-semibold px-4 py-2 rounded-lg transition-all ${activeTab === 'url' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-white'}`}
                            >
                                <Loader2 className="w-5 h-5 inline mr-2" /> Paste URL
                            </button>
                        </div>

                        {activeTab === 'upload' ? (
                            <>
                                <div
                                    {...getRootProps()}
                                    className={`
                        border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300
                        flex flex-col items-center justify-center min-h-[300px]
                        ${isDragActive ? 'border-primary bg-primary/10 scale-[1.02]' : 'border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/5'}
                    `}
                                >
                                    <input {...getInputProps()} />
                                    {file ? (
                                        <div className="space-y-4">
                                            {preview && (
                                                file.type.startsWith('video') ?
                                                    <video src={preview} className="max-h-48 mx-auto rounded shadow-md" controls /> :
                                                    <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded shadow-md" />
                                            )}
                                            <div className="flex items-center gap-2 justify-center text-lg font-medium">
                                                <FileIcon className="w-5 h-5" /> {file.name}
                                            </div>
                                            <p className="text-sm text-muted-foreground">Click to change file</p>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="w-20 h-20 bg-muted/20 rounded-full flex items-center justify-center mb-6">
                                                <Upload className="w-10 h-10 text-muted-foreground" />
                                            </div>
                                            <p className="text-xl font-medium mb-2">Drag & drop or Click to Upload</p>
                                            <p className="text-sm text-muted-foreground">
                                                Supports Images and Videos for deepfake analysis.
                                            </p>
                                        </>
                                    )}
                                </div>

                                {file && (
                                    <button
                                        onClick={handleAnalyze}
                                        disabled={loading}
                                        className="w-full mt-6 bg-primary hover:bg-primary/90 text-primary-foreground font-bold text-lg py-4 rounded-xl shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                                    >
                                        {loading ? <Loader2 className="animate-spin w-6 h-6" /> : "Analyze File"}
                                    </button>
                                )}
                            </>
                        ) : (
                            <>
                                <div className="space-y-6 min-h-[300px] flex flex-col justify-center">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Media URL</label>
                                        <input
                                            type="text"
                                            placeholder="https://example.com/video.mp4"
                                            className="w-full bg-black/20 border border-white/10 rounded-xl p-4 text-lg focus:outline-none focus:border-primary/50 transition-all"
                                            value={urlInput}
                                            onChange={(e) => setUrlInput(e.target.value)}
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            Supports direct links to Images, Videos, or YouTube/Social Media posts.
                                        </p>
                                    </div>

                                    <button
                                        onClick={handleUrlAnalyze}
                                        disabled={loading || !urlInput}
                                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-lg py-4 rounded-xl shadow-lg transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                                    >
                                        {loading ? <Loader2 className="animate-spin w-6 h-6" /> : "Analyze from URL"}
                                    </button>
                                </div>
                            </>
                        )}

                        {error && (
                            <div className="mt-6 p-4 bg-destructive/10 text-destructive rounded-lg flex items-center gap-3 border border-destructive/20">
                                <AlertCircle className="w-5 h-5" /> {error}
                            </div>
                        )}
                    </div>

                    {/* Result Section */}
                    <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-8 shadow-2xl min-h-[500px] flex flex-col relative overflow-hidden">

                        <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2 z-10">
                            <CheckCircle className="w-6 h-6 text-primary" /> Analysis Result
                        </h2>

                        <div className="flex-1 flex flex-col items-center justify-center z-10">
                            {loading ? (
                                <div className="text-center space-y-4">
                                    <div className="w-64 h-64 mx-auto">
                                        <Lottie animationData={faceRecognitionData} loop={true} />
                                    </div>
                                    <p className="text-xl font-medium animate-pulse text-primary">Scanning for artifacts...</p>
                                    <p className="text-sm text-muted-foreground">Analyzing compression traces and inconsistencies</p>
                                </div>
                            ) : result ? (
                                getResultAsset()
                            ) : (
                                <div className="text-center text-muted-foreground/50 space-y-4">
                                    <div className="w-32 h-32 border-4 border-dashed border-muted-foreground/20 rounded-full mx-auto flex items-center justify-center">
                                        <FileIcon className="w-12 h-12" />
                                    </div>
                                    <p>Results will appear here after analysis</p>
                                </div>
                            )}
                        </div>

                        {/* Background Decoration */}
                        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -z-0 translate-x-1/2 -translate-y-1/2 pointer-events-none" />
                        <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl -z-0 -translate-x-1/2 translate-y-1/2 pointer-events-none" />

                    </div>
                </div>

                {result && (
                    <div className="mt-12 grid grid-cols-1 md:grid-cols-4 gap-6 animate-in slide-in-from-bottom duration-700 delay-200">
                        <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                            <div className="text-sm text-muted-foreground mb-1">Confidence</div>
                            <div className={`text-3xl font-mono font-bold ${result.confidence > 50 ? 'text-red-400' : 'text-green-400'}`}>
                                {result.confidence.toFixed(1)}%
                            </div>
                        </div>
                        {result.efficientnet_score !== undefined && (
                            <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                                <div className="text-sm text-muted-foreground mb-1">EfficientNet Score</div>
                                <div className="text-3xl font-mono font-bold">{result.efficientnet_score.toFixed(1)}%</div>
                                <div className="w-full bg-muted/30 h-2 mt-3 rounded-full overflow-hidden">
                                    <div className="h-full bg-blue-500 transition-all duration-1000" style={{ width: `${result.efficientnet_score}%` }} />
                                </div>
                            </div>
                        )}
                        {result.resnet_score !== undefined && (
                            <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                                <div className="text-sm text-muted-foreground mb-1">ResNet Score</div>
                                <div className="text-3xl font-mono font-bold">{result.resnet_score.toFixed(1)}%</div>
                                <div className="w-full bg-muted/30 h-2 mt-3 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 transition-all duration-1000" style={{ width: `${result.resnet_score}%` }} />
                                </div>
                            </div>
                        )}
                        {result.xception_score !== undefined && (
                            <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                                <div className="text-sm text-muted-foreground mb-1">Xception Score</div>
                                <div className="text-3xl font-mono font-bold">{result.xception_score.toFixed(1)}%</div>
                                <div className="w-full bg-muted/30 h-2 mt-3 rounded-full overflow-hidden">
                                    <div className="h-full bg-purple-500 transition-all duration-1000" style={{ width: `${result.xception_score}%` }} />
                                </div>
                            </div>
                        )}
                        {result.risk_score !== undefined && (
                            <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                                <div className="text-sm text-muted-foreground mb-1">Website Risk Score</div>
                                <div className="text-3xl font-mono font-bold">{result.risk_score}%</div>
                            </div>
                        )}
                        {result.swin_score !== undefined && (
                            <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                                <div className="text-sm text-muted-foreground mb-1">Swin Score</div>
                                <div className="text-3xl font-mono font-bold">{result.swin_score.toFixed(1)}%</div>
                            </div>
                        )}
                        {result.processing_time !== undefined && (
                            <div className="bg-card/30 border border-border/50 p-6 rounded-xl">
                                <div className="text-sm text-muted-foreground mb-1">Processing Time</div>
                                <div className="text-3xl font-mono font-bold">{typeof result.processing_time === 'number' ? `${result.processing_time.toFixed(2)}s` : result.processing_time}</div>
                            </div>
                        )}
                    </div>
                )}

            </div>
        </Layout>
    );
};

export default DeepfakeDetector;
