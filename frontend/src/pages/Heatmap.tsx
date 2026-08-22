import React, { useState, useEffect } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { districts } from '@/data/mockCases';
import { Map, Filter, TrendingUp, AlertTriangle, Loader, AlertCircle } from 'lucide-react';

/* ================= MAP IMPORTS ================= */
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import 'leaflet.heat';

/* ================= FIX MARKER ICON ================= */
delete (L.Icon.Default.prototype as any)._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:
    'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:
    'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

/* ================= HEAT LAYER ================= */
const HeatLayer: React.FC<{ points: [number, number, number][] }> = ({ points }) => {
  const map = useMap();

  useEffect(() => {
    if (!map) return;

    const heat = (L as any).heatLayer(points, {
      radius: 35,
      blur: 25,
      maxZoom: 12,
      gradient: {
        0.2: 'yellow',
        0.5: 'orange',
        0.8: 'red',
      },
    });

    heat.addTo(map);
    return () => {
      map.removeLayer(heat);
    };
  }, [map, points]);

  return null;
};

interface HeatmapCell {
  district: string;
  count: number;
  lat: number;
  lng: number;
}

const Heatmap: React.FC = () => {
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [timeFilter, setTimeFilter] = useState('all');
  const [casesData, setCasesData] = useState<any[]>([]); // Using any[] for now or import Case type
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Fetch real cases
  const fetchCases = React.useCallback(async (isRetry = false) => {
    if (!isRetry) {
      setLoading(true);
      setError(null);
    }
    try {
      const data = await import('@/services/api').then(m => m.cases.list());
      setCasesData(data.cases || []);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch cases';
      console.error('Failed to fetch cases:', message);
      setError(message);

      // Auto-retry once after 2 seconds, e.g. if the backend was still starting up
      if (!isRetry && retryCount < 1) {
        setTimeout(() => {
          setRetryCount((prev) => prev + 1);
          fetchCases(true);
        }, 2000);
      }
    } finally {
      setLoading(false);
    }
  }, [retryCount]);

  useEffect(() => {
    fetchCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ================= DATA LOGIC ================= */
  // Get unique districts from actual data + predefined districts to ensure we cover all
  const availableDistricts = Array.from(new Set([...districts, ...casesData.map((c: any) => c.district)]));

  const districtCounts: HeatmapCell[] = availableDistricts
    .map((district) => {
      // Filter cases for this district
      const districtCases = casesData.filter((c: any) => c.district === district);

      // Calculate avg lat/lng
      const avgLat =
        districtCases.length > 0
          ? districtCases.reduce((s: number, c: any) => s + parseFloat(c.latitude), 0) / districtCases.length
          : 28.6139; // Default to center if no cases (or maybe handle differently)

      const avgLng =
        districtCases.length > 0
          ? districtCases.reduce((s: number, c: any) => s + parseFloat(c.longitude), 0) / districtCases.length
          : 77.209;

      return {
        district,
        count: districtCases.length,
        lat: avgLat,
        lng: avgLng,
      };
    })
    .filter((d) => d.count > 0); // Only show districts with cases

  const maxCount = Math.max(...districtCounts.map((d) => d.count), 1); // Avoid div by zero
  const selectedDistrictData = districtCounts.find(
    (d) => d.district === selectedDistrict
  );




  const heatPoints: [number, number, number][] = districtCounts.map((d) => [
    d.lat,
    d.lng,
    d.count,
  ]);

  if (loading) {
    return (
      <Layout>
        <div className="container py-8 flex justify-center items-center h-[500px]">
          <div className="text-center">
            <Loader className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
            <p className="text-muted-foreground">Loading heatmap data...</p>
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="container py-8 space-y-6">
        {/* HEADER */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Crime Heatmap</h1>
            <p className="text-muted-foreground">
              Geographic visualization of case density across districts
            </p>
          </div>
          <Select value={timeFilter} onValueChange={setTimeFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Time Period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Time</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
              <SelectItem value="year">This Year</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* ERROR STATE */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 flex items-start gap-4">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-medium text-red-900">Error Loading Case Data</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setRetryCount(0);
                  fetchCases();
                }}
                className="mt-3"
              >
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* LEGEND */}
        <div className="flex gap-6">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 bg-yellow-400 rounded" /> Low
          </div>
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 bg-orange-400 rounded" /> Medium
          </div>
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 bg-red-700 rounded" /> High
          </div>
        </div>

        {/* MAIN GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* REAL MAP */}
          <Card className="lg:col-span-2">
            <CardContent className="p-0">
              <div className="h-[500px] rounded-lg overflow-hidden">
                <MapContainer
                  center={[28.6139, 77.209]}
                  zoom={10}
                  className="h-full w-full brightness-110 contrast-90"
                >
                  <TileLayer

                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  />

                  <HeatLayer points={heatPoints} />

                  {districtCounts.map((d) => (
                    <Marker
                      key={d.district}
                      position={[d.lat, d.lng]}
                      eventHandlers={{
                        click: () => setSelectedDistrict(d.district),
                      }}
                    >
                      <Popup>
                        <b>{d.district}</b>
                        <br />
                        Total Cases: {d.count}
                      </Popup>
                    </Marker>
                  ))}
                </MapContainer>
              </div>
            </CardContent>
          </Card>

          {/* RIGHT PANEL */}
          <div className="space-y-4 lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>District Details</CardTitle>
              </CardHeader>
              <CardContent>
                {selectedDistrictData ? (
                  <>
                    <p className="font-bold">{selectedDistrictData.district}</p>
                    <p className="text-3xl font-bold">
                      {selectedDistrictData.count}
                    </p>
                    <Badge>
                      {selectedDistrictData.count / maxCount > 0.7
                        ? 'High'
                        : selectedDistrictData.count / maxCount > 0.4
                          ? 'Medium'
                          : 'Low'}
                    </Badge>
                  </>
                ) : (
                  <p>Select a district</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Top Districts</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {districtCounts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No case data available yet.
                  </p>
                ) : (
                  districtCounts
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 5)
                    .map((d, i) => (
                      <div
                        key={d.district}
                        className="flex justify-between p-2 hover:bg-muted rounded cursor-pointer"
                        onClick={() => setSelectedDistrict(d.district)}
                      >
                        <span>#{i + 1} {d.district}</span>
                        <Badge variant="secondary">{d.count}</Badge>
                      </div>
                    ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Map className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{districtCounts.length}</p>
                  <p className="text-sm text-muted-foreground">Active Districts</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-destructive/10 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {districtCounts.filter((d) => d.count / maxCount > 0.7).length}
                  </p>
                  <p className="text-sm text-muted-foreground">High Intensity</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-warning/10 rounded-lg">
                  <Filter className="h-5 w-5 text-warning" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{casesData.length}</p>
                  <p className="text-sm text-muted-foreground">Total Cases</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-success/10 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-success" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {(casesData.length / Math.max(districtCounts.length, 1)).toFixed(1)}
                  </p>
                  <p className="text-sm text-muted-foreground">Avg per District</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default Heatmap;
