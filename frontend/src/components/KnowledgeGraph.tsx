import React, { useEffect, useRef, useState } from 'react';
import ForceGraph2D, {
  ForceGraphMethods,
  GraphData,
  LinkObject,
  NodeObject,
} from 'react-force-graph-2d';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Network } from 'lucide-react';

export type GraphNode = NodeObject<{
  label?: string;
  group?: string;
  type?: string;
  evidence_id?: string;
  [key: string]: unknown;
}>;

export type GraphLink = LinkObject<
  GraphNode,
  {
    label?: string;
    evidence_id?: string;
    [key: string]: unknown;
  }
>;

interface ComponentProps {
  data: GraphData<GraphNode, GraphLink>;
  selectedNodeId?: string;
  highlightedNodeIds?: string[];
  searchTerm?: string;
  onNodeClick?: (node: GraphNode) => void;
  onBackgroundClick?: () => void;
}

const KnowledgeGraph: React.FC<ComponentProps> = ({
    data,
    selectedNodeId,
    highlightedNodeIds = [],
    searchTerm = '',
    onNodeClick,
    onBackgroundClick,
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | null>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

    // Resize handler
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.offsetWidth,
                    height: 640,
                });
            }
        };

        window.addEventListener('resize', updateDimensions);
        updateDimensions();

        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    useEffect(() => {
        if (fgRef.current && selectedNodeId) {
            const node = data.nodes.find((n) => n.id === selectedNodeId);
            if (node && typeof node.x === 'number' && typeof node.y === 'number') {
                fgRef.current.centerAt(node.x, node.y, 200);
                const currentZoom = fgRef.current.zoom();
                fgRef.current.zoom(Math.min(2, currentZoom), 400);
            }
        }
    }, [selectedNodeId, data.nodes]);

    const nodeColors: Record<string, string> = {
        Case: '#7c3aed',
        Person: '#22c55e',
        Location: '#38bdf8',
        Evidence: '#facc15',
        Incident: '#fb7185',
        Entity: '#8b5cf6',
        DEFAULT: '#9ca3af',
    };

    const filteredNodeIds = searchTerm
        ? data.nodes
              .filter((node) => typeof node.label === 'string' && node.label.toLowerCase().includes(searchTerm.toLowerCase()))
              .map((node) => String(node.id))
        : [];

    const isHighlighted = (node: GraphNode) => {
        const nodeId = String(node.id);
        if (selectedNodeId) return nodeId === selectedNodeId || highlightedNodeIds.includes(nodeId);
        if (searchTerm) return filteredNodeIds.includes(nodeId);
        return highlightedNodeIds.includes(nodeId);
    };

    const nodeCanvasObject = (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
        if (typeof node.x !== 'number' || typeof node.y !== 'number') return;

        const label = typeof node.label === 'string' ? node.label : String(node.id);
        const radius = isHighlighted(node) ? 10 : 6;
        const color = nodeColors[node.group || 'DEFAULT'] || nodeColors.DEFAULT;

        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();

        if (isHighlighted(node)) {
            ctx.lineWidth = 2;
            ctx.strokeStyle = '#ffffff';
            ctx.stroke();
        }

        ctx.font = `${12 / globalScale}px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(label, node.x, node.y + radius + 12 / globalScale);
    };

    const resolveLinkNode = (endpoint: string | number | GraphNode | undefined): GraphNode | undefined => {
        if (!endpoint) return undefined;
        if (typeof endpoint === 'object') return endpoint;
        return data.nodes.find((node) => String(node.id) === String(endpoint));
    };

    const linkCanvasObject = (link: GraphLink, ctx: CanvasRenderingContext2D) => {
        const label = link.label ? String(link.label) : '';
        if (!label) return;

        const start = resolveLinkNode(link.source);
        const end = resolveLinkNode(link.target);
        if (!start || !end || typeof start.x !== 'number' || typeof start.y !== 'number' || typeof end.x !== 'number' || typeof end.y !== 'number') return;

        const fontSize = 9;
        const midX = (start.x + end.x) / 2;
        const midY = (start.y + end.y) / 2;

        ctx.font = `${fontSize}px monospace`;
        ctx.fillStyle = '#d1d5db';
        ctx.fillText(label, midX, midY);
    };

    return (
        <Card className="border-border/20 bg-background/90 overflow-hidden">
            <CardHeader className="border-b border-border/10 pb-3">
                <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                    <Network className="h-5 w-5 text-primary" />
                    Case Knowledge Graph
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0 relative" ref={containerRef}>
                {data.nodes.length === 0 ? (
                    <div className="flex items-center justify-center h-[520px] text-muted-foreground font-medium">
                        No graph data available yet.
                    </div>
                ) : (
                    <ForceGraph2D<GraphNode, GraphLink>
                        ref={fgRef}
                        width={dimensions.width}
                        height={dimensions.height}
                        graphData={data}
                        backgroundColor="#0f172a"
                        nodeLabel={(node) => String(node.label ?? node.id)}
                        nodeColor={(node) => nodeColors[node.group || 'DEFAULT'] || nodeColors.DEFAULT}
                        nodeRelSize={6}
                        nodeVal={(node) => (isHighlighted(node) ? 12 : 8)}
                        linkColor={(link) => {
                            const sourceId = String(
                                typeof link.source === 'object' ? link.source.id : link.source
                            );
                            const targetId = String(
                                typeof link.target === 'object' ? link.target.id : link.target
                            );
                            return highlightedNodeIds.includes(sourceId) || highlightedNodeIds.includes(targetId)
                                ? '#60a5fa'
                                : '#64748b';
                        }}
                        linkWidth={(link) => {
                            const sourceId = String(
                                typeof link.source === 'object' ? link.source.id : link.source
                            );
                            const targetId = String(
                                typeof link.target === 'object' ? link.target.id : link.target
                            );
                            return selectedNodeId && (sourceId === selectedNodeId || targetId === selectedNodeId) ? 2.5 : 1;
                        }}
                        linkDirectionalParticles={1}
                        linkDirectionalParticleWidth={1}
                        linkDirectionalParticleColor={() => '#38bdf8'}
                        nodeCanvasObject={nodeCanvasObject}
                        linkCanvasObjectMode={() => 'after'}
                        linkCanvasObject={(link, ctx) => linkCanvasObject(link, ctx)}
                        onNodeClick={(node) => {
                            if (onNodeClick) onNodeClick(node);
                        }}
                        onBackgroundClick={() => {
                            if (onBackgroundClick) onBackgroundClick();
                        }}
                        cooldownTicks={100}
                    />
                )}

            </CardContent>
        </Card>
    );
};

export default KnowledgeGraph;
