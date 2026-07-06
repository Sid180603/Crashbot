'use client';

import { Box, Grid, Paper, Typography, Divider } from '@mui/material';
import { SeverityBadge } from '@/components/shared/SeverityBadge';
import { ConfidenceMeter } from '@/components/shared/ConfidenceMeter';
import type { CrashAnalysis } from '@/types';

function InfoCell({ label, value }: { label: string; value?: string | null }) {
  return (
    <Box>
      <Typography variant="caption" sx={{ color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{ fontFamily: "'JetBrains Mono', monospace", mt: 0.25, color: value ? '#e6edf3' : '#8b949e' }}
      >
        {value ?? '—'}
      </Typography>
    </Box>
  );
}

export function OverviewTab({ analysis }: { analysis: CrashAnalysis }) {
  const severity = analysis.llm_analysis?.severity ?? analysis.severity;
  const confidence = analysis.llm_analysis?.confidence ?? analysis.confidence_score;

  return (
    <Box sx={{ pt: 2 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Crash Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6} sm={3}>
                <InfoCell label="Exception Code" value={analysis.exception_code} />
              </Grid>
              <Grid item xs={6} sm={3}>
                <InfoCell label="Platform" value={analysis.platform} />
              </Grid>
              <Grid item xs={6} sm={3}>
                <InfoCell label="Architecture" value={analysis.architecture} />
              </Grid>
              <Grid item xs={6} sm={3}>
                <InfoCell label="OS Version" value={analysis.os_version} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <InfoCell label="Faulting Module" value={analysis.faulting_module} />
              </Grid>
              <Grid item xs={12} sm={6}>
                <InfoCell label="Faulting Address" value={analysis.faulting_address} />
              </Grid>
            </Grid>
            {analysis.exception_message && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="caption" sx={{ color: '#8b949e', textTransform: 'uppercase' }}>
                  Exception Message
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ fontFamily: "'JetBrains Mono', monospace", mt: 0.5, color: '#e6edf3' }}
                >
                  {analysis.exception_message}
                </Typography>
              </>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, height: '100%' }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              AI Assessment
            </Typography>
            {severity && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" sx={{ color: '#8b949e' }}>
                  Severity
                </Typography>
                <Box sx={{ mt: 0.5 }}>
                  <SeverityBadge severity={severity} />
                </Box>
              </Box>
            )}
            {confidence != null && (
              <Box>
                <Typography variant="caption" sx={{ color: '#8b949e' }}>
                  Confidence
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <ConfidenceMeter value={confidence} />
                </Box>
              </Box>
            )}
            <Divider sx={{ my: 2 }} />
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <InfoCell
                  label="Parse (s)"
                  value={analysis.parse_duration_seconds?.toFixed(1)}
                />
              </Grid>
              <Grid item xs={6}>
                <InfoCell
                  label="Analyze (s)"
                  value={analysis.analysis_duration_seconds?.toFixed(1)}
                />
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
