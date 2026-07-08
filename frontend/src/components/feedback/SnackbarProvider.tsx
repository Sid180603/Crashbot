'use client';

import { createContext, useContext, useCallback, useState } from 'react';
import { Snackbar, Alert, Slide, type AlertColor } from '@mui/material';

interface Toast {
  id: number;
  message: string;
  severity: AlertColor;
}

interface ToastCtx {
  showToast: (message: string, severity?: AlertColor) => void;
}

export const ToastContext = createContext<ToastCtx>({ showToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let counter = 0;

export function SnackbarProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, severity: AlertColor = 'info') => {
    const id = ++counter;
    setToasts((prev) => [...prev, { id, message, severity }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toasts.map((toast, i) => (
        <Snackbar
          key={toast.id}
          open
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          TransitionComponent={Slide}
          sx={{ bottom: `${(i + 1) * 64}px !important` }}
        >
          <Alert
            severity={toast.severity}
            variant="filled"
            onClose={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
            sx={{ minWidth: 300 }}
          >
            {toast.message}
          </Alert>
        </Snackbar>
      ))}
    </ToastContext.Provider>
  );
}
