'use client';

import { useState } from 'react';
import { Box, Button, Typography, Alert } from '@mui/material';
import { BubbleChartOutlined } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useCrashList, useClusterCrashes } from '@/hooks/queries';
import { ClusterView } from '@/components/clusters/ClusterView';
import { EmptyState } from '@/components/shared/EmptyState';
import type { BatchAnalysisResponse } from '@/types';

export default function ClustersPage() {
  const { data: crashes = [] } = useCrashList({ limit: 200 });
  const { mutateAsync: cluster, isPending } = useClusterCrashes();
  const [results, setResults] = useState<BatchAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCluster = async () => {
    setError(null);
    try {
      const res = await cluster(undefined);
      setResults(res);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Clustering failed');
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Crash Clusters
          </Typography>
          <Typography variant="body2" sx={{ color: '#8b949e' }}>
            Group similar crashes to identify patterns.
          </Typography>
        </Box>
        <Button
          startIcon={<BubbleChartOutlined />}
          variant="contained"
          onClick={handleCluster}
          disabled={isPending || crashes.length === 0}
        >
          {isPending ? 'Clustering...' : 'Cluster All Crashes'}
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!results && !isPending && (
        <EmptyState
          icon={<BubbleChartOutlined sx={{ fontSize: 48 }} />}
          title="No clusters yet"
          description="Click 'Cluster All Crashes' to group similar crashes by pattern."
          action={{ label: 'Cluster Now', onClick: () => handleCluster() }}
        />
      )}

      {results && <ClusterView results={results} />}
    </motion.div>
  );
}
