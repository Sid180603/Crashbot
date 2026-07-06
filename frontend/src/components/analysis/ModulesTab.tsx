'use client';

import { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
} from '@mui/material';
import { EmptyState } from '@/components/shared/EmptyState';
import type { CrashAnalysis, ModuleInfo } from '@/types';

function humanSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

type SortKey = keyof Pick<ModuleInfo, 'name' | 'version' | 'size'>;

export function ModulesTab({ analysis }: { analysis: CrashAnalysis }) {
  const modules = (analysis.loaded_modules ?? []) as ModuleInfo[];
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const sorted = useMemo(() => {
    return [...modules].sort((a, b) => {
      const aVal = a[sortKey] ?? '';
      const bVal = b[sortKey] ?? '';
      const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [modules, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (modules.length === 0) {
    return <EmptyState title="No module data" description="No loaded modules were captured." />;
  }

  return (
    <Box sx={{ pt: 2 }}>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: '#8b949e' }}>
                <TableSortLabel
                  active={sortKey === 'name'}
                  direction={sortKey === 'name' ? sortDir : 'asc'}
                  onClick={() => handleSort('name')}
                  sx={{ color: '#8b949e', '&.Mui-active': { color: '#58a6ff' } }}
                >
                  Name
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ color: '#8b949e' }}>
                <TableSortLabel
                  active={sortKey === 'version'}
                  direction={sortKey === 'version' ? sortDir : 'asc'}
                  onClick={() => handleSort('version')}
                  sx={{ color: '#8b949e', '&.Mui-active': { color: '#58a6ff' } }}
                >
                  Version
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ color: '#8b949e' }}>Base Address</TableCell>
              <TableCell sx={{ color: '#8b949e' }}>
                <TableSortLabel
                  active={sortKey === 'size'}
                  direction={sortKey === 'size' ? sortDir : 'asc'}
                  onClick={() => handleSort('size')}
                  sx={{ color: '#8b949e', '&.Mui-active': { color: '#58a6ff' } }}
                >
                  Size
                </TableSortLabel>
              </TableCell>
              <TableCell sx={{ color: '#8b949e' }}>Path</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sorted.map((mod, i) => {
              const isFaulting =
                mod.name?.toLowerCase() === analysis.faulting_module?.toLowerCase();
              return (
                <TableRow
                  key={i}
                  sx={{
                    background: isFaulting ? 'rgba(248,81,73,0.08)' : 'transparent',
                    '&:hover': { background: 'rgba(255,255,255,0.04)' },
                  }}
                >
                  <TableCell
                    sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8125rem', color: isFaulting ? '#f85149' : undefined }}
                  >
                    {mod.name}
                  </TableCell>
                  <TableCell sx={{ color: '#8b949e', fontSize: '0.8125rem' }}>
                    {mod.version ?? '—'}
                  </TableCell>
                  <TableCell sx={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8125rem', color: '#8b949e' }}>
                    {mod.base_address ?? '—'}
                  </TableCell>
                  <TableCell sx={{ color: '#8b949e', fontSize: '0.8125rem' }}>
                    {humanSize(mod.size)}
                  </TableCell>
                  <TableCell
                    sx={{
                      fontSize: '0.75rem',
                      color: '#8b949e',
                      maxWidth: 200,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {mod.path ?? '—'}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
