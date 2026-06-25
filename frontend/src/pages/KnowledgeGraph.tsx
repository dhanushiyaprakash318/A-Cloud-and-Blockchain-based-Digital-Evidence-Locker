import React, { useState } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { mockCases } from '@/data/mockCases';
import { GitBranch, User, MapPin, FileText, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

interface Node {
  id: string;
  type: 'case' | 'accused' | 'location' | 'evidence';
  label: string;
  x: number;
  y: number;
}

interface Edge {
  from: string;
  to: string;
  label?: string;
}

const KnowledgeGraph: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [zoom, setZoom] = useState(1);

  // Generate nodes and edges from mock data
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  mockCases.forEach((c, caseIndex) => {
    const caseNode: Node = {
      id: `case-${c.id}`,
      type: 'case',
      label: c.caseNumber,
      x: 400 + Math.cos(caseIndex * 1.2) * 200,
      y: 300 + Math.sin(caseIndex * 1.2) * 150,
    };
    nodes.push(caseNode);

    // Add accused nodes
    c.accused.forEach((acc, accIndex) => {
      const existingAccused = nodes.find(
        (n) => n.type === 'accused' && n.label === acc.name
      );
      if (!existingAccused) {
        nodes.push({
          id: `accused-${acc.id}`,
          type: 'accused',
          label: acc.name,
          x: caseNode.x + 120 + accIndex * 30,
          y: caseNode.y + 80 + accIndex * 40,
        });
      }
      edges.push({
        from: `case-${c.id}`,
        to: existingAccused?.id || `accused-${acc.id}`,
        label: 'accused',
      });
    });

    // Add location nodes
    const existingLocation = nodes.find(
      (n) => n.type === 'location' && n.label === c.district
    );
    if (!existingLocation) {
      nodes.push({
        id: `location-${c.district}`,
        type: 'location',
        label: c.district,
        x: caseNode.x - 100,
        y: caseNode.y - 80,
      });
    }
    edges.push({
      from: `case-${c.id}`,
      to: `location-${c.district}`,
      label: 'location',
    });
  });

  const nodeColors = {
    case: 'fill-primary',
    accused: 'fill-destructive',
    location: 'fill-success',
    evidence: 'fill-warning',
  };

  const nodeIcons = {
    case: FileText,
    accused: User,
    location: MapPin,
    evidence: FileText,
  };

  return (
    <Layout>
      <div className="container py-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Knowledge Graph</h1>
            <p className="text-muted-foreground mt-1">
              Interactive network visualization of case relationships
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <Button variant="outline" size="icon" onClick={() => setZoom(Math.min(2, zoom + 0.1))}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={() => setZoom(1)}>
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-full bg-primary" />
            <span className="text-sm">Cases</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-full bg-destructive" />
            <span className="text-sm">Accused</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-full bg-success" />
            <span className="text-sm">Locations</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-full bg-warning" />
            <span className="text-sm">Evidence</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Graph Visualization */}
          <Card className="lg:col-span-3 overflow-hidden">
            <CardContent className="p-0">
              <div className="relative bg-muted/30 h-[600px] overflow-hidden">
                <svg
                  width="100%"
                  height="100%"
                  viewBox="0 0 800 600"
                  style={{ transform: `scale(${zoom})`, transformOrigin: 'center' }}
                >
                  {/* Edges */}
                  {edges.map((edge, index) => {
                    const fromNode = nodes.find((n) => n.id === edge.from);
                    const toNode = nodes.find((n) => n.id === edge.to);
                    if (!fromNode || !toNode) return null;
                    return (
                      <line
                        key={index}
                        x1={fromNode.x}
                        y1={fromNode.y}
                        x2={toNode.x}
                        y2={toNode.y}
                        stroke="hsl(var(--border))"
                        strokeWidth="1"
                        strokeDasharray="4"
                      />
                    );
                  })}

                  {/* Nodes */}
                  {nodes.map((node) => {
                    const Icon = nodeIcons[node.type];
                    const isSelected = selectedNode?.id === node.id;
                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x}, ${node.y})`}
                        onClick={() => setSelectedNode(node)}
                        className="cursor-pointer"
                      >
                        <circle
                          r={isSelected ? 28 : 24}
                          className={`${nodeColors[node.type]} transition-all duration-200`}
                          opacity={isSelected ? 1 : 0.8}
                          stroke={isSelected ? 'hsl(var(--foreground))' : 'none'}
                          strokeWidth={isSelected ? 3 : 0}
                        />
                        <text
                          y={40}
                          textAnchor="middle"
                          className="fill-foreground text-xs font-medium"
                          style={{ fontSize: '10px' }}
                        >
                          {node.label.length > 15 ? node.label.substring(0, 15) + '...' : node.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                {/* Empty state overlay */}
                <div className="absolute bottom-4 left-4 text-sm text-muted-foreground">
                  Click on nodes to see details
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Node Details Panel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <GitBranch className="h-5 w-5" />
                Node Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedNode ? (
                <div className="space-y-4">
                  <div>
                    <Badge
                      variant="outline"
                      className={
                        selectedNode.type === 'case'
                          ? 'bg-primary/10 text-primary border-primary/20'
                          : selectedNode.type === 'accused'
                          ? 'bg-destructive/10 text-destructive border-destructive/20'
                          : selectedNode.type === 'location'
                          ? 'bg-success/10 text-success border-success/20'
                          : 'bg-warning/10 text-warning border-warning/20'
                      }
                    >
                      {selectedNode.type.charAt(0).toUpperCase() + selectedNode.type.slice(1)}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Label</p>
                    <p className="font-medium">{selectedNode.label}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Connections</p>
                    <p className="font-medium">
                      {edges.filter(
                        (e) => e.from === selectedNode.id || e.to === selectedNode.id
                      ).length}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Position</p>
                    <p className="font-mono text-sm">
                      x: {Math.round(selectedNode.x)}, y: {Math.round(selectedNode.y)}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Select a node from the graph to view its details
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Stats
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-primary">
                  {nodes.filter((n) => n.type === 'case').length}
                </p>
                <p className="text-sm text-muted-foreground">Cases</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-destructive">
                  {nodes.filter((n) => n.type === 'accused').length}
                </p>
                <p className="text-sm text-muted-foreground">Accused Persons</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-success">
                  {nodes.filter((n) => n.type === 'location').length}
                </p>
                <p className="text-sm text-muted-foreground">Locations</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-3xl font-bold text-warning">{edges.length}</p>
                <p className="text-sm text-muted-foreground">Connections</p>
              </div>
            </CardContent>
          </Card>
        </div> */}
      </div>
    </Layout>
  );
};

export default KnowledgeGraph;