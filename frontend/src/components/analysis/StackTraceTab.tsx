'use client';

import { useState, useMemo } from 'react';
import { Box, Paper, Typography, InputBase, Tooltip } from '@mui/material';
import { Search } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { EmptyState } from '@/components/shared/EmptyState';
import type { CrashAnalysis } from '@/types';

export function StackTraceTab({ analysis }: { analysis: CrashAnalysis }) {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<number | null>(null);

  const frames = analysis.stack_trace ?? [];

  const filtered = useMemo(() => {
    if (!search) return frames;
    const q = search.toLowerCase();
    return frames.filter(
      (f) =>
        f.module?.toLowerCase().includes(q) ||
        f.function?.toLowerCase().includes(q) ||
        f.address?.toLowerCase().includes(q)
    );
  }, [frames, search]);

  if (frames.length === 0) {
    return <EmptyState title="No stack trace" description="No stack frames were captured." />;
  }

  return (
    <Box sx={{ pt: 2 }}>
      {/* Search */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          p: 1,
          mb: 2,
          background: '#161B22',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 1,
          maxWidth: 400,
        }}
      >
        <Search sx={{ color: '#8b949e', fontSize: 18 }} />
        <InputBase
          placeholder="Filter frames..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ color: '#e6edf3', fontSize: '0.875rem', flex: 1 }}
        />
      </Box>

      <Paper sx={{ p: 0, overflow: 'hidden' }}>
        <div className="stack-trace" style={{ maxHeight: 600, overflow: 'auto' }}>
          {filtered.map((frame, i) => {
            const isFaulting =
              frame.module?.toLowerCase() === analysis.faulting_module?.toLowerCase();
            return (
              <motion.span
                key={frame.index}
                className={`frame${isFaulting ? ' faulting' : ''}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.01 }}
                onClick={() => setExpanded(expanded === frame.index ? null : frame.index)}
                style={{ cursor: 'pointer', display: 'block' }}
              >
                <span style={{ color: '#8b949e', marginRight: 8, userSelect: 'none' }}>
                  {String(frame.index).padStart(2, '0')}
                </span>
                <span style={{ color: isFaulting ? '#f85149' : '#79b8ff' }}>
                  {frame.module ?? 'unknown'}
                </span>
                <span style={{ color: '#8b949e' }}>!</span>
                <span>{frame.function ?? frame.address ?? 'unknown'}</span>
                {expanded === frame.index && (
                  <Box
                    component="span"
                    sx={{ display: 'block', pl: 3, pt: 0.5, color: '#8b949e', fontSize: '0.8rem' }}
                  >
                    {frame.address && <span>addr: {frame.address} </span>}
                    {frame.offset && <span>+{frame.offset} </span>}
                    {frame.source_file && (
                      <span>
                        {frame.source_file}
                        {frame.line_number ? `:${frame.line_number}` : ''}
                      </span>
                    )}
                  </Box>
                )}
              </motion.span>
            );
          })}
        </div>
      </Paper>
    </Box>
  );
}
