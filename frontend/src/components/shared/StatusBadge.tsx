'use client';

import { motion } from 'framer-motion';
import { Chip } from '@mui/material';
import { CheckCircle, Error, HourglassEmpty } from '@mui/icons-material';
import type { AnalysisStatus } from '@/types';

const STATUS_CONFIG: Record<
  AnalysisStatus,
  { label: string; color: string; bg: string; icon: React.ReactNode; pulse: boolean }
> = {
  completed: {
    label: 'Completed',
    color: '#3fb950',
    bg: 'rgba(63,185,80,0.15)',
    icon: <CheckCircle sx={{ fontSize: 14 }} />,
    pulse: false,
  },
  failed: {
    label: 'Failed',
    color: '#f85149',
    bg: 'rgba(248,81,73,0.15)',
    icon: <Error sx={{ fontSize: 14 }} />,
    pulse: false,
  },
  analyzing: {
    label: 'Analyzing',
    color: '#d29922',
    bg: 'rgba(210,153,34,0.15)',
    icon: <HourglassEmpty sx={{ fontSize: 14 }} />,
    pulse: true,
  },
  parsing: {
    label: 'Parsing',
    color: '#58a6ff',
    bg: 'rgba(88,166,255,0.15)',
    icon: <HourglassEmpty sx={{ fontSize: 14 }} />,
    pulse: true,
  },
  queued: {
    label: 'Queued',
    color: '#8b949e',
    bg: 'rgba(139,148,158,0.15)',
    icon: <HourglassEmpty sx={{ fontSize: 14 }} />,
    pulse: false,
  },
};

export function StatusBadge({ status }: { status: AnalysisStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.queued;

  return (
    <motion.div
      animate={cfg.pulse ? { opacity: [1, 0.5, 1] } : {}}
      transition={{ duration: 1.5, repeat: Infinity }}
      style={{ display: 'inline-flex' }}
    >
      <Chip
        icon={<span style={{ color: cfg.color, display: 'flex', alignItems: 'center' }}>{cfg.icon}</span>}
        label={cfg.label}
        size="small"
        sx={{
          background: cfg.bg,
          color: cfg.color,
          border: `1px solid ${cfg.color}40`,
          fontWeight: 600,
          '& .MuiChip-icon': { ml: 0.5 },
        }}
      />
    </motion.div>
  );
}
