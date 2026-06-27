import React, { useEffect, useMemo, useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { GitBranch, RefreshCcw, Info } from 'lucide-react';
import { cases } from '@/services/api';
import { Case, KnowledgeGraphResponse } from '@/types/case';
import KnowledgeGraph from '@/components/KnowledgeGraph';

const KnowledgeGraphPage: React.FC = () => {
  const [caseList, setCaseList] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [graphData, setGraphData] = useState<KnowledgeGraphResponse>({
    case_id: '',
    case_number: '',
    nodes: [],
    links: [],
  });
  const [selectedNodeId, setSelectedNodeId] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const loadCases = async () => {
      setLoadingCases(true);
      setError(null);

      try {
        const data = await cases.list();
        const items = Array.isArray(data.cases) ? data.cases : [];
        setCaseList(items);

        if (!selectedCaseId && items.length > 0) {
          setSelectedCaseId(items[0].id);
        }
      } catch (err) {
        console.error(err);
        setError('Unable to load cases for the knowledge graph.');
      } finally {
        setLoadingCases(false);
      }
    };

    loadCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedCaseId) return;

    const loadGraph = async () => {
      setLoadingGraph(true);
      setError(null);

      try {
        const data = await cases.graph(selectedCaseId);
        setGraphData(data);
        setSelectedNodeId('');
      } catch (err) {
        console.error(err);
        setGraphData({ case_id: '', case_number: '', nodes: [], links: [] });
        setError('Unable to load knowledge graph for the selected case.');
      } finally {
        setLoadingGraph(false);
      }
    };

    loadGraph();
  }, [selectedCaseId, refreshKey]);

  const filteredNodeIds = useMemo(() => {
    if (!searchTerm) return [];
    return graphData.nodes
      .filter((node) => node.label.toLowerCase().includes(searchTerm.toLowerCase()))
      .map((node) => node.id);
  }, [graphData.nodes, searchTerm]);

  const selectedNode = useMemo(
    () => graphData.nodes.find((node) => node.id === selectedNodeId),
    [graphData.nodes, selectedNodeId]
  );

  const connectedNodeIds = useMemo(() => {
    if (!selectedNodeId) return [];
    const neighbors = new Set<string>();

    graphData.links.forEach((link) => {
      if (link.source === selectedNodeId) neighbors.add(link.target);
      if (link.target === selectedNodeId) neighbors.add(link.source);
    });

    return Array.from(neighbors);
  }, [graphData.links, selectedNodeId]);

  const nodeSummary = selectedNode
    ? {
        label: selectedNode.label,
        type: selectedNode.group || 'Entity',
        connections:
          graphData.links.filter(
            (link) => link.source === selectedNode.id || link.target === selectedNode.id
          ).length,
        evidenceId: selectedNode.evidence_id,
      }
    : null;

  return (
    <Layout>
      <div className="container py-8 space-y-6">
        <div className="flex flex-col lg:flex-row items-start lg:items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Knowledge Graph</h1>
            <p className="text-muted-foreground mt-1 max-w-2xl">
              Visualize case entities, evidence, and investigator insights in a connected network. Select a case and explore relationships, evidence links, and entity context.
            </p>
          </div>

          <div className="grid w-full max-w-3xl grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-semibold text-slate-900 block mb-2">Choose case</label>
              <Select value={selectedCaseId} onValueChange={(value) => setSelectedCaseId(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={loadingCases ? 'Loading cases...' : 'Select a case'} />
                </SelectTrigger>
                <SelectContent>
                  {caseList.map((item) => (
                    <SelectItem key={item.id} value={item.id} className="border-b border-border/10">
                      {item.caseNumber} - {item.district}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-semibold text-slate-900 block mb-2">Search entities</label>
              <Input
                placeholder="Search node labels..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                autoComplete="off"
              />
            </div>
          </div>
        </div>

        {error ? (
          <Card className="border border-destructive/20 bg-destructive/5 p-4">
            <div className="flex items-center gap-3">
              <Info className="h-5 w-5 text-destructive" />
              <p className="text-sm text-destructive">{error}</p>
            </div>
          </Card>
        ) : null}

        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          <div className="xl:col-span-3 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-muted-foreground">Case</p>
                <h2 className="text-xl font-semibold">{graphData.case_number || 'No case selected'}</h2>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRefreshKey((prev) => prev + 1)}
                disabled={loadingGraph || !selectedCaseId}
              >
                <RefreshCcw className="h-4 w-4 mr-2" />
                Refresh graph
              </Button>
            </div>

            <Card className="min-h-[680px]">
              <CardContent className="p-4">
                {loadingGraph ? (
                  <div className="flex min-h-[520px] items-center justify-center text-muted-foreground">
                    Loading graph data...
                  </div>
                ) : (
                  <KnowledgeGraph
                    data={{ nodes: graphData.nodes, links: graphData.links }}
                    selectedNodeId={selectedNodeId}
                    highlightedNodeIds={selectedNodeId ? [selectedNodeId, ...connectedNodeIds] : filteredNodeIds}
                    searchTerm={searchTerm}
                    onNodeClick={(node) => setSelectedNodeId(String(node.id))}
                    onBackgroundClick={() => setSelectedNodeId('')}
                  />
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base font-semibold">
                  <GitBranch className="h-5 w-5" />
                  Graph summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-slate-700">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Nodes</p>
                    <p className="mt-2 text-lg font-semibold">{graphData.node_count ?? graphData.nodes.length}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Connections</p>
                    <p className="mt-2 text-lg font-semibold">{graphData.link_count ?? graphData.links.length}</p>
                  </div>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Evidence files</p>
                  <p className="mt-2 text-lg font-semibold">{graphData.evidence_count ?? 0}</p>
                </div>
              </CardContent>
            </Card>

            <Card className="sticky top-6">
              <CardHeader>
                <CardTitle className="text-base font-semibold">Node details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm text-slate-700">
                {selectedNode ? (
                  <div className="space-y-4">
                    <div>
                      <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Label</p>
                      <p className="mt-1 text-base font-medium">{nodeSummary?.label}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Type</p>
                      <p className="mt-1 text-base font-medium">{nodeSummary?.type}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Connections</p>
                      <p className="mt-1 text-base font-medium">{nodeSummary?.connections}</p>
                    </div>
                    {nodeSummary?.evidenceId ? (
                      <div>
                        <p className="text-muted-foreground text-xs uppercase tracking-[0.2em]">Evidence ID</p>
                        <p className="mt-1 break-all font-mono text-sm">{nodeSummary.evidenceId}</p>
                      </div>
                    ) : null}
                    <Button variant="secondary" size="sm" onClick={() => setSelectedNodeId('')}>
                      Clear selection
                    </Button>
                  </div>
                ) : (
                  <div className="text-sm text-slate-600">
                    Click on a node in the graph to inspect an entity or evidence connection.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default KnowledgeGraphPage;
