'use client';

import { motion } from 'framer-motion';
import { usePathname, useRouter } from 'next/navigation';
import { Box, IconButton, Tooltip, Typography } from '@mui/material';
import {
  DashboardOutlined,
  UploadFileOutlined,
  LayersOutlined,
  BubbleChartOutlined,
  BugReport,
  ChevronLeft,
  ChevronRight,
} from '@mui/icons-material';
import { useAppStore } from '@/store';

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/', icon: <DashboardOutlined /> },
  { label: 'Upload', href: '/upload', icon: <UploadFileOutlined /> },
  { label: 'Batch', href: '/batch', icon: <LayersOutlined /> },
  { label: 'Clusters', href: '/clusters', icon: <BubbleChartOutlined /> },
];

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useAppStore();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <motion.div
      animate={{ width: sidebarOpen ? 240 : 64 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      style={{
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 1200,
        display: 'flex',
        flexDirection: 'column',
        background: '#161B22',
        borderRight: '1px solid rgba(255,255,255,0.1)',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 2,
          py: 2.5,
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          minHeight: 64,
          cursor: 'pointer',
        }}
        onClick={() => router.push('/')}
      >
        <BugReport sx={{ color: '#58a6ff', fontSize: 28, flexShrink: 0 }} />
        <motion.div
          animate={{ opacity: sidebarOpen ? 1 : 0, width: sidebarOpen ? 'auto' : 0 }}
          transition={{ duration: 0.15 }}
          style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
        >
          <Typography variant="h6" sx={{ fontWeight: 700, color: '#e6edf3', lineHeight: 1 }}>
            Crashbot
          </Typography>
        </motion.div>
      </Box>

      {/* Nav items */}
      <Box sx={{ flex: 1, pt: 1 }}>
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href);
          return (
            <Tooltip
              key={item.href}
              title={!sidebarOpen ? item.label : ''}
              placement="right"
            >
              <Box
                onClick={() => router.push(item.href)}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  px: 2,
                  py: 1.5,
                  mx: 1,
                  mb: 0.5,
                  borderRadius: 1.5,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                  background: active
                    ? 'rgba(88,166,255,0.15)'
                    : 'transparent',
                  color: active ? '#58a6ff' : '#8b949e',
                  '&:hover': {
                    background: active
                      ? 'rgba(88,166,255,0.2)'
                      : 'rgba(255,255,255,0.06)',
                    color: active ? '#58a6ff' : '#e6edf3',
                  },
                }}
              >
                <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
                  {item.icon}
                </Box>
                <motion.div
                  animate={{ opacity: sidebarOpen ? 1 : 0, width: sidebarOpen ? 'auto' : 0 }}
                  transition={{ duration: 0.15 }}
                  style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
                >
                  <Typography variant="body2" sx={{ fontWeight: active ? 600 : 400 }}>
                    {item.label}
                  </Typography>
                </motion.div>
              </Box>
            </Tooltip>
          );
        })}
      </Box>

      {/* Collapse toggle */}
      <Box
        sx={{
          p: 1,
          borderTop: '1px solid rgba(255,255,255,0.1)',
          display: 'flex',
          justifyContent: sidebarOpen ? 'flex-end' : 'center',
        }}
      >
        <IconButton onClick={toggleSidebar} size="small" sx={{ color: '#8b949e' }}>
          {sidebarOpen ? <ChevronLeft /> : <ChevronRight />}
        </IconButton>
      </Box>
    </motion.div>
  );
}
