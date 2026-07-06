'use client';

import { Box, Paper, Typography, Divider, List, ListItem } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { CodeBlock } from '@/components/shared/CodeBlock';
import { EmptyState } from '@/components/shared/EmptyState';
import { Psychology } from '@mui/icons-material';
import type { CrashAnalysis } from '@/types';

export function RootCauseTab({ analysis }: { analysis: CrashAnalysis }) {
  const llm = analysis.llm_analysis;
  const rootCause = llm?.root_cause ?? analysis.root_cause;
  const explanation = llm?.explanation ?? analysis.explanation;
  const references = llm?.references ?? analysis.references;

  if (!rootCause) {
    return (
      <EmptyState
        icon={<Psychology sx={{ fontSize: 48 }} />}
        title="No AI analysis yet"
        description="The AI analysis hasn't completed yet, or no LLM is configured."
      />
    );
  }

  return (
    <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Paper sx={{ p: 2.5 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
          Root Cause
        </Typography>
        <Box sx={{ '& p': { color: '#e6edf3', lineHeight: 1.7 }, '& code': { fontFamily: "'JetBrains Mono', monospace" } }}>
          <ReactMarkdown>{rootCause}</ReactMarkdown>
        </Box>

        {explanation && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              Detailed Explanation
            </Typography>
            <Box sx={{ '& p': { color: '#e6edf3', lineHeight: 1.7 } }}>
              <ReactMarkdown
                components={{
                  code: ({ children }) => (
                    <CodeBlock code={String(children)} />
                  ),
                }}
              >
                {explanation}
              </ReactMarkdown>
            </Box>
          </>
        )}
      </Paper>

      {references && references.length > 0 && (
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
            References
          </Typography>
          <List dense disablePadding>
            {references.map((ref, i) => (
              <ListItem key={i} disablePadding sx={{ py: 0.25 }}>
                <a
                  href={ref}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#58a6ff', fontSize: '0.875rem', wordBreak: 'break-all' }}
                >
                  {ref}
                </a>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
}
