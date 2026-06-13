/**
 * PHASE 3: Root Layout
 * Next.js 14 App Router Layout
 */
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AppBar, Toolbar, Typography, Container, Box } from '@mui/material';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Crashbot - AI-Powered Crash Dump Analysis',
  description: 'Analyze crash dumps with AI-powered root cause analysis and automated solutions',
  keywords: ['crash analysis', 'debugging', 'AI', 'crash dump', 'WinDbg'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          
          {/* App Bar */}
          <AppBar position="static" elevation={1}>
            <Toolbar>
              <Typography 
                variant="h6" 
                component="a" 
                href="/"
                sx={{ 
                  flexGrow: 1, 
                  textDecoration: 'none', 
                  color: 'inherit',
                  fontWeight: 700 
                }}
              >
                🤖 Crashbot
              </Typography>
              <Typography variant="body2" sx={{ ml: 2 }}>
                AI-Powered Debugging
              </Typography>
            </Toolbar>
          </AppBar>

          {/* Main Content */}
          <Box component="main" sx={{ minHeight: 'calc(100vh - 64px)', bgcolor: 'background.default' }}>
            {children}
          </Box>

          {/* Footer */}
          <Box 
            component="footer" 
            sx={{ 
              py: 3, 
              px: 2, 
              mt: 'auto',
              backgroundColor: 'background.paper',
              borderTop: '1px solid',
              borderColor: 'divider'
            }}
          >
            <Container maxWidth="lg">
              <Typography variant="body2" color="text.secondary" align="center">
                © {new Date().getFullYear()} Crashbot. Powered by AI for faster debugging.
              </Typography>
            </Container>
          </Box>
        </Providers>
      </body>
    </html>
  );
}
