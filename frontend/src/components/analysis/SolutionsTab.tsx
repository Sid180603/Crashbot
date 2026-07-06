'use client';

import { Box, Paper, Typography, Chip, Divider, List, ListItem } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import { CodeBlock } from '@/components/shared/CodeBlock';
import { EmptyState } from '@/components/shared/EmptyState';
import { LightbulbOutlined } from '@mui/icons-material';
import type { CrashAnalysis, Solution } from '@/types';

function priorityColor(p: number): string {
  if (p <= 1) return '#f85149';
  if (p <= 2) return '#d29922';
  return '#3fb950';
}

function priorityLabel(p: number): string {
  if (p <= 1) return 'High Priority';
  if (p <= 2) return 'Medium Priority';
  return 'Low Priority';
}

export function SolutionsTab({ analysis }: { analysis: CrashAnalysis }) {
  const solutions: Solution[] = (analysis.llm_analysis?.solutions ?? analysis.solutions ?? [])
    .slice()
    .sort((a, b) => a.priority - b.priority);

  if (solutions.length === 0) {
    return (
      <EmptyState
        icon={<LightbulbOutlined sx={{ fontSize: 48 }} />}
        title="No solutions yet"
        description="Solutions will appear after AI analysis completes."
      />
    );
  }

  return (
    <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
      {solutions.map((sol, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          whileHover={{ scale: 1.005 }}
        >
          <Paper sx={{ p: 2.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
                {sol.title}
              </Typography>
              <Chip
                label={priorityLabel(sol.priority)}
                size="small"
                sx={{
                  background: `${priorityColor(sol.priority)}20`,
                  color: priorityColor(sol.priority),
                  border: `1px solid ${priorityColor(sol.priority)}40`,
                  fontWeight: 600,
                }}
              />
            </Box>
            <Box sx={{ '& p': { color: '#8b949e', lineHeight: 1.7, fontSize: '0.875rem' } }}>
              <ReactMarkdown>{sol.description}</ReactMarkdown>
            </Box>

            {sol.code_example && (
              <Box sx={{ mt: 2 }}>
                <CodeBlock code={sol.code_example} />
              </Box>
            )}

            {sol.references && sol.references.length > 0 && (
              <>
                <Divider sx={{ my: 1.5 }} />
                <List dense disablePadding>
                  {sol.references.map((ref, j) => (
                    <ListItem key={j} disablePadding>
                      <a
                        href={ref}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#58a6ff', fontSize: '0.8125rem' }}
                      >
                        {ref}
                      </a>
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </Paper>
        </motion.div>
      ))}
    </Box>
  );
}
