'use client';

import { Box, Typography } from '@mui/material';
import { motion } from 'framer-motion';
import { FileUpload } from '@/components/upload/FileUpload';

export default function UploadPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Box sx={{ maxWidth: 640, mx: 'auto' }}>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
          Upload Crash Dumps
        </Typography>
        <Typography variant="body2" sx={{ color: '#8b949e', mb: 3 }}>
          Drag one or more .dmp, .dump, or .core files to analyze them with AI.
        </Typography>
        <FileUpload />
      </Box>
    </motion.div>
  );
}
