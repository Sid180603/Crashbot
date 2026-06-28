/**
 * PHASE 3.5: Thread Timeline Visualization
 * Show thread execution with Mermaid diagram
 */
'use client';

import React, { useEffect, useRef } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import mermaid from 'mermaid';

interface ThreadInfo {
  thread_id: number;
  is_current: boolean;
  stack_frames?: any[];
}

interface ThreadTimelineProps {
  threads: ThreadInfo[];
  exception?: string;
}

export const ThreadTimeline: React.FC<ThreadTimelineProps> = ({
  threads,
  exception,
}) => {
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mermaidRef.current || !threads.length) return;

    // Initialize Mermaid
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'strict',
    });

    // Generate Mermaid diagram
    const diagram = generateThreadDiagram(threads, exception);

    // Render diagram
    mermaidRef.current.innerHTML = diagram;
    mermaid.contentLoaded();
  }, [threads, exception]);

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        Thread Timeline
      </Typography>
      <Box ref={mermaidRef} className="mermaid" />
    </Paper>
  );
};

function generateThreadDiagram(threads: ThreadInfo[], exception?: string): string {
  let diagram = 'graph TD\n';

  threads.forEach((thread) => {
    const threadId = `T${thread.thread_id}`;
    const label = thread.is_current
      ? `Thread ${thread.thread_id} (CRASHED)`
      : `Thread ${thread.thread_id}`;

    const style = thread.is_current ? 'fill:#ff6b6b' : 'fill:#4dabf7';

    diagram += `  ${threadId}["${label}"]\n`;
    diagram += `  style ${threadId} ${style}\n`;
  });

  if (exception) {
    diagram += `  EX["Exception: ${exception}"]\n`;
    diagram += `  style EX fill:#ffcc00\n`;

    const currentThread = threads.find((t) => t.is_current);
    if (currentThread) {
      diagram += `  T${currentThread.thread_id} --> EX\n`;
    }
  }

  return diagram;
}
