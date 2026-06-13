/**
 * PHASE 3: Analysis Detail Page
 * Display detailed crash analysis results
 */
'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Container,
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Divider,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  ArrowBack,
  CheckCircle,
  Error,
  HourglassEmpty,
  ExpandMore,
  Download,
  Refresh,
} from '@mui/icons-material';
import { apiClient, CrashAnalysis } from '@/api/client';
import { StackTraceVisualization } from '@/visualizations/StackTraceVisualization';
import { ThreadTimeline } from '@/visualizations/ThreadTimeline';

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const getStatusConfig = () => {
    switch (status.toLowerCase()) {
      case 'completed':
        return { icon: <CheckCircle />, color: 'success' as const, label: 'Completed' };
      case 'failed':
        return { icon: <Error />, color: 'error' as const, label: 'Failed' };
      case 'parsing':
        return { icon: <HourglassEmpty />, color: 'info' as const, label: 'Parsing' };
      case 'analyzing':
        return { icon: <HourglassEmpty />, color: 'warning' as const, label: 'Analyzing' };
      default:
        return { icon: <HourglassEmpty />, color: 'default' as const, label: 'Queued' };
    }
  };

  const config = getStatusConfig();
  return (
    <Chip
      icon={config.icon}
      label={config.label}
      color={config.color}
      size="small"
    />
  );
};

export default function AnalysisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const crashId = params.id as string;

  const [analysis, setAnalysis] = useState<CrashAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const fetchAnalysis = async () => {
    try {
      const data = await apiClient.getCrashAnalysis(crashId);
      setAnalysis(data);
      setError(null);

      // Continue polling if not complete
      if (data.status !== 'completed' && data.status !== 'failed') {
        setPolling(true);
      } else {
        setPolling(false);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analysis');
      setPolling(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, [crashId]);

  // Polling effect
  useEffect(() => {
    if (!polling) return;

    const interval = setInterval(fetchAnalysis, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [polling]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <CircularProgress size={60} />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Loading analysis...
          </Typography>
        </Box>
      </Container>
    );
  }

  if (error || !analysis) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || 'Analysis not found'}
        </Alert>
        <Button startIcon={<ArrowBack />} onClick={() => router.push('/')}>
          Back to Home
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Button startIcon={<ArrowBack />} onClick={() => router.push('/')} sx={{ mb: 2 }}>
          Back to Home
        </Button>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
            Crash Analysis
          </Typography>
          <StatusBadge status={analysis.status} />
          {polling && <CircularProgress size={24} />}
        </Box>
        <Typography variant="body2" color="text.secondary">
          {analysis.filename} • {(analysis.file_size / 1024 / 1024).toFixed(2)} MB
        </Typography>
      </Box>

      {/* Error Message */}
      {analysis.status === 'failed' && analysis.error_message && (
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Analysis Failed</Typography>
          <Typography variant="body2">{analysis.error_message}</Typography>
        </Alert>
      )}

      {/* In Progress */}
      {(analysis.status === 'queued' || analysis.status === 'parsing' || analysis.status === 'analyzing') && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Analysis in Progress</Typography>
          <Typography variant="body2">
            Status: {analysis.status} • This may take a minute...
          </Typography>
        </Alert>
      )}

      {/* Basic Information */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Basic Information
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">
              Exception Code
            </Typography>
            <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
              {analysis.exception_code || 'N/A'}
            </Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">
              Platform
            </Typography>
            <Typography variant="body1">
              {analysis.platform || 'Unknown'} ({analysis.architecture || 'Unknown'})
            </Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">
              Faulting Module
            </Typography>
            <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
              {analysis.faulting_module || 'N/A'}
            </Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">
              Faulting Address
            </Typography>
            <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
              {analysis.faulting_address || 'N/A'}
            </Typography>
          </Grid>
        </Grid>
        {analysis.exception_message && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Exception Message
            </Typography>
            <Typography variant="body2" sx={{ fontFamily: 'monospace', mt: 1 }}>
              {analysis.exception_message}
            </Typography>
          </Box>
        )}
      </Paper>

      {/* AI Analysis */}
      {analysis.llm_analysis && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            🤖 AI Analysis
          </Typography>
          
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip 
                label={`Severity: ${analysis.llm_analysis.severity}`} 
                color={analysis.llm_analysis.severity === 'high' ? 'error' : 'warning'}
                size="small"
              />
              <Chip 
                label={`Confidence: ${(analysis.llm_analysis.confidence * 100).toFixed(0)}%`} 
                color="primary"
                size="small"
              />
            </Box>
            
            <Typography variant="subtitle2" gutterBottom>
              Root Cause
            </Typography>
            <Typography variant="body1" paragraph>
              {analysis.llm_analysis.root_cause}
            </Typography>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" gutterBottom>
            Recommended Solutions
          </Typography>
          <Grid container spacing={2}>
            {analysis.llm_analysis.solutions.map((solution: any, index: number) => (
              <Grid item xs={12} key={index}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {solution.title}
                      </Typography>
                      <Chip 
                        label={solution.priority} 
                        size="small"
                        color={solution.priority === 'high' ? 'error' : solution.priority === 'medium' ? 'warning' : 'default'}
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {solution.description}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {analysis.llm_analysis.references && analysis.llm_analysis.references.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                References
              </Typography>
              <List dense>
                {analysis.llm_analysis.references.map((ref: string, index: number) => (
                  <ListItem key={index}>
                    <ListItemText
                      primary={
                        <a href={ref} target="_blank" rel="noopener noreferrer" style={{ color: '#1976d2' }}>
                          {ref}
                        </a>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </Paper>
      )}

      {/* Stack Trace Visualization */}
      {analysis.stack_trace && analysis.stack_trace.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Stack Trace Visualization
          </Typography>
          <StackTraceVisualization 
            stackFrames={analysis.stack_trace}
            faultingModule={analysis.faulting_module}
          />
          
          {/* Raw Stack Trace */}
          <Accordion sx={{ mt: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography variant="subtitle2">View Raw Stack Trace</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box
                sx={{
                  bgcolor: '#1e1e1e',
                  color: '#d4d4d4',
                  p: 2,
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  overflow: 'auto',
                  maxHeight: '400px',
                }}
              >
                <pre style={{ margin: 0 }}>
                  {analysis.stack_trace.map((frame, idx) => (
                    `${frame.index.toString().padStart(2, '0')}: ${frame.module || 'unknown'}!${frame.function || frame.address || 'unknown'}\n`
                  )).join('')}
                </pre>
              </Box>
            </AccordionDetails>
          </Accordion>
        </Paper>
      )}

      {/* Similar Crashes */}
      {analysis.similar_crashes && analysis.similar_crashes.length > 0 && (
        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Similar Crashes
          </Typography>
          <List>
            {analysis.similar_crashes.map((similar: any) => (
              <ListItem
                key={similar.id}
                button
                onClick={() => router.push(`/analysis/${similar.id}`)}
              >
                <ListItemText
                  primary={similar.filename}
                  secondary={`Similarity: ${(similar.similarity * 100).toFixed(0)}%`}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Actions */}
      <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
        <Button
          startIcon={<Refresh />}
          onClick={fetchAnalysis}
          variant="outlined"
        >
          Refresh
        </Button>
        <Button
          startIcon={<Download />}
          variant="outlined"
          disabled
        >
          Download Report
        </Button>
      </Box>
    </Container>
  );
}
