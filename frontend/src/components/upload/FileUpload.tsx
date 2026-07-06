'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, Typography, Paper } from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadProgress } from './UploadProgress';
import { useUploadCrash } from '@/hooks/queries';

interface FileEntry {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'done' | 'error';
  crashId?: string;
  error?: string;
}

interface Props {
  onSuccess?: (crashId: string) => void;
}

export function FileUpload({ onSuccess }: Props) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const { mutateAsync: upload } = useUploadCrash();

  const processFile = useCallback(
    async (file: File) => {
      const entry: FileEntry = { file, progress: 0, status: 'uploading' };
      setEntries((prev) => [...prev, entry]);

      const updateEntry = (patch: Partial<FileEntry>) =>
        setEntries((prev) =>
          prev.map((e) => (e.file === file ? { ...e, ...patch } : e))
        );

      try {
        const result = await upload({
          file,
          onProgress: (p) => updateEntry({ progress: p }),
        });
        updateEntry({ status: 'done', crashId: result.id, progress: 100 });
        onSuccess?.(result.id);
      } catch (err: any) {
        updateEntry({
          status: 'error',
          error: err.response?.data?.detail ?? 'Upload failed',
        });
      }
    },
    [upload, onSuccess]
  );

  const onDrop = useCallback(
    (accepted: File[]) => accepted.forEach(processFile),
    [processFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: {
      'application/octet-stream': ['.dmp', '.dump', '.core'],
    },
    maxSize: 500 * 1024 * 1024,
  });

  return (
    <Box>
      <Paper
        {...getRootProps()}
        sx={{
          border: `2px dashed ${isDragActive ? '#58a6ff' : 'rgba(255,255,255,0.2)'}`,
          borderRadius: 2,
          p: 5,
          textAlign: 'center',
          cursor: 'pointer',
          background: isDragActive ? 'rgba(88,166,255,0.08)' : 'transparent',
          transition: 'all 0.2s ease',
          '&:hover': {
            borderColor: '#58a6ff',
            background: 'rgba(88,166,255,0.04)',
          },
        }}
      >
        <input {...getInputProps()} />
        <motion.div
          animate={isDragActive ? { scale: 1.1 } : { scale: 1 }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          <CloudUpload
            sx={{ fontSize: 56, color: isDragActive ? '#58a6ff' : '#8b949e', mb: 2 }}
          />
        </motion.div>
        <Typography variant="h6" sx={{ color: isDragActive ? '#58a6ff' : '#e6edf3', mb: 1 }}>
          {isDragActive ? 'Drop files here' : 'Drag & drop crash dumps'}
        </Typography>
        <Typography variant="body2" sx={{ color: '#8b949e' }}>
          .dmp, .dump, .core — up to 500 MB each
        </Typography>
        <Typography variant="caption" sx={{ color: '#58a6ff', mt: 1, display: 'block' }}>
          or click to browse
        </Typography>
      </Paper>

      <AnimatePresence>
        {entries.map((entry) => (
          <UploadProgress
            key={entry.file.name + entry.file.size}
            file={entry.file}
            progress={entry.progress}
            status={entry.status}
            crashId={entry.crashId}
            error={entry.error}
            onRetry={() => processFile(entry.file)}
          />
        ))}
      </AnimatePresence>
    </Box>
  );
}
