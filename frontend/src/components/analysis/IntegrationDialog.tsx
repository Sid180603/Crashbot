'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
} from '@mui/material';

type IntegrationType = 'slack' | 'jira' | 'github';

interface Props {
  open: boolean;
  type: IntegrationType;
  onClose: () => void;
  onSubmit: (data: Record<string, string>) => void;
  loading?: boolean;
}

const DIALOG_CONFIG: Record<
  IntegrationType,
  { title: string; fields: Array<{ key: string; label: string; required?: boolean; placeholder?: string }> }
> = {
  slack: {
    title: 'Send to Slack',
    fields: [
      { key: 'channel', label: 'Channel', placeholder: '#crashes (optional)' },
    ],
  },
  jira: {
    title: 'Create JIRA Issue',
    fields: [
      { key: 'project_key', label: 'Project Key', required: true, placeholder: 'CRASH' },
      { key: 'issue_type', label: 'Issue Type', placeholder: 'Bug' },
      { key: 'priority', label: 'Priority Override', placeholder: 'auto-detected' },
    ],
  },
  github: {
    title: 'Create GitHub Issue',
    fields: [
      { key: 'repository', label: 'Repository', required: true, placeholder: 'owner/repo' },
      { key: 'labels', label: 'Labels (comma-separated)', placeholder: 'bug, crash' },
    ],
  },
};

export function IntegrationDialog({ open, type, onClose, onSubmit, loading }: Props) {
  const cfg = DIALOG_CONFIG[type];
  const [values, setValues] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    onSubmit(values);
    setValues({});
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { background: '#161B22' } }}
    >
      <DialogTitle>{cfg.title}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {cfg.fields.map((f) => (
            <TextField
              key={f.key}
              label={f.label}
              placeholder={f.placeholder}
              required={f.required}
              value={values[f.key] ?? ''}
              onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              fullWidth
              size="small"
              sx={{
                '& .MuiOutlinedInput-root': {
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.2)' },
                },
              }}
            />
          ))}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="outlined">
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
