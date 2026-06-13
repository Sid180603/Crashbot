/**
 * PHASE 3: Main Upload Page
 * File upload with drag-and-drop
 */
'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Container,
  Box,
  Typography,
  Paper,
  Alert,
  CircularProgress,
} from '@mui/material';
import { FileUpload } from '@/components/FileUpload';
import { RecentAnalyses } from '@/components/RecentAnalyses';
import { apiClient } from '@/api/client';

export default function HomePage() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);

    try {
      const response = await apiClient.uploadCrashDump(file);
      
      // Redirect to analysis page
      router.push(`/analysis/${response.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 6, textAlign: 'center' }}>
        <Typography variant="h2" component="h1" gutterBottom>
          Crashbot
        </Typography>
        <Typography variant="h5" color="text.secondary">
          AI-Powered Crash Dump Analysis
        </Typography>
      </Box>

      {/* Upload Section */}
      <Paper sx={{ p: 4, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          Upload Crash Dump
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Upload a crash dump file (.dmp, .dump, .core) to analyze
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {uploading ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CircularProgress size={60} />
            <Typography variant="body1" sx={{ mt: 2 }}>
              Uploading and analyzing...
            </Typography>
          </Box>
        ) : (
          <FileUpload onFileSelect={handleFileUpload} />
        )}
      </Paper>

      {/* Recent Analyses */}
      <RecentAnalyses />
    </Container>
  );
}
