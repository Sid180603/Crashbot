'use client';

import { Box, Skeleton, Grid } from '@mui/material';

export function CardSkeleton() {
  return (
    <Box sx={{ p: 2, border: '1px solid rgba(255,255,255,0.1)', borderRadius: 1.5 }}>
      <Skeleton variant="text" width="60%" animation="wave" />
      <Skeleton variant="text" width="40%" animation="wave" sx={{ mt: 1 }} />
      <Skeleton variant="rectangular" height={40} animation="wave" sx={{ mt: 2, borderRadius: 1 }} />
    </Box>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Box>
      <Skeleton variant="rectangular" height={48} animation="wave" sx={{ mb: 1, borderRadius: 1 }} />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={52} animation="wave" sx={{ mb: 0.5, borderRadius: 1 }} />
      ))}
    </Box>
  );
}

export function DashboardSkeleton() {
  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[1, 2, 3, 4].map((i) => (
          <Grid item xs={12} sm={6} md={3} key={i}>
            <CardSkeleton />
          </Grid>
        ))}
      </Grid>
      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Skeleton variant="rectangular" height={280} animation="wave" sx={{ borderRadius: 1.5 }} />
        </Grid>
        <Grid item xs={12} md={4}>
          <Skeleton variant="rectangular" height={280} animation="wave" sx={{ borderRadius: 1.5 }} />
        </Grid>
      </Grid>
      <Box sx={{ mt: 3 }}>
        <TableSkeleton rows={6} />
      </Box>
    </Box>
  );
}

export function AnalysisDetailSkeleton() {
  return (
    <Box>
      <Skeleton variant="text" width="40%" height={40} animation="wave" />
      <Box sx={{ display: 'flex', gap: 1, mt: 1, mb: 3 }}>
        <Skeleton variant="rounded" width={80} height={24} animation="wave" />
        <Skeleton variant="rounded" width={100} height={24} animation="wave" />
      </Box>
      <Skeleton variant="rectangular" height={48} animation="wave" sx={{ mb: 2, borderRadius: 1 }} />
      <Skeleton variant="rectangular" height={300} animation="wave" sx={{ borderRadius: 1.5 }} />
    </Box>
  );
}
