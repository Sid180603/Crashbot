'use client';

import { useRouter } from 'next/navigation';
import { Box, LinearProgress, Typography, IconButton, Tooltip } from '@mui/material';
import { CheckCircle, Error, Refresh, OpenInNew } from '@mui/icons-material';
import { motion } from 'framer-motion';

interface Props {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'done' | 'error';
  crashId?: string;
  error?: string;
  onRetry?: () => void;
}

export function UploadProgress({ file, progress, status, crashId, error, onRetry }: Props) {
  const router = useRouter();
  const sizeMB = (file.size / 1024 / 1024).toFixed(1);

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Box
        sx={{
          mt: 2,
          p: 2,
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 1.5,
          background: '#161B22',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          {status === 'done' && <CheckCircle sx={{ color: '#3fb950', fontSize: 18 }} />}
          {status === 'error' && <Error sx={{ color: '#f85149', fontSize: 18 }} />}
          <Typography
            variant="body2"
            sx={{
              flex: 1,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.8125rem',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {file.name}
          </Typography>
          <Typography variant="caption" sx={{ color: '#8b949e', flexShrink: 0 }}>
            {sizeMB} MB
          </Typography>
          {status === 'error' && onRetry && (
            <Tooltip title="Retry">
              <IconButton size="small" onClick={onRetry} sx={{ color: '#8b949e' }}>
                <Refresh fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          {status === 'done' && crashId && (
            <Tooltip title="View Analysis">
              <IconButton
                size="small"
                onClick={() => router.push(`/analysis/${crashId}`)}
                sx={{ color: '#58a6ff' }}
              >
                <OpenInNew fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>

        {status === 'uploading' && (
          <LinearProgress
            variant={progress < 100 ? 'determinate' : 'indeterminate'}
            value={progress}
            sx={{
              borderRadius: 1,
              '& .MuiLinearProgress-bar': { background: '#58a6ff' },
              background: 'rgba(255,255,255,0.1)',
            }}
          />
        )}
        {status === 'done' && (
          <LinearProgress
            variant="determinate"
            value={100}
            sx={{
              borderRadius: 1,
              '& .MuiLinearProgress-bar': { background: '#3fb950' },
              background: 'rgba(255,255,255,0.1)',
            }}
          />
        )}
        {status === 'error' && (
          <Typography variant="caption" sx={{ color: '#f85149' }}>
            {error ?? 'Upload failed'}
          </Typography>
        )}
      </Box>
    </motion.div>
  );
}
