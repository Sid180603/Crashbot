'use client';

import { useState } from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import { ContentCopy, Check } from '@mui/icons-material';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Props {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language = 'text' }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Box sx={{ position: 'relative', borderRadius: 1.5, overflow: 'hidden' }}>
      <Tooltip title={copied ? 'Copied!' : 'Copy'}>
        <IconButton
          onClick={handleCopy}
          size="small"
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1,
            color: '#8b949e',
            '&:hover': { color: '#e6edf3' },
          }}
        >
          {copied ? <Check fontSize="small" /> : <ContentCopy fontSize="small" />}
        </IconButton>
      </Tooltip>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 6,
          fontSize: '0.8125rem',
          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </Box>
  );
}
