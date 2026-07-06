'use client';

import { Box, Breadcrumbs, Link, Typography, InputBase } from '@mui/material';
import { Search, NavigateNext } from '@mui/icons-material';
import { usePathname } from 'next/navigation';

function getBreadcrumbs(pathname: string): Array<{ label: string; href?: string }> {
  if (pathname === '/') return [{ label: 'Dashboard' }];
  if (pathname === '/upload') return [{ label: 'Dashboard', href: '/' }, { label: 'Upload' }];
  if (pathname === '/batch') return [{ label: 'Dashboard', href: '/' }, { label: 'Batch Analysis' }];
  if (pathname === '/clusters') return [{ label: 'Dashboard', href: '/' }, { label: 'Clusters' }];
  if (pathname.startsWith('/analysis/')) {
    return [
      { label: 'Dashboard', href: '/' },
      { label: 'Analysis Detail' },
    ];
  }
  return [{ label: 'Dashboard' }];
}

export function TopBar() {
  const pathname = usePathname();
  const crumbs = getBreadcrumbs(pathname);

  return (
    <Box
      sx={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3,
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        background: '#0D1117',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <Breadcrumbs separator={<NavigateNext fontSize="small" />}>
        {crumbs.map((c, i) =>
          c.href ? (
            <Link
              key={i}
              href={c.href}
              underline="hover"
              sx={{ color: '#8b949e', fontSize: '0.875rem' }}
            >
              {c.label}
            </Link>
          ) : (
            <Typography key={i} sx={{ color: '#e6edf3', fontSize: '0.875rem', fontWeight: 600 }}>
              {c.label}
            </Typography>
          )
        )}
      </Breadcrumbs>

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          background: '#161B22',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 1,
          px: 1.5,
          py: 0.5,
        }}
      >
        <Search sx={{ color: '#8b949e', fontSize: 18 }} />
        <InputBase
          placeholder="Search crashes..."
          sx={{ color: '#e6edf3', fontSize: '0.875rem', width: 200 }}
        />
      </Box>
    </Box>
  );
}
