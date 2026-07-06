'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  InputBase,
  IconButton,
  CircularProgress,
} from '@mui/material';
import { Send } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { useCrashChat } from '@/hooks/queries';
import { useAppStore } from '@/store';
import type { ChatMessage } from '@/types';

interface Props {
  crashId: string;
}

export function ChatPanel({ crashId }: Props) {
  const { chatHistory, addChatMessage } = useAppStore();
  const messages: ChatMessage[] = chatHistory[crashId] ?? [];
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const { mutateAsync: chat, isPending } = useCrashChat(crashId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const q = input.trim();
    if (!q || isPending) return;
    setInput('');
    addChatMessage(crashId, { role: 'user', content: q });
    try {
      const res = await chat({ question: q });
      addChatMessage(crashId, { role: 'assistant', content: res.answer });
    } catch {
      addChatMessage(crashId, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      });
    }
  };

  return (
    <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', height: 560 }}>
      {/* Message list */}
      <Paper sx={{ flex: 1, overflow: 'auto', p: 2, mb: 2 }}>
        {messages.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4, color: '#8b949e' }}>
            <Typography variant="body2">
              Ask me anything about this crash dump.
            </Typography>
          </Box>
        )}
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 1.5,
                }}
              >
                <Box
                  sx={{
                    maxWidth: '80%',
                    p: 1.5,
                    borderRadius: 2,
                    background:
                      msg.role === 'user'
                        ? 'rgba(88,166,255,0.2)'
                        : 'rgba(255,255,255,0.06)',
                    border:
                      msg.role === 'user'
                        ? '1px solid rgba(88,166,255,0.3)'
                        : '1px solid rgba(255,255,255,0.1)',
                  }}
                >
                  <Box
                    sx={{
                      '& p': { m: 0, lineHeight: 1.6, fontSize: '0.875rem' },
                      '& code': { fontFamily: "'JetBrains Mono', monospace", fontSize: '0.8rem' },
                    }}
                  >
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </Box>
                </Box>
              </Box>
            </motion.div>
          ))}
        </AnimatePresence>
        {isPending && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
            <Box sx={{ p: 1.5, borderRadius: 2, background: 'rgba(255,255,255,0.06)' }}>
              <CircularProgress size={14} />
            </Box>
          </Box>
        )}
        <div ref={bottomRef} />
      </Paper>

      {/* Input */}
      <Box
        sx={{
          display: 'flex',
          gap: 1,
          p: 1.5,
          background: '#161B22',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 1.5,
        }}
      >
        <InputBase
          fullWidth
          placeholder="Ask about this crash..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          multiline
          maxRows={4}
          sx={{ color: '#e6edf3', fontSize: '0.875rem' }}
        />
        <IconButton
          onClick={handleSend}
          disabled={!input.trim() || isPending}
          sx={{ color: '#58a6ff' }}
        >
          <Send />
        </IconButton>
      </Box>
    </Box>
  );
}
