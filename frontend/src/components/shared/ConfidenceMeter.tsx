'use client';

import { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import { motion, useMotionValue, useSpring } from 'framer-motion';

interface Props {
  value: number; // 0–1
  size?: number;
}

export function ConfidenceMeter({ value, size = 80 }: Props) {
  const pct = Math.round(value * 100);
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const motionVal = useMotionValue(0);
  const spring = useSpring(motionVal, { stiffness: 80, damping: 20 });

  useEffect(() => {
    motionVal.set(value);
  }, [value, motionVal]);

  const color = value >= 0.8 ? '#3fb950' : value >= 0.5 ? '#d29922' : '#f85149';

  return (
    <Box sx={{ position: 'relative', width: size, height: size, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', position: 'absolute' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={6}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{
            strokeDashoffset: spring.get()
              ? (1 - spring.get()) * circumference
              : circumference,
          }}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: (1 - value) * circumference }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </svg>
      <Typography variant="caption" sx={{ fontWeight: 700, color, position: 'relative' }}>
        {pct}%
      </Typography>
    </Box>
  );
}
