'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Box, Grid, Fab, Dialog, DialogTitle, DialogContent, Tooltip } from '@mui/material';
import { Add } from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useCrashList } from '@/hooks/queries';
import { StatsRow } from '@/components/dashboard/StatsRow';
import { CrashTrendChart } from '@/components/dashboard/CrashTrendChart';
import { SeverityChart } from '@/components/dashboard/SeverityChart';
import { RecentAnalysesTable } from '@/components/dashboard/RecentAnalysesTable';
import { DashboardSkeleton } from '@/components/feedback/SkeletonLoaders';
import { FileUpload } from '@/components/upload/FileUpload';

export default function DashboardPage() {
  const router = useRouter();
  const { data: crashes = [], isLoading } = useCrashList({ limit: 100 });
  const [uploadOpen, setUploadOpen] = useState(false);

  if (isLoading) return <DashboardSkeleton />;

  return (
    <Box>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <StatsRow crashes={crashes} />

        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12} md={8}>
            <CrashTrendChart crashes={crashes} />
          </Grid>
          <Grid item xs={12} md={4}>
            <SeverityChart crashes={crashes} />
          </Grid>
        </Grid>

        <RecentAnalysesTable crashes={crashes} />
      </motion.div>

      <Tooltip title="Quick Upload">
        <Fab
          color="primary"
          onClick={() => setUploadOpen(true)}
          sx={{ position: 'fixed', bottom: 32, right: 32 }}
        >
          <Add />
        </Fab>
      </Tooltip>

      <Dialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { background: '#161B22' } }}
      >
        <DialogTitle>Upload Crash Dump</DialogTitle>
        <DialogContent>
          <FileUpload
            onSuccess={(id) => {
              setUploadOpen(false);
              router.push(`/analysis/${id}`);
            }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
}
