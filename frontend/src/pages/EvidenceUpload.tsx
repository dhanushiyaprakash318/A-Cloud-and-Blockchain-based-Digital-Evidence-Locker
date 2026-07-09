import React, { useEffect, useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Upload, CheckCircle2 } from 'lucide-react';
import { cases, evidence } from '@/services/api';
import type { Case } from '@/types/case';

const EvidenceUpload: React.FC = () => {
  const [caseId, setCaseId] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [availableCases, setAvailableCases] = useState<Case[]>([]);
  const [caseFetchError, setCaseFetchError] = useState<string | null>(null);

  useEffect(() => {
    const loadCases = async () => {
      try {
        const payload = await cases.list();
        setAvailableCases(payload.cases || []);
      } catch (err) {
        setCaseFetchError('Unable to load cases. Please enter a Case ID manually.');
      }
    };

    loadCases();
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!caseId.trim()) {
      setError('Case ID is required.');
      return;
    }

    if (!selectedFile) {
      setError('Please choose an evidence file to upload.');
      return;
    }

    setError(null);
    setResult(null);
    setUploading(true);

    try {
      const response = await evidence.upload(caseId.trim(), selectedFile);
      setResult(response);
    } catch (uploadError: unknown) {
      const message = uploadError instanceof Error ? uploadError.message : 'Upload failed.';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Layout>
      <div className="container py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-slate-950 text-primary">
                <Upload className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">Evidence Upload</h1>
                <p className="text-sm text-muted-foreground">Securely upload evidence and receive blockchain and AI summary results.</p>
              </div>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Upload Evidence</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-2">
                <div>
                  <label className="text-sm font-medium text-foreground">Case ID</label>
                  <div className="mt-2">
                    <Select value={caseId} onValueChange={(value) => setCaseId(value)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a case or type one" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableCases.length > 0 ? (
                          availableCases.map((caseItem) => (
                            <SelectItem key={caseItem.id} value={caseItem.id}>
                              {caseItem.caseNumber} — {caseItem.district}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="">No cases available</SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                  <Input
                    value={caseId}
                    placeholder="Enter Case ID manually"
                    onChange={(event) => setCaseId(event.target.value)}
                    className="mt-3"
                  />
                  {caseFetchError && <p className="text-sm text-destructive mt-2">{caseFetchError}</p>}
                </div>

                <div>
                  <label className="text-sm font-medium text-foreground">Evidence File</label>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
                    onChange={handleFileChange}
                    className="mt-3 w-full cursor-pointer rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                  />
                  {selectedFile && (
                    <p className="mt-2 text-sm text-muted-foreground">Selected file: {selectedFile.name}</p>
                  )}
                </div>
              </div>

              {error && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                  {error}
                </div>
              )}

              <div className="flex items-center gap-3">
                <Button onClick={handleUpload} disabled={uploading} className="min-w-[180px]">
                  {uploading ? (
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Uploading...
                    </span>
                  ) : (
                    'Upload Evidence'
                  )}
                </Button>
                <span className="text-sm text-muted-foreground">Supported: PDF, DOCX, TXT, JPG, PNG</span>
              </div>
            </CardContent>
          </Card>

          {result && (
            <Card className="border-green-500/20 bg-green-950/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-green-500">
                  <CheckCircle2 className="h-5 w-5" /> Evidence Uploaded Successfully
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-border/50 bg-background p-4">
                    <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Evidence ID</p>
                    <p className="mt-2 text-lg font-semibold">{result.evidence_id || 'N/A'}</p>
                  </div>
                  <div className="rounded-xl border border-border/50 bg-background p-4">
                    <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Blockchain Status</p>
                    <p className="mt-2 text-lg font-semibold">
                      {result.blockchain?.blockchain_status || result.blockchain?.tx_hash ? 'Verified' : 'Pending'}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-border/50 bg-background p-4">
                  <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">AI Summary</p>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground">
                    {result.generated_summary || 'No AI summary returned.'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default EvidenceUpload;
