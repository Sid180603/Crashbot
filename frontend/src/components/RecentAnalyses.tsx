/**
 * PHASE 3: Recent Analyses List
 * Shows recently analyzed crash dumps
 */
'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import { apiClient, CrashAnalysis } from '@/api/client';
import { formatDistanceToNow } from 'date-fns';

export const RecentAnalyses: React.FC = () => {
  const router = useRouter();
  const [analyses, setAnalyses] = useState<CrashAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    try {
      const data = await apiClient.listCrashAnalyses({ limit: 10 });
      setAnalyses(data);
    } catch (err: any) {
      setError('Failed to load analyses');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'analyzing':
      case 'parsing':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (analyses.length === 0) {
    return null;
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Recent Analyses
      </Typography>
      <List>
        {analyses.map((analysis) => (
          <ListItem key={analysis.id} disablePadding>
            <ListItemButton
              onClick={() => router.push(`/analysis/${analysis.id}`)}
            >
              <ListItemText
                primary={analysis.filename}
                secondary={
                  <>
                    {analysis.exception_code && `${analysis.exception_code} • `}
                    {formatDistanceToNow(new Date(analysis.created_at), {
                      addSuffix: true,
                    })}
                  </>
                }
              />
              <Chip
                label={analysis.status}
                color={getStatusColor(analysis.status) as any}
                size="small"
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};
