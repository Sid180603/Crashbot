'use client';

import { useEffect } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';

interface Props {
  label: string;
  value: number;
  suffix?: string;
  trend?: { value: number; positive: boolean };
  icon?: React.ReactNode;
}

function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const motionVal = useMotionValue(0);
  const spring = useSpring(motionVal, { stiffness: 80, damping: 20 });
  const display = useTransform(spring, (v) => `${Math.round(v)}${suffix}`);

  useEffect(() => {
    motionVal.set(value);
  }, [value, motionVal]);

  return <motion.span>{display}</motion.span>;
}

export function StatCard({ label, value, suffix, trend, icon }: Props) {
  return (
    <motion.div whileHover={{ scale: 1.02 }} transition={{ type: 'spring', stiffness: 300 }}>
      <Paper sx={{ p: 2.5, height: '100%' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="caption" sx={{ color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {label}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, mt: 0.5, color: '#e6edf3' }}>
              <AnimatedNumber value={value} suffix={suffix} />
            </Typography>
            {trend && (
              <Typography
                variant="caption"
                sx={{ color: trend.positive ? '#3fb950' : '#f85149', mt: 0.5, display: 'block' }}
              >
                {trend.positive ? '+' : ''}{trend.value}% vs last week
              </Typography>
            )}
          </Box>
          {icon && (
            <Box sx={{ color: '#58a6ff', opacity: 0.6, fontSize: 32, display: 'flex' }}>
              {icon}
            </Box>
          )}
        </Box>
      </Paper>
    </motion.div>
  );
}
