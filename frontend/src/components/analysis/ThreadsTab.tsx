'use client';

import { useState } from 'react';
import { Box, Paper, Typography, Chip, Collapse, IconButton } from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { EmptyState } from '@/components/shared/EmptyState';
import type { CrashAnalysis } from '@/types';

export function ThreadsTab({ analysis }: { analysis: CrashAnalysis }) {
  const [expandedThread, setExpandedThread] = useState<number | null>(
    analysis.threads?.find((t) => t.is_current)?.thread_id ?? null
  );

  const threads = analysis.threads ?? [];

  if (threads.length === 0) {
    return <EmptyState title="No thread data" description="No thread information was captured." />;
  }

  return (
    <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {threads.map((thread, i) => (
        <motion.div
          key={thread.thread_id}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.04 }}
        >
          <Paper
            sx={{
              border: thread.is_current
                ? '1px solid rgba(248,81,73,0.4)'
                : '1px solid rgba(255,255,255,0.1)',
            }}
          >
            <Box
              sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                cursor: 'pointer',
                '&:hover': { background: 'rgba(255,255,255,0.03)' },
              }}
              onClick={() =>
                setExpandedThread(
                  expandedThread === thread.thread_id ? null : thread.thread_id
                )
              }
            >
              <Typography
                variant="body2"
                sx={{ fontFamily: "'JetBrains Mono', monospace", flex: 1 }}
              >
                Thread #{thread.thread_id}
              </Typography>
              {thread.is_current && (
                <Chip
                  label="Crashed"
                  size="small"
                  sx={{
                    background: 'rgba(248,81,73,0.15)',
                    color: '#f85149',
                    border: '1px solid rgba(248,81,73,0.4)',
                    fontWeight: 600,
                  }}
                />
              )}
              <Typography variant="caption" sx={{ color: '#8b949e' }}>
                {thread.stack_frames.length} frames
              </Typography>
              <IconButton size="small" sx={{ color: '#8b949e' }}>
                {expandedThread === thread.thread_id ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>
            <Collapse in={expandedThread === thread.thread_id}>
              <div className="stack-trace" style={{ margin: '0 0 0 0', borderRadius: 0 }}>
                {thread.stack_frames.map((frame) => (
                  <span key={frame.index} className="frame" style={{ display: 'block' }}>
                    <span style={{ color: '#8b949e', marginRight: 8 }}>
                      {String(frame.index).padStart(2, '0')}
                    </span>
                    <span style={{ color: '#79b8ff' }}>{frame.module ?? 'unknown'}</span>
                    <span style={{ color: '#8b949e' }}>!</span>
                    <span>{frame.function ?? frame.address ?? 'unknown'}</span>
                  </span>
                ))}
              </div>
            </Collapse>
          </Paper>
        </motion.div>
      ))}
    </Box>
  );
}
