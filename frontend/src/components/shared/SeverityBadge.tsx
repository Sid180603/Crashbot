'use client';

import { motion } from 'framer-motion';
import { Chip, type ChipProps } from '@mui/material';
import type { CrashSeverity } from '@/types';

const SEVERITY_CONFIG: Record<CrashSeverity, { label: string; color: string; bg: string }> = {
  critical: { label: 'Critical', color: '#f85149', bg: 'rgba(248,81,73,0.15)' },
  high: { label: 'High', color: '#d29922', bg: 'rgba(210,153,34,0.15)' },
  medium: { label: 'Medium', color: '#58a6ff', bg: 'rgba(88,166,255,0.15)' },
  low: { label: 'Low', color: '#3fb950', bg: 'rgba(63,185,80,0.15)' },
  unknown: { label: 'Unknown', color: '#8b949e', bg: 'rgba(139,148,158,0.15)' },
};

interface Props {
  severity: CrashSeverity;
  size?: ChipProps['size'];
}

export function SeverityBadge({ severity, size = 'small' }: Props) {
  const cfg = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.unknown;
  const isPulse = severity === 'critical';

  return (
    <motion.div
      animate={isPulse ? { scale: [1, 1.05, 1] } : {}}
      transition={{ duration: 2, repeat: Infinity }}
      style={{ display: 'inline-flex' }}
    >
      <Chip
        label={cfg.label}
        size={size}
        sx={{
          background: cfg.bg,
          color: cfg.color,
          border: `1px solid ${cfg.color}40`,
          fontWeight: 600,
        }}
      />
    </motion.div>
  );
}
