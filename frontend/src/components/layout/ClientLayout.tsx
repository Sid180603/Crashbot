'use client';

import { Box } from '@mui/material';
import { useAppStore } from '@/store';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { SnackbarProvider } from '@/components/feedback/SnackbarProvider';

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);

  return (
    <>
      <Sidebar />
      <Box
        sx={{
          marginLeft: sidebarOpen ? '240px' : '64px',
          transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          background: '#0D1117',
        }}
      >
        <TopBar />
        <Box sx={{ flex: 1, p: 3 }}>{children}</Box>
      </Box>
      <SnackbarProvider />
    </>
  );
}
