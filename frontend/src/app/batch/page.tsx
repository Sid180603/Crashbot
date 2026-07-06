'use client';

import { useState } from 'react';
import { Box, Button, Typography, Alert, Divider } from '@mui/material';
import { LayersOutlined } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useCrashList, useBatchAnalysis, useSeverityClassification } from '@/hooks/queries';
import { useAppStore } from '@/store';
import { CrashSelectionTable } from '@/components/batch/CrashSelectionTable';
import { BatchResults } from '@/components/batch/BatchResults';
import { DashboardSkeleton } from '@/components/feedback/SkeletonLoaders';
import { EmptyState } from '@/components/shared/EmptyState';
import type { BatchAnalysisResponse, SeverityClassificationResponse } from '@/types';

export default function BatchPage() {
  const { data: crashes = [], isLoading } = useCrashList({ limit: 200 });
  const { selectedCrashIds } = useAppStore();
  const { mutateAsync: runBatch, isPending: batchRunning } = useBatchAnalysis();
  const { mutateAsync: classifySev, isPending: classifying } = useSeverityClassification();

  const [batchResult, setBatchResult] = useState<BatchAnalysisResponse | null>(null);
  const [sevResult, setSevResult] = useState<SeverityClassificationResponse | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);

  const selectedIds = Array.from(selectedCrashIds);

  const handleBatch = async () => {
    setBatchError(null);
    try {
      const res = await runBatch({ crash_ids: selectedIds });
      setBatchResult(res);
    } catch (err: any) {
      setBatchError(err.response?.data?.detail ?? 'Batch analysis failed');
    }
  };

  const handleClassify = async () => {
    try {
      const res = await classifySev({ crash_ids: selectedIds });
      setSevResult(res);
    } catch (err: any) {
      setBatchError(err.response?.data?.detail ?? 'Classification failed');
    }
  };

  if (isLoading) return <DashboardSkeleton />;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Batch Analysis
          </Typography>
          <Typography variant="body2" sx={{ color: '#8b949e' }}>
            Select 2+ completed crashes to analyze patterns across them.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            startIcon={<LayersOutlined />}
            variant="contained"
            onClick={handleBatch}
            disabled={selectedIds.length < 2 || batchRunning}
          >
            {batchRunning ? 'Analyzing...' : `Analyze Selected (${selectedIds.length})`}
          </Button>
          <Button
            variant="outlined"
            onClick={handleClassify}
            disabled={selectedIds.length < 1 || classifying}
          >
            {classifying ? 'Classifying...' : 'Classify Severity'}
          </Button>
        </Box>
      </Box>

      {batchError && <Alert severity="error" sx={{ mb: 2 }}>{batchError}</Alert>}

      {crashes.length === 0 ? (
        <EmptyState title="No crashes yet" description="Upload crash dumps to get started." />
      ) : (
        <CrashSelectionTable crashes={crashes} />
      )}

      {batchResult && (
        <>
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
            Results
          </Typography>
          <BatchResults results={batchResult} />
        </>
      )}

      {sevResult && (
        <>
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Severity Classification
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {sevResult.results.map((r) => (
              <Box
                key={r.crash_id}
                sx={{
                  p: 2,
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 1.5,
                  display: 'flex',
                  gap: 2,
                  alignItems: 'center',
                }}
              >
                <Typography variant="body2" sx={{ fontFamily: "'JetBrains Mono', monospace", color: '#8b949e', flexShrink: 0, fontSize: '0.75rem' }}>
                  {r.crash_id.slice(0, 8)}…
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: '#e6edf3', flexShrink: 0, textTransform: 'capitalize' }}>
                  {r.severity}
                </Typography>
                <Typography variant="caption" sx={{ color: '#8b949e', flex: 1 }}>
                  {r.explanation}
                </Typography>
                <Typography variant="caption" sx={{ color: '#58a6ff', flexShrink: 0 }}>
                  {Math.round(r.confidence * 100)}%
                </Typography>
              </Box>
            ))}
          </Box>
        </>
      )}
    </motion.div>
  );
}
