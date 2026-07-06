'use client';

import { Grid } from '@mui/material';
import {
  BugReportOutlined,
  HourglassEmptyOutlined,
  TimerOutlined,
  WarningAmberOutlined,
} from '@mui/icons-material';
import { StatCard } from '@/components/shared/StatCard';
import type { CrashAnalysis } from '@/types';
import { useMemo } from 'react';

interface Props {
  crashes: CrashAnalysis[];
}

export function StatsRow({ crashes }: Props) {
  const stats = useMemo(() => {
    const total = crashes.length;
    const active = crashes.filter((c) =>
      ['queued', 'parsing', 'analyzing'].includes(c.status)
    ).length;
    const completed = crashes.filter((c) => c.status === 'completed');
    const critical = completed.filter(
      (c) => c.llm_analysis?.severity === 'critical' || c.severity === 'critical'
    ).length;
    const avgResolution =
      completed.length > 0
        ? completed.reduce((sum, c) => {
            const t =
              (c.analysis_duration_seconds ?? 0) +
              (c.parse_duration_seconds ?? 0);
            return sum + t;
          }, 0) / completed.length
        : 0;
    return { total, active, avgResolution: Math.round(avgResolution), critical };
  }, [crashes]);

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          label="Total Crashes"
          value={stats.total}
          icon={<BugReportOutlined sx={{ fontSize: 32 }} />}
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          label="Active Analyses"
          value={stats.active}
          icon={<HourglassEmptyOutlined sx={{ fontSize: 32 }} />}
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          label="Avg Resolution (s)"
          value={stats.avgResolution}
          icon={<TimerOutlined sx={{ fontSize: 32 }} />}
        />
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          label="Critical Crashes"
          value={stats.critical}
          icon={<WarningAmberOutlined sx={{ fontSize: 32 }} />}
        />
      </Grid>
    </Grid>
  );
}
