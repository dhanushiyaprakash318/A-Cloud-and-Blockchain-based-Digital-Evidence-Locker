import React, { useEffect, useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  ScanFace,
  ShieldCheck,
  ShieldAlert,
  Image as ImageIcon,
  Link as LinkIcon,
  AlertTriangle,
} from 'lucide-react';
import { deepfake } from '@/services/api';

type MediaResult = {
  prediction: 'REAL' | 'FAKE';
  confidence: number;
  media_type: string;
  frames_analyzed: number | null;
  processing_time: string;
};

type UrlResult = {
  classification: string;
  confidence: number;
  risk_score: number;
  reason: string;
  hostname: string | null;
  is_https: boolean;
};

const DeepfakeDetection: React.FC = () => {
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null);

  // Media (image/video) state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [mediaResult, setMediaResult] = useState<MediaResult | null>(null);
  const [mediaError, setMediaError] = useState<string | null>(null);

  // URL state
  const [urlInput, setUrlInput] = useState('');
  const [checkingUrl, setCheckingUrl] = useState(false);
  const [urlResult, setUrlResult] = useState<UrlResult | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);

  useEffect(() => {
    deepfake
      .health()
      .then(() => setServiceOnline(true))
      .catch(() => setServiceOnline(false));
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    if (!selectedFile.type.startsWith('image/')) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setMediaError(null);
    setMediaResult(null);
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleAnalyzeMedia = async () => {
    if (!selectedFile) {
      setMediaError('Please choose an image or video to analyze.');
      return;
    }

    const isImage = selectedFile.type.startsWith('image/');
    const isVideo = selectedFile.type.startsWith('video/');
    if (!isImage && !isVideo) {
      setMediaError('Unsupported file type. Please select an image or video file.');
      return;
    }

    setMediaError(null);
    setMediaResult(null);
    setAnalyzing(true);
    try {
      const result = (isVideo
        ? await deepfake.checkVideo(selectedFile)
        : await deepfake.checkImage(selectedFile)) as MediaResult;
      setMediaResult(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Deepfake service unavailable.';
      setMediaError(`Analysis failed: ${message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleCheckUrl = async () => {
    if (!urlInput.trim()) {
      setUrlError('Please enter a URL to analyze.');
      return;
    }
    setUrlError(null);
    setUrlResult(null);
    setCheckingUrl(true);
    try {
      const result = (await deepfake.checkUrl(urlInput.trim())) as UrlResult;
      setUrlResult(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Deepfake service unavailable.';
      setUrlError(`URL check failed: ${message}`);
    } finally {
      setCheckingUrl(false);
    }
  };

  // For image/video: confidence is the FAKE probability (0-100). "Real" confidence = 100 - it.
  const isFake = mediaResult?.prediction === 'FAKE';
  const fakePct = mediaResult ? mediaResult.confidence : 0;
  const displayConfidence = isFake ? fakePct : 100 - fakePct;

  const urlSuspicious = urlResult
    ? urlResult.classification.toUpperCase() !== 'SAFE'
    : false;

  return (
    <Layout>
      <div className="container py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-slate-950 text-primary">
                <ScanFace className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">Deepfake Detection</h1>
                <p className="text-sm text-muted-foreground">
                  Standalone analysis tool — check any image, video, or website URL for manipulation.
                  Not tied to any case.
                </p>
              </div>
            </div>

            {serviceOnline === false && (
              <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Deepfake detection service is offline (expected at localhost:8001). Start the service to run analysis.
              </div>
            )}
          </div>

          <Tabs defaultValue="media" className="w-full">
            <TabsList className="grid grid-cols-2 w-full max-w-md">
              <TabsTrigger value="media" className="flex items-center gap-2">
                <ImageIcon className="h-4 w-4" /> Image / Video
              </TabsTrigger>
              <TabsTrigger value="url" className="flex items-center gap-2">
                <LinkIcon className="h-4 w-4" /> Website URL
              </TabsTrigger>
            </TabsList>

            {/* ── Image / Video ── */}
            <TabsContent value="media" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Analyze Image or Video</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-foreground">Media File</label>
                    <input
                      type="file"
                      accept="image/*,video/*"
                      onChange={handleFileChange}
                      className="mt-3 w-full cursor-pointer rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                    />
                    {selectedFile && (
                      <p className="mt-2 text-sm text-muted-foreground">Selected: {selectedFile.name}</p>
                    )}
                  </div>

                  {previewUrl && (
                    <img
                      src={previewUrl}
                      alt="preview"
                      className="max-h-64 rounded-lg border border-border object-contain"
                    />
                  )}

                  {mediaError && (
                    <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                      {mediaError}
                    </div>
                  )}

                  <Button onClick={handleAnalyzeMedia} disabled={analyzing} className="min-w-[180px]">
                    {analyzing ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" /> Analyzing...
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2">
                        <ScanFace className="h-4 w-4" /> Run Detection
                      </span>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {mediaResult && (
                <Card
                  className={
                    isFake
                      ? 'mt-4 border-destructive/30 bg-destructive/5'
                      : 'mt-4 border-green-500/20 bg-green-950/5'
                  }
                >
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {isFake ? (
                        <>
                          <ShieldAlert className="h-5 w-5 text-destructive" />
                          <span className="text-destructive">Likely Deepfake / Manipulated</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="h-5 w-5 text-green-500" />
                          <span className="text-green-500">Appears Authentic</span>
                        </>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-border/50 bg-background p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Verdict</p>
                        <p className="mt-2 text-lg font-semibold">
                          {mediaResult.prediction} · {displayConfidence.toFixed(1)}% confidence
                        </p>
                      </div>
                      <div className="rounded-xl border border-border/50 bg-background p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Details</p>
                        <p className="mt-2 text-sm">
                          {mediaResult.media_type}
                          {mediaResult.frames_analyzed != null && ` · ${mediaResult.frames_analyzed} frames`}
                          {` · ${mediaResult.processing_time}`}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* ── Website URL ── */}
            <TabsContent value="url" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle>Analyze Website URL</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-foreground">URL</label>
                    <Input
                      value={urlInput}
                      placeholder="https://example.com/page"
                      onChange={(e) => setUrlInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleCheckUrl()}
                      className="mt-3"
                    />
                  </div>

                  {urlError && (
                    <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                      {urlError}
                    </div>
                  )}

                  <Button onClick={handleCheckUrl} disabled={checkingUrl} className="min-w-[180px]">
                    {checkingUrl ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" /> Checking...
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2">
                        <LinkIcon className="h-4 w-4" /> Check URL
                      </span>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {urlResult && (
                <Card
                  className={
                    urlSuspicious
                      ? 'mt-4 border-destructive/30 bg-destructive/5'
                      : 'mt-4 border-green-500/20 bg-green-950/5'
                  }
                >
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {urlSuspicious ? (
                        <>
                          <ShieldAlert className="h-5 w-5 text-destructive" />
                          <span className="text-destructive">Suspicious</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="h-5 w-5 text-green-500" />
                          <span className="text-green-500">Safe</span>
                        </>
                      )}
                      <Badge variant="outline" className="ml-2">
                        Risk {urlResult.risk_score}/100
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-border/50 bg-background p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Classification</p>
                        <p className="mt-2 text-lg font-semibold">
                          {urlResult.classification} · {urlResult.confidence.toFixed(1)}%
                        </p>
                      </div>
                      <div className="rounded-xl border border-border/50 bg-background p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Host</p>
                        <p className="mt-2 text-sm break-all">
                          {urlResult.hostname || 'Unknown'} · {urlResult.is_https ? 'HTTPS' : 'HTTP'}
                        </p>
                      </div>
                    </div>
                    <div className="rounded-xl border border-border/50 bg-background p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Reason</p>
                      <p className="mt-2 text-sm leading-6">{urlResult.reason}</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </Layout>
  );
};

export default DeepfakeDetection;
