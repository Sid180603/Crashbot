'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Button,
  Alert,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { useCrashDetail } from '@/hooks/queries';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { AnalysisDetailSkeleton } from '@/components/feedback/SkeletonLoaders';
import { OverviewTab } from '@/components/analysis/OverviewTab';
import { RootCauseTab } from '@/components/analysis/RootCauseTab';
import { StackTraceTab } from '@/components/analysis/StackTraceTab';
import { ThreadsTab } from '@/components/analysis/ThreadsTab';
import { ModulesTab } from '@/components/analysis/ModulesTab';
import { SolutionsTab } from '@/components/analysis/SolutionsTab';
import { SimilarCrashesTab } from '@/components/analysis/SimilarCrashesTab';
import { ChatPanel } from '@/components/analysis/ChatPanel';
import { ActionBar } from '@/components/analysis/ActionBar';

const TABS = [
  'Overview',
  'Root Cause',
  'Stack Trace',
  'Threads',
  'Modules',
  'Solutions',
  'Similar',
  'Chat',
];

export default function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tab, setTab] = useState(0);

  const { data: analysis, isLoading, error } = useCrashDetail(id);

  if (isLoading) return <AnalysisDetailSkeleton />;

  if (error || !analysis) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {(error as any)?.response?.data?.detail ?? 'Analysis not found'}
        </Alert>
        <Button startIcon={<ArrowBack />} onClick={() => router.push('/')}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  const inProgress = ['queued', 'parsing', 'analyzing'].includes(analysis.status);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => router.push('/')}
          sx={{ mb: 1.5, color: '#8b949e' }}
        >
          Dashboard
        </Button>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap', mb: 1 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
            {analysis.filename}
          </Typography>
          <StatusBadge status={analysis.status} />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="caption" sx={{ color: '#8b949e' }}>
            {(analysis.file_size / 1024 / 1024).toFixed(2)} MB
            {analysis.platform && ` · ${analysis.platform}`}
            {analysis.architecture && ` · ${analysis.architecture}`}
          </Typography>
          <ActionBar crashId={id} />
        </Box>
      </Box>

      {/* Status banners */}
      {analysis.status === 'failed' && analysis.error_message && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {analysis.error_message}
        </Alert>
      )}
      {inProgress && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Analysis in progress — auto-refreshing every 3s ({analysis.status})
        </Alert>
      )}

      {/* Tabs */}
      <Box sx={{ borderBottom: '1px solid rgba(255,255,255,0.1)', mb: 0 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': { color: '#8b949e', textTransform: 'none', minWidth: 'auto', px: 2 },
            '& .Mui-selected': { color: '#58a6ff' },
            '& .MuiTabs-indicator': { backgroundColor: '#58a6ff' },
          }}
        >
          {TABS.map((t) => (
            <Tab key={t} label={t} />
          ))}
        </Tabs>
      </Box>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {tab === 0 && <OverviewTab analysis={analysis} />}
          {tab === 1 && <RootCauseTab analysis={analysis} />}
          {tab === 2 && <StackTraceTab analysis={analysis} />}
          {tab === 3 && <ThreadsTab analysis={analysis} />}
          {tab === 4 && <ModulesTab analysis={analysis} />}
          {tab === 5 && <SolutionsTab analysis={analysis} />}
          {tab === 6 && <SimilarCrashesTab analysis={analysis} />}
          {tab === 7 && <ChatPanel crashId={id} />}
        </motion.div>
      </AnimatePresence>
    </motion.div>
  );
}
