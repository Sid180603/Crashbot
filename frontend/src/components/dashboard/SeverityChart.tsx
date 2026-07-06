'use client';

import { useMemo } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { CrashAnalysis, CrashSeverity } from '@/types';

const SEVERITY_COLORS: Record<CrashSeverity, string> = {
  critical: '#f85149',
  high: '#d29922',
  medium: '#58a6ff',
  low: '#3fb950',
  unknown: '#8b949e',
};

interface Props {
  crashes: CrashAnalysis[];
}

export function SeverityChart({ crashes }: Props) {
  const data = useMemo(() => {
    const counts: Record<string, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      unknown: 0,
    };
    crashes.forEach((c) => {
      const sev = c.llm_analysis?.severity ?? c.severity ?? 'unknown';
      if (sev in counts) counts[sev]++;
      else counts.unknown++;
    });
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }));
  }, [crashes]);

  const total = crashes.length;

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Severity Distribution
      </Typography>
      <Box sx={{ height: 220, position: 'relative' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={2}
              dataKey="value"
              animationBegin={0}
              animationDuration={800}
            >
              {data.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={SEVERITY_COLORS[entry.name as CrashSeverity] ?? '#8b949e'}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: '#161B22',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 6,
                color: '#e6edf3',
              }}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              formatter={(value) => (
                <span style={{ color: '#8b949e', fontSize: 12 }}>{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -55%)',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            {total}
          </Typography>
          <Typography variant="caption" sx={{ color: '#8b949e' }}>
            total
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
