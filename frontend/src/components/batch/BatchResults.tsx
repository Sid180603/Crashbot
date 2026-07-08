'use client';

import { Box, Paper, Typography, Alert, Grid } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import type { BatchAnalysisResponse } from '@/types';

interface Props {
  results: BatchAnalysisResponse;
}

export function BatchResults({ results }: Props) {
  const exceptionsData = Object.entries(results.common_exceptions)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([name, count]) => ({ name: name.length > 20 ? name.slice(0, 20) + '…' : name, count }));

  const modulesData = Object.entries(results.common_modules)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([name, count]) => ({ name: name.length > 20 ? name.slice(0, 20) + '…' : name, count }));

  const timelineData = results.timeline.map((t) => ({
    date: String(t.date ?? t.timestamp ?? ''),
    count: Number(t.count ?? t.crashes ?? 0),
  }));

  const tooltipStyle = {
    contentStyle: {
      background: '#161B22',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 6,
      color: '#e6edf3',
    },
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 3 }}>
      {results.regression_detected && (
        <Alert severity="warning" sx={{ border: '1px solid rgba(210,153,34,0.4)' }}>
          Regression detected — a recurring pattern suggests the same bug is re-appearing.
        </Alert>
      )}

      <Typography variant="body2" sx={{ color: '#8b949e' }}>
        Analyzed <strong style={{ color: '#e6edf3' }}>{results.total_crashes}</strong> crashes
        across <strong style={{ color: '#e6edf3' }}>{results.clusters.length}</strong> clusters.
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Common Exceptions
            </Typography>
            <Box sx={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={exceptionsData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis type="number" tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" width={120} tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="count" fill="#58a6ff" radius={[0, 3, 3, 0]} animationDuration={800} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Common Modules
            </Typography>
            <Box sx={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={modulesData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis type="number" tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" width={120} tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey="count" fill="#3fb950" radius={[0, 3, 3, 0]} animationDuration={800} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Clusters */}
      {results.clusters.length > 0 && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
            Crash Clusters
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {results.clusters.map((cluster) => (
              <Box
                key={cluster.cluster_id}
                sx={{
                  p: 2,
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 1.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ fontFamily: "'JetBrains Mono', monospace", color: '#58a6ff', flexShrink: 0 }}
                >
                  Cluster #{cluster.cluster_id}
                </Typography>
                <Typography variant="body2" sx={{ flex: 1, color: '#8b949e' }}>
                  {cluster.pattern}
                </Typography>
                <Typography variant="caption" sx={{ color: '#8b949e', flexShrink: 0 }}>
                  {cluster.crash_count} crashes
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>
      )}

      {/* Timeline */}
      {timelineData.length > 0 && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
            Timeline
          </Typography>
          <Box sx={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#58a6ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#58a6ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="date" tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#8b949e', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...tooltipStyle} />
                <Area type="monotone" dataKey="count" stroke="#58a6ff" fill="url(#areaGrad)" animationDuration={800} />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        </Paper>
      )}
    </Box>
  );
}
