/**
 * PHASE 3: File Upload Component
 * Drag-and-drop file upload
 */
'use client';

import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, Typography, Paper } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/octet-stream': ['.dmp', '.dump', '.core'],
    },
    multiple: false,
    maxSize: 500 * 1024 * 1024, // 500MB
  });

  return (
    <Paper
      {...getRootProps()}
      sx={{
        border: '2px dashed',
        borderColor: isDragActive ? 'primary.main' : 'grey.400',
        backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
        p: 4,
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': {
          borderColor: 'primary.main',
          backgroundColor: 'action.hover',
        },
      }}
    >
      <input {...getInputProps()} />
      <CloudUploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
      <Typography variant="h6" gutterBottom>
        {isDragActive ? 'Drop the file here' : 'Drag & drop a crash dump'}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        or click to browse (max 500MB)
      </Typography>
      <Typography variant="caption" display="block" sx={{ mt: 1 }}>
        Supported formats: .dmp, .dump, .core
      </Typography>
    </Paper>
  );
};
