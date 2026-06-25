import React, { useState, useMemo, useCallback } from 'react';
import { Layout } from '@/components/layout/Layout';
import { CaseCard } from '@/components/cases/CaseCard';
import { CaseFilters, FilterState } from '@/components/cases/CaseFilters';
import { CaseUploadModal } from '@/components/cases/CaseUploadModal';
import { useRole } from '@/contexts/RoleContext';
import { Button } from '@/components/ui/button';
import { Plus, FileText, AlertCircle, Loader } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cases } from '@/services/api';

const defaultFilters: FilterState = {
  search: '',
  district: '',
  status: '',
  dateFrom: undefined,
  dateTo: undefined,
};

interface DashboardError {
  message: string;
  timestamp: Date;
}

const Dashboard: React.FC = () => {
  const { canUpload } = useRole();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [caseList, setCaseList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<DashboardError | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const fetchCases = useCallback(async (isRetry = false) => {
    if (!isRetry) {
      setLoading(true);
      setError(null);
    }

    try {
      console.log('📡 Fetching cases from API...');
      const data = await cases.list();
      
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid API response');
      }

      const caseArray = data.cases || [];
      
      if (!Array.isArray(caseArray)) {
        throw new Error('Cases data is not an array');
      }

      // Validate and normalize case data
      const validatedCases = caseArray.map((c: any) => ({
        ...c,
        id: c.id || `case-${Math.random()}`,
        latitude: typeof c.latitude === 'string' ? parseFloat(c.latitude) : (c.latitude || 0),
        longitude: typeof c.longitude === 'string' ? parseFloat(c.longitude) : (c.longitude || 0),
        status: c.status || 'Under Investigation',
        evidence: Array.isArray(c.evidence) ? c.evidence : [],
        accused: Array.isArray(c.accused) ? c.accused : [],
      }));

      setCaseList(validatedCases);
      console.log(`✅ Successfully loaded ${validatedCases.length} cases`);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch cases';
      console.error('❌ Error fetching cases:', errorMessage);
      
      setError({
        message: errorMessage,
        timestamp: new Date(),
      });

      // Auto-retry once after 2 seconds
      if (!isRetry && retryCount < 1) {
        console.log('🔄 Retrying in 2 seconds...');
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          fetchCases(true);
        }, 2000);
      }
    } finally {
      setLoading(false);
    }
  }, [retryCount]);

  React.useEffect(() => {
    fetchCases();
  }, [uploadModalOpen]); // Refresh when upload modal closes

  const filteredCases = useMemo(() => {
    return caseList.filter((c) => {
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        const matchesCaseNumber = c.caseNumber?.toLowerCase().includes(searchLower) || false;
        const matchesDistrict = c.district?.toLowerCase().includes(searchLower) || false;
        const matchesAccused = c.accused?.some((a: any) =>
          a.name?.toLowerCase().includes(searchLower)
        ) || false;
        if (!matchesCaseNumber && !matchesDistrict && !matchesAccused) return false;
      }

      if (filters.district && filters.district !== 'all' && c.district !== filters.district) {
        return false;
      }

      if (filters.status && filters.status !== 'all' && c.status !== filters.status) {
        return false;
      }

      if (filters.dateFrom) {
        const offenceDate = new Date(c.dateOfOffence);
        if (offenceDate < filters.dateFrom) return false;
      }

      if (filters.dateTo) {
        const offenceDate = new Date(c.dateOfOffence);
        if (offenceDate > filters.dateTo) return false;
      }

      return true;
    });
  }, [filters, caseList]);

  const stats = useMemo(() => {
    return {
      total: caseList.length,
      underInvestigation: caseList.filter((c) => c.status === 'Under Investigation').length,
      pendingTrial: caseList.filter((c) => c.status === 'Pending Trial').length,
      closed: caseList.filter((c) => c.status === 'Closed' || c.status === 'Convicted').length,
    };
  }, [caseList]);

  return (
    <Layout>
      <div className="container py-8 space-y-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold mb-2">Cases Dashboard</h1>
            <p className="text-muted-foreground">
              Total: {stats.total} | Under Investigation: {stats.underInvestigation} | Pending Trial: {stats.pendingTrial} | Closed: {stats.closed}
            </p>
          </div>
          {canUpload && (
            <button
              onClick={() => setUploadModalOpen(true)}
              className="
                fixed bottom-8 right-8 z-50
                h-16 w-16 rounded-full
                bg-primary text-primary-foreground
                flex items-center justify-center
                shadow-lg hover:scale-110
                transition-transform duration-300
              "
              title="Upload new case"
            >
              <Plus className="h-8 w-8" />
            </button>
          )}
        </div>

        <CaseFilters
          filters={filters}
          onFilterChange={setFilters}
          onReset={() => setFilters(defaultFilters)}
        />

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {filteredCases.length} of {caseList.length} cases
          </p>
        </div>

        {/* Error State */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-4 flex items-start gap-4">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-medium text-red-900">Error Loading Cases</h3>
              <p className="text-sm text-red-700 mt-1">{error.message}</p>
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

        {/* Loading State */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <Loader className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Loading cases...</p>
            </div>
          </div>
        ) : filteredCases.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCases.map((c) => (
              <CaseCard key={c.id} caseData={c} />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No cases found</h3>
            <p className="text-muted-foreground">
              {caseList.length === 0
                ? 'No cases have been created yet. Click the + button to create a new case.'
                : 'Try adjusting your filters to see more results'}
            </p>
          </div>
        )}
      </div>

      <CaseUploadModal open={uploadModalOpen} onOpenChange={setUploadModalOpen} />
    </Layout>
  );
};

export default Dashboard;