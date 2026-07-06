'use client';

import { useRouter } from 'next/navigation';
import { Box, Paper, Typography, LinearProgress } from '@mui/material';
import { motion } from 'framer-motion';
import { EmptyState } from '@/components/shared/EmptyState';
import type { CrashAnalysis } from '@/types';

export function SimilarCrashesTab({ analysis }: { analysis: CrashAnalysis }) {
  const router = useRouter();
  const similar = analysis.similar_crashes ?? [];

  if (similar.length === 0) {
    return (
      <EmptyState
        title="No similar crashes"
        description="No similar crashes found in the database. Add more crash dumps to improve matching."
      />
    );
  }

  return (
    <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {similar.map((sc, i) => {
        const pct = Math.round(sc.similarity * 100);
        return (
          <motion.div
            key={sc.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            whileHover={{ scale: 1.01 }}
            onClick={() => router.push(`/analysis/${sc.id}`)}
            style={{ cursor: 'pointer' }}
          >
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.75 }}>
                <Typography
                  variant="body2"
                  sx={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}
                >
                  {sc.filename ?? sc.id}
                </Typography>
                <Typography variant="body2" sx={{ color: '#58a6ff', fontWeight: 700 }}>
                  {pct}%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={pct}
                sx={{
                  borderRadius: 1,
                  height: 4,
                  background: 'rgba(255,255,255,0.1)',
                  '& .MuiLinearProgress-bar': {
                    background: pct > 90 ? '#f85149' : pct > 70 ? '#d29922' : '#58a6ff',
                  },
                }}
              />
              {sc.exception_code && (
                <Typography variant="caption" sx={{ color: '#8b949e', mt: 0.5, display: 'block' }}>
                  {sc.exception_code} · {sc.platform ?? 'unknown platform'}
                </Typography>
              )}
            </Paper>
          </motion.div>
        );
      })}
    </Box>
  );
}
