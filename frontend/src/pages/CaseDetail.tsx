import React, { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { useRole } from '@/contexts/RoleContext';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft,
  MapPin,
  Calendar,
  User,
  FileText,
  Image,
  Video,
  Music,
  File,
  Brain,
  Info,
  Clock,
  ShieldCheck,
  Loader2,
  Network
} from 'lucide-react';
import { evidence as evidenceApi } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import KnowledgeGraph from '@/components/KnowledgeGraph';
import { BlockchainVerificationDialog } from '@/components/BlockchainVerificationDialog';

const statusColors: Record<string, string> = {
  'Under Investigation': 'bg-warning/10 text-warning border-warning/20',
  'Pending Trial': 'bg-info/10 text-info border-info/20',
  'Closed': 'bg-muted text-muted-foreground border-muted',
  'Convicted': 'bg-success/10 text-success border-success/20',
  'Charge Sheet Filed': 'bg-info/10 text-info border-info/20',
  'Arrested': 'bg-destructive/10 text-destructive border-destructive/20',
  'Bail Granted': 'bg-success/10 text-success border-success/20',
  'Acquitted': 'bg-success/10 text-success border-success/20',
  'Archived': 'bg-muted text-muted-foreground border-muted',
};

const accusedStatusColors: Record<string, string> = {
  'Arrested': 'bg-destructive/10 text-destructive border-destructive/20',
  'Absconding': 'bg-warning/10 text-warning border-warning/20',
  'Released on Bail': 'bg-info/10 text-info border-info/20',
  'Under Investigation': 'bg-muted text-muted-foreground border-muted',
};

const evidenceIcons: Record<string, React.ElementType> = {
  image: Image,
  document: FileText,
  video: Video,
  audio: Music,
  'application/pdf': FileText,
};

import { cases } from '@/services/api';

const CaseDetail: React.FC = () => {

  const { id } = useParams<{ id: string }>();
  const { canViewMetadata } = useRole();
  const { toast } = useToast();
  const [verifyingId, setVerifyingId] = React.useState<string | null>(null);
  const [caseData, setCaseData] = React.useState<any | null>(null);
  const [loading, setLoading] = React.useState(true);

  // Verification Dialog State
  const [verificationResult, setVerificationResult] = React.useState<any | null>(null);
  const [isVerificationOpen, setIsVerificationOpen] = React.useState(false);
  const [isVerifying, setIsVerifying] = React.useState(false);

  React.useEffect(() => {
    if (!id) return;
    const fetchCase = async () => {
      try {
        const data = await cases.get(id);
        // Extract case object from CaseDetailResponse if wrapped
        const caseObj = data && 'case' in data ? (data as any).case : data;
        setCaseData(caseObj);
      } catch (error) {
        console.error("Failed to fetch case", error);
        toast({
          title: "Error",
          description: "Failed to load case details",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };
    fetchCase();
  }, [id]);

  const handleVerify = async (evidenceId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent card click
    setVerifyingId(evidenceId);
    setIsVerificationOpen(true); // Open Modal immediately
    setIsVerifying(true); // Show spinner in modal
    setVerificationResult(null); // Reset previous result

    try {
      const result = await evidenceApi.verify(evidenceId);
      setVerificationResult(result);

      // Optional: keep using toast for quick feedback as well? 
      // Maybe not if the modal is opening.
    } catch (error) {
      console.error("Verification failed", error);
      toast({
        title: "Verification Failed",
        description: "Could not complete blockchain verification.",
        variant: "destructive",
      });
      setIsVerificationOpen(false); // Close if it failed fast
    } finally {
      setVerifyingId(null);
      setIsVerifying(false);
    }
  };

  // Derive Graph Data from all evidence
  const graphData = useMemo(() => {
    if (!caseData || !caseData.evidence) return { nodes: [], links: [] };

    const nodesMap = new Map();
    const links: any[] = [];

    caseData.evidence.forEach((ev: any) => {
      if (ev.metadata?.knowledge_graph) {
        const kg = ev.metadata.knowledge_graph;

        // Merge Nodes
        kg.nodes?.forEach((node: any) => {
          if (!nodesMap.has(node.id)) {
            nodesMap.set(node.id, { ...node });
          }
        });

        // Merge Links
        kg.links?.forEach((link: any) => {
          links.push({ ...link });
        });
      }
    });

    // Add Central Case Node
    const caseNodeId = `Case ${caseData.caseNumber}`;
    if (!nodesMap.has(caseNodeId)) {
      nodesMap.set(caseNodeId, { id: caseNodeId, group: "Case", val: 20 });
    }

    // Link Evidence to Case
    // caseData.evidence.forEach((ev: any) => {
    //    // Optional: add evidence files as nodes
    // });

    return {
      nodes: Array.from(nodesMap.values()),
      links: links
    };
  }, [caseData]);

  // Derive Aggregate Summary
  const displaySummary = useMemo(() => {
    if (!caseData) return "";
    if (caseData.aiSummary) return caseData.aiSummary;

    // Fallback: Aggregate summaries from recent evidence
    const summaries = caseData.evidence
      .filter((ev: any) => ev.metadata?.ai_summary)
      .map((ev: any) => `[Evidence: ${ev.name}]: ${ev.metadata.ai_summary}`)
      .join("\n\n");

    return summaries || "";
  }, [caseData]);

  if (loading) {
    return <Layout><div className="container py-8 text-center">Loading case details...</div></Layout>;
  }

  if (!caseData) {
    return (
      <Layout>
        <div className="container py-8 text-center">
          <h1 className="text-2xl font-bold mb-4">Case Not Found</h1>
          <Link to="/">
            <Button>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container py-8 space-y-6">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>

        {/* Verification Dialog */}
        <BlockchainVerificationDialog
          open={isVerificationOpen}
          onOpenChange={setIsVerificationOpen}
          result={verificationResult}
          loading={isVerifying}
        />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{caseData.caseNumber}</h1>
              <Badge variant="outline" className={cn(statusColors[caseData.status] || 'bg-muted text-muted-foreground border-muted')}>
                {caseData.status}
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-muted-foreground">
              <span className="flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {caseData.district}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                {new Date(caseData.dateOfOffence).toLocaleDateString()}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {caseData.lawSections.map((section: string) => (
              <Badge key={section} variant="secondary">
                {section}
              </Badge>
            ))}
          </div>
        </div>

        {/* AI Analysis Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left: Summary */}
          <div className="lg:col-span-1">
            {displaySummary && (
              <Card className="border-primary/20 bg-primary/5 h-full">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Brain className="h-6 w-6 text-primary animate-pulse" />
                    AI Case Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[400px] overflow-y-auto pr-2 text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {displaySummary}
                  </div>
                </CardContent>
              </Card>
            )}
            {!displaySummary && (
              <Card className="border-dashed h-full flex items-center justify-center p-6 text-muted-foreground">
                No AI Analysis Available. Upload evidence to generate insights.
              </Card>
            )}
          </div>

          {/* Right: Knowledge Graph */}
          <div className="lg:col-span-2">
            <KnowledgeGraph data={graphData} />
          </div>
        </div>

        <Tabs defaultValue="details" className="space-y-4">
          <TabsList>
            <TabsTrigger value="details">Case Details</TabsTrigger>
            <TabsTrigger value="accused">Accused ({caseData.accused.length})</TabsTrigger>
            <TabsTrigger value="evidence">Evidence ({caseData.evidence.length})</TabsTrigger>
            {canViewMetadata && <TabsTrigger value="metadata">Metadata</TabsTrigger>}
          </TabsList>

          <TabsContent value="details" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Location Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-sm text-muted-foreground">Scene of Crime</p>
                    <p className="font-medium">{caseData.sceneOfCrime}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Latitude</p>
                      <p className="font-medium">{caseData.latitude}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Longitude</p>
                      <p className="font-medium">{caseData.longitude}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">District</p>
                    <p className="font-medium">{caseData.district}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Unit</p>
                    <p className="font-medium">{caseData.unit}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Timeline</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-destructive/10 rounded-lg">
                      <Clock className="h-4 w-4 text-destructive" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Date of Offence</p>
                      <p className="font-medium">
                        {new Date(caseData.dateOfOffence).toLocaleDateString('en-IN', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-info/10 rounded-lg">
                      <FileText className="h-4 w-4 text-info" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Date of Report</p>
                      <p className="font-medium">
                        {new Date(caseData.dateOfReport).toLocaleDateString('en-IN', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-muted rounded-lg">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Last Updated</p>
                      <p className="font-medium">
                        {new Date(caseData.updatedAt).toLocaleDateString('en-IN', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {(caseData.contrabandType || caseData.vehicleDetails) && (
                <Card className="md:col-span-2">
                  <CardHeader>
                    <CardTitle className="text-base">Additional Details</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {caseData.contrabandType && (
                        <div>
                          <p className="text-sm text-muted-foreground">Contraband Type</p>
                          <p className="font-medium">{caseData.contrabandType}</p>
                        </div>
                      )}
                      {caseData.contrabandQuantity && (
                        <div>
                          <p className="text-sm text-muted-foreground">Quantity</p>
                          <p className="font-medium">{caseData.contrabandQuantity}</p>
                        </div>
                      )}
                      {caseData.vehicleDetails && (
                        <div>
                          <p className="text-sm text-muted-foreground">Vehicle Details</p>
                          <p className="font-medium">{caseData.vehicleDetails}</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          <TabsContent value="accused" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {caseData.accused.map((accused: any) => (
                <Card key={accused.id}>
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
                        <User className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center justify-between">
                          <h3 className="font-semibold text-lg">{accused.name}</h3>
                          <Badge
                            variant="outline"
                            className={cn(accusedStatusColors[accused.status])}
                          >
                            {accused.status}
                          </Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-muted-foreground">Father's Name</p>
                            <p>{accused.fatherName}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Age / Gender</p>
                            <p>{accused.age} / {accused.gender}</p>
                          </div>
                          <div className="col-span-2">
                            <p className="text-muted-foreground">Address</p>
                            <p>{accused.address}</p>
                          </div>
                          {accused.mobile && (
                            <div>
                              <p className="text-muted-foreground">Mobile</p>
                              <p>{accused.mobile}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="evidence" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {caseData.evidence.map((evidence: any) => {
                const Icon = evidenceIcons[evidence.type] || File;
                return (
                  <Card key={evidence.id} className="hover:shadow-md transition-shadow cursor-pointer">
                    <CardContent className="pt-6">
                      <div className="flex items-start gap-3">
                        <div className="p-3 bg-primary/10 rounded-lg">
                          <Icon className="h-6 w-6 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium truncate">{evidence.name}</h4>
                          <p className="text-sm text-muted-foreground capitalize">
                            {evidence.type}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Uploaded: {new Date(evidence.uploadedAt).toLocaleDateString()}
                          </p>
                          {canViewMetadata && evidence.metadata && (
                            <div className="mt-2 pt-2 border-t border-border">
                              {Object.entries(evidence.metadata).map(([key, value]) => (
                                <p key={key} className="text-xs text-muted-foreground">
                                  <span className="capitalize">{key}:</span> {String(value)}
                                </p>
                              ))}
                            </div>
                          )}
                        </div>
                        {canViewMetadata && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="ml-2 shrink-0"
                            onClick={(e) => handleVerify(evidence.id, e)}
                            disabled={verifyingId === evidence.id}
                          >
                            {verifyingId === evidence.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <ShieldCheck className="h-4 w-4 text-green-600" />
                            )}
                            <span className="sr-only">Verify</span>
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {canViewMetadata && (
            <TabsContent value="metadata" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Info className="h-5 w-5" />
                    Case Metadata
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Case ID</p>
                      <p className="font-mono text-sm">{caseData.id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Created At</p>
                      <p className="font-mono text-sm">{caseData.createdAt}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Updated At</p>
                      <p className="font-mono text-sm">{caseData.updatedAt}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">GPS Coordinates</p>
                      <p className="font-mono text-sm">
                        {caseData.latitude}, {caseData.longitude}
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-border">
                    <h4 className="font-medium mb-4">Evidence Metadata</h4>
                    <div className="space-y-3">
                      {caseData.evidence.map((ev: any) => (
                        <div key={ev.id} className="p-3 bg-muted/50 rounded-lg">
                          <p className="font-medium text-sm">{ev.name}</p>
                          {ev.metadata && (
                            <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2">
                              {Object.entries(ev.metadata).map(([key, value]) => (
                                <div key={key}>
                                  <p className="text-xs text-muted-foreground capitalize">{key}</p>
                                  <p className="text-sm font-mono">{String(value)}</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </Layout>
  );
};

export default CaseDetail;