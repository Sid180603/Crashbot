'use client';

import { useRouter } from 'next/navigation';
import { Box, Paper, Typography, Chip, Collapse, IconButton } from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useState } from 'react';
import { motion } from 'framer-motion';
import type { BatchAnalysisResponse } from '@/types';

interface Props {
  results: BatchAnalysisResponse;
}

export function ClusterView({ results }: Props) {
  const router = useRouter();
  const [expanded, setExpanded] = useState<number | null>(null);

  const scatterData = results.clusters.map((c, i) => ({
    x: (i % 4) * 10 + 5,
    y: Math.floor(i / 4) * 10 + 5,
    z: c.crash_count,
    name: `Cluster #${c.cluster_id}`,
    count: c.crash_count,
    pattern: c.pattern,
  }));

  return (
    <Box>
      {/* Bubble chart */}
      {results.clusters.length > 0 && (
        <Paper sx={{ p: 2.5, mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
            Cluster Map
          </Typography>
          <Box sx={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <XAxis dataKey="x" hide />
                <YAxis dataKey="y" hide />
                <ZAxis dataKey="z" range={[60, 400]} />
                <Tooltip
                  cursor={false}
                  content={({ payload }) => {
                    if (!payload?.length) return null;
                    const d = payload[0]?.payload as typeof scatterData[0];
                    return (
                      <Box sx={{ background: '#161B22', border: '1px solid rgba(255,255,255,0.1)', p: 1.5, borderRadius: 1 }}>
                        <Typography variant="caption" sx={{ display: 'block', fontWeight: 600 }}>
                          {d.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>
                          {d.count} crashes
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block', maxWidth: 200 }}>
                          {d.pattern}
                        </Typography>
                      </Box>
                    );
                  }}
                />
                <Scatter data={scatterData} fill="#58a6ff" opacity={0.7} />
              </ScatterChart>
            </ResponsiveContainer>
          </Box>
        </Paper>
      )}

      {/* Cluster cards */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {results.clusters.map((cluster, i) => (
          <motion.div
            key={cluster.cluster_id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <Paper>
              <Box
                sx={{
                  p: 2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                  cursor: 'pointer',
                  '&:hover': { background: 'rgba(255,255,255,0.03)' },
                }}
                onClick={() => setExpanded(expanded === cluster.cluster_id ? null : cluster.cluster_id)}
              >
                <Chip
                  label={`#${cluster.cluster_id}`}
                  size="small"
                  sx={{ background: 'rgba(88,166,255,0.15)', color: '#58a6ff', fontFamily: "'JetBrains Mono', monospace" }}
                />
                <Typography variant="body2" sx={{ flex: 1, color: '#e6edf3' }}>
                  {cluster.pattern}
                </Typography>
                <Typography variant="caption" sx={{ color: '#8b949e', flexShrink: 0 }}>
                  {cluster.crash_count} crashes
                </Typography>
                <IconButton size="small" sx={{ color: '#8b949e' }}>
                  {expanded === cluster.cluster_id ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>
              <Collapse in={expanded === cluster.cluster_id}>
                <Box sx={{ px: 2, pb: 2 }}>
                  <Typography variant="caption" sx={{ color: '#8b949e', mb: 1, display: 'block' }}>
                    Member crashes:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                    {cluster.crash_ids.map((cid) => (
                      <Chip
                        key={cid}
                        label={cid.slice(0, 8) + '…'}
                        size="small"
                        onClick={() => router.push(`/analysis/${cid}`)}
                        sx={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: '0.7rem',
                          cursor: 'pointer',
                          '&:hover': { background: 'rgba(88,166,255,0.15)' },
                        }}
                      />
                    ))}
                  </Box>
                </Box>
              </Collapse>
            </Paper>
          </motion.div>
        ))}
      </Box>
    </Box>
  );
}
