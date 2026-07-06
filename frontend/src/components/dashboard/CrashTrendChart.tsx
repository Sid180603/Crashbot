'use client';

import { useMemo } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { format, subDays, startOfDay } from 'date-fns';
import type { CrashAnalysis } from '@/types';

interface Props {
  crashes: CrashAnalysis[];
}

export function CrashTrendChart({ crashes }: Props) {
  const data = useMemo(() => {
    const days = Array.from({ length: 30 }, (_, i) => {
      const d = startOfDay(subDays(new Date(), 29 - i));
      return { date: d, label: format(d, 'MMM d'), count: 0 };
    });

    crashes.forEach((c) => {
      const day = startOfDay(new Date(c.created_at)).getTime();
      const entry = days.find((d) => d.date.getTime() === day);
      if (entry) entry.count++;
    });

    return days.map(({ label, count }) => ({ label, count }));
  }, [crashes]);

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Crash Trend (30 days)
      </Typography>
      <Box sx={{ height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="label"
              tick={{ fill: '#8b949e', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              interval={6}
            />
            <YAxis
              tick={{ fill: '#8b949e', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: '#161B22',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 6,
                color: '#e6edf3',
              }}
            />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#58a6ff"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#58a6ff' }}
              animationDuration={800}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}
