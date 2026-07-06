'use client';

import { useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
} from '@mui/material';
import {
  Delete,
  Refresh,
  BugReport,
  GitHub,
  Notifications,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { useDeleteCrash, useJiraIssue, useGitHubIssue, useSlackNotification } from '@/hooks/queries';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/hooks/queries';
import { IntegrationDialog } from './IntegrationDialog';

interface Props {
  crashId: string;
}

type DialogType = 'delete' | 'jira' | 'github' | 'slack' | null;

export function ActionBar({ crashId }: Props) {
  const router = useRouter();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<DialogType>(null);

  const { mutateAsync: deleteCrash, isPending: deleting } = useDeleteCrash();
  const { mutateAsync: createJira, isPending: jiraLoading } = useJiraIssue();
  const { mutateAsync: createGH, isPending: ghLoading } = useGitHubIssue();
  const { mutateAsync: sendSlack, isPending: slackLoading } = useSlackNotification();

  const handleDelete = async () => {
    await deleteCrash(crashId);
    setDialog(null);
    router.push('/');
  };

  const handleJira = async (data: Record<string, string>) => {
    await createJira({
      crash_id: crashId,
      project_key: data.project_key,
      issue_type: data.issue_type || undefined,
      priority: data.priority || undefined,
    });
    setDialog(null);
  };

  const handleGH = async (data: Record<string, string>) => {
    await createGH({
      crash_id: crashId,
      repository: data.repository,
      labels: data.labels ? data.labels.split(',').map((l) => l.trim()) : [],
    });
    setDialog(null);
  };

  const handleSlack = async (data: Record<string, string>) => {
    await sendSlack({ crash_id: crashId, channel: data.channel || undefined });
    setDialog(null);
  };

  return (
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
      <Button
        startIcon={<Refresh />}
        variant="outlined"
        size="small"
        onClick={() => qc.invalidateQueries({ queryKey: queryKeys.crash(crashId) })}
      >
        Refresh
      </Button>
      <Button
        startIcon={<BugReport />}
        variant="outlined"
        size="small"
        onClick={() => setDialog('jira')}
      >
        JIRA
      </Button>
      <Button
        startIcon={<GitHub />}
        variant="outlined"
        size="small"
        onClick={() => setDialog('github')}
      >
        GitHub
      </Button>
      <Button
        startIcon={<Notifications />}
        variant="outlined"
        size="small"
        onClick={() => setDialog('slack')}
      >
        Slack
      </Button>
      <Button
        startIcon={<Delete />}
        variant="outlined"
        color="error"
        size="small"
        onClick={() => setDialog('delete')}
      >
        Delete
      </Button>

      {/* Delete confirm */}
      <Dialog
        open={dialog === 'delete'}
        onClose={() => setDialog(null)}
        PaperProps={{ sx: { background: '#161B22' } }}
      >
        <DialogTitle>Delete Analysis?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: '#8b949e' }}>
            This will permanently delete this crash analysis and cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialog(null)} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleDelete} variant="contained" color="error" disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      <IntegrationDialog
        open={dialog === 'jira'}
        type="jira"
        onClose={() => setDialog(null)}
        onSubmit={handleJira}
        loading={jiraLoading}
      />
      <IntegrationDialog
        open={dialog === 'github'}
        type="github"
        onClose={() => setDialog(null)}
        onSubmit={handleGH}
        loading={ghLoading}
      />
      <IntegrationDialog
        open={dialog === 'slack'}
        type="slack"
        onClose={() => setDialog(null)}
        onSubmit={handleSlack}
        loading={slackLoading}
      />
    </Box>
  );
}
