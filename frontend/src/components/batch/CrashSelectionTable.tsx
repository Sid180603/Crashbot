'use client';

import { useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Typography,
  Chip,
} from '@mui/material';
import { formatDistanceToNow } from 'date-fns';
import { useAppStore } from '@/store';
import { SeverityBadge } from '@/components/shared/SeverityBadge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import type { CrashAnalysis } from '@/types';

interface Props {
  crashes: CrashAnalysis[];
}

export function CrashSelectionTable({ crashes }: Props) {
  const { selectedCrashIds, toggleCrashSelection, selectAll, clearSelection } = useAppStore();

  const completed = useMemo(() => crashes.filter((c) => c.status === 'completed'), [crashes]);
  const allSelected = completed.length > 0 && completed.every((c) => selectedCrashIds.has(c.id));
  const someSelected = completed.some((c) => selectedCrashIds.has(c.id));

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox">
              <Checkbox
                indeterminate={someSelected && !allSelected}
                checked={allSelected}
                onChange={() => (allSelected ? clearSelection() : selectAll(completed.map((c) => c.id)))}
                sx={{ color: '#8b949e' }}
              />
            </TableCell>
            <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Filename</TableCell>
            <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Status</TableCell>
            <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Severity</TableCell>
            <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Platform</TableCell>
            <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Created</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {completed.map((crash) => {
            const sel = selectedCrashIds.has(crash.id);
            return (
              <TableRow
                key={crash.id}
                selected={sel}
                onClick={() => toggleCrashSelection(crash.id)}
                sx={{
                  cursor: 'pointer',
                  '&.Mui-selected': { background: 'rgba(88,166,255,0.08)' },
                  '&:hover': { background: 'rgba(255,255,255,0.04)' },
                }}
              >
                <TableCell padding="checkbox">
                  <Checkbox checked={sel} sx={{ color: '#8b949e' }} />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8125rem' }}>
                    {crash.filename}
                  </Typography>
                </TableCell>
                <TableCell>
                  <StatusBadge status={crash.status} />
                </TableCell>
                <TableCell>
                  {(crash.llm_analysis?.severity ?? crash.severity) ? (
                    <SeverityBadge severity={crash.llm_analysis?.severity ?? crash.severity ?? 'unknown'} />
                  ) : (
                    <Typography variant="caption" sx={{ color: '#8b949e' }}>—</Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="caption" sx={{ color: '#8b949e' }}>
                    {crash.platform ?? '—'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="caption" sx={{ color: '#8b949e' }}>
                    {formatDistanceToNow(new Date(crash.created_at), { addSuffix: true })}
                  </Typography>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
