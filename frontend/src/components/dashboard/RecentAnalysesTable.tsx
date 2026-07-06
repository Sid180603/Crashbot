'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  Box,
} from '@mui/material';
import { motion } from 'framer-motion';
import { formatDistanceToNow } from 'date-fns';

const MotionTableRow = motion(TableRow);
import { StatusBadge } from '@/components/shared/StatusBadge';
import { SeverityBadge } from '@/components/shared/SeverityBadge';
import { EmptyState } from '@/components/shared/EmptyState';
import type { CrashAnalysis, AnalysisStatus } from '@/types';

const STATUS_FILTERS: AnalysisStatus[] = ['queued', 'parsing', 'analyzing', 'completed', 'failed'];

interface Props {
  crashes: CrashAnalysis[];
}

export function RecentAnalysesTable({ crashes }: Props) {
  const router = useRouter();
  const [page, setPage] = useState(0);
  const [rowsPerPage] = useState(10);
  const [statusFilter, setStatusFilter] = useState<AnalysisStatus | null>(null);

  const filtered = useMemo(
    () => (statusFilter ? crashes.filter((c) => c.status === statusFilter) : crashes),
    [crashes, statusFilter]
  );

  const paginated = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Paper sx={{ mt: 3 }}>
      <Box sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mr: 1 }}>
          Recent Analyses
        </Typography>
        <Chip
          label="All"
          size="small"
          onClick={() => setStatusFilter(null)}
          variant={!statusFilter ? 'filled' : 'outlined'}
          sx={{ fontSize: '0.75rem' }}
        />
        {STATUS_FILTERS.map((s) => (
          <Chip
            key={s}
            label={s}
            size="small"
            onClick={() => setStatusFilter(s === statusFilter ? null : s)}
            variant={statusFilter === s ? 'filled' : 'outlined'}
            sx={{ fontSize: '0.75rem', textTransform: 'capitalize' }}
          />
        ))}
      </Box>

      {paginated.length === 0 ? (
        <EmptyState
          title="No crashes found"
          description="Upload a crash dump to get started."
          action={{ label: 'Upload Crash', onClick: () => router.push('/upload') }}
        />
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Filename</TableCell>
                <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Exception</TableCell>
                <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Severity</TableCell>
                <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Platform</TableCell>
                <TableCell sx={{ color: '#8b949e', fontWeight: 600 }}>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginated.map((crash, i) => (
                <MotionTableRow
                  key={crash.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => router.push(`/analysis/${crash.id}`)}
                  sx={{ cursor: 'pointer', '&:hover': { background: 'rgba(255,255,255,0.04)' } }}
                >
                  <TableCell>
                    <StatusBadge status={crash.status} />
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '0.8125rem',
                        maxWidth: 200,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {crash.filename}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="caption"
                      sx={{ fontFamily: "'JetBrains Mono', monospace", color: '#8b949e' }}
                    >
                      {crash.exception_code ?? '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {(crash.llm_analysis?.severity ?? crash.severity) ? (
                      <SeverityBadge
                        severity={crash.llm_analysis?.severity ?? crash.severity ?? 'unknown'}
                      />
                    ) : (
                      <Typography variant="caption" sx={{ color: '#8b949e' }}>
                        —
                      </Typography>
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
                </MotionTableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {filtered.length > rowsPerPage && (
        <TablePagination
          component="div"
          count={filtered.length}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          rowsPerPageOptions={[10]}
          sx={{ color: '#8b949e' }}
        />
      )}
    </Paper>
  );
}
