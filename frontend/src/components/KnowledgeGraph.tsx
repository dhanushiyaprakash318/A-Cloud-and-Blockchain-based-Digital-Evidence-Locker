import React, { useRef, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useTheme } from 'next-themes';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Network } from 'lucide-react';

interface ComponentProps {
    data: {
        nodes: any[];
        links: any[];
    };
}

const KnowledgeGraph: React.FC<ComponentProps> = ({ data }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
    const { theme } = useTheme();

    // Resize handler
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.offsetWidth,
                    height: 600, // Fixed height or dynamic
                });
            }
        };

        window.addEventListener('resize', updateDimensions);
        updateDimensions();

        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    // Cyber/Hacker Theme Configuration
    const nodeColors: Record<string, string> = {
        Person: '#00f2ff',   // Cyan
        Location: '#ff00ff', // Magenta
        Incident: '#ff3333', // Red
        Evidence: '#ffff00', // Yellow
        DEFAULT: '#888888'
    };

    return (
        <Card className="border-primary/20 bg-black/40 backdrop-blur-sm overflow-hidden">
            <CardHeader className="border-b border-primary/10 pb-3">
                <CardTitle className="flex items-center gap-2 text-primary font-mono tracking-wider text-xl uppercase">
                    <Network className="h-5 w-5" />
                    Case_Network_Graph // v.2.0
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0 relative" ref={containerRef}>
                {data.nodes.length === 0 ? (
                    <div className="flex items-center justify-center h-[400px] text-muted-foreground font-mono">
                        [NO_DATA_DETECTED]
                    </div>
                ) : (
                    <ForceGraph2D
                        width={dimensions.width}
                        height={dimensions.height}
                        graphData={data}

                        // Visuals
                        backgroundColor="#050505" // Very dark bg
                        nodeLabel="id"
                        nodeColor={(node: any) => nodeColors[node.group] || nodeColors['DEFAULT']}
                        nodeRelSize={6}

                        // Links
                        linkColor={() => "#444444"}
                        linkWidth={1}
                        linkDirectionalParticles={2}
                        linkDirectionalParticleSpeed={0.005}
                        linkDirectionalParticleWidth={2}
                        linkDirectionalParticleColor={() => "#00f2ff"}

                        // Text Labels on Nodes
                        nodeCanvasObject={(node: any, ctx, globalScale) => {
                            const label = node.id;
                            const fontSize = 12 / globalScale;
                            ctx.font = `${fontSize}px monospace`;

                            // Draw Node Circle
                            const color = nodeColors[node.group] || nodeColors['DEFAULT'];
                            ctx.beginPath();
                            ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                            ctx.fillStyle = color;
                            ctx.fill();

                            // Glow affect
                            ctx.shadowBlur = 10;
                            ctx.shadowColor = color;

                            // Text Label
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillStyle = '#ffffff';
                            ctx.fillText(label, node.x, node.y + 8);

                            // Reset shadow
                            ctx.shadowBlur = 0;
                        }}

                        // Interaction
                        cooldownTicks={100}
                        onNodeClick={(node) => {
                            // Focus visualizer or show tooltip details
                            // For now, center graph?
                        }}
                    />
                )}

                {/* Overlay UI Stats */}
                <div className="absolute top-4 right-4 flex flex-col gap-2 font-mono text-xs text-primary/70">
                    <div className="bg-black/80 p-2 border border-primary/20 rounded">
                        NODES: {data.nodes.length}
                    </div>
                    <div className="bg-black/80 p-2 border border-primary/20 rounded">
                        LINKS: {data.links.length}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default KnowledgeGraph;
