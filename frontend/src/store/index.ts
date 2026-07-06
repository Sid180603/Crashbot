import { create } from 'zustand';
import type { ChatMessage } from '@/types';

interface UISlice {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  activeFilters: {
    status: string[];
    severity: string[];
    platform: string[];
    dateFrom: string | null;
    dateTo: string | null;
  };
  setFilter: <K extends keyof UISlice['activeFilters']>(
    key: K,
    value: UISlice['activeFilters'][K]
  ) => void;
  resetFilters: () => void;
}

interface SelectionSlice {
  selectedCrashIds: Set<string>;
  toggleCrashSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
}

interface ChatSlice {
  chatHistory: Record<string, ChatMessage[]>;
  addChatMessage: (crashId: string, message: ChatMessage) => void;
  clearChatHistory: (crashId: string) => void;
}

type AppStore = UISlice & SelectionSlice & ChatSlice;

const defaultFilters: UISlice['activeFilters'] = {
  status: [],
  severity: [],
  platform: [],
  dateFrom: null,
  dateTo: null,
};

export const useAppStore = create<AppStore>((set) => ({
  // UI slice
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  activeFilters: defaultFilters,
  setFilter: (key, value) =>
    set((s) => ({ activeFilters: { ...s.activeFilters, [key]: value } })),
  resetFilters: () => set({ activeFilters: defaultFilters }),

  // Selection slice
  selectedCrashIds: new Set(),
  toggleCrashSelection: (id) =>
    set((s) => {
      const next = new Set(s.selectedCrashIds);
      next.has(id) ? next.delete(id) : next.add(id);
      return { selectedCrashIds: next };
    }),
  selectAll: (ids) => set({ selectedCrashIds: new Set(ids) }),
  clearSelection: () => set({ selectedCrashIds: new Set() }),

  // Chat slice
  chatHistory: {},
  addChatMessage: (crashId, message) =>
    set((s) => ({
      chatHistory: {
        ...s.chatHistory,
        [crashId]: [...(s.chatHistory[crashId] ?? []), message],
      },
    })),
  clearChatHistory: (crashId) =>
    set((s) => {
      const next = { ...s.chatHistory };
      delete next[crashId];
      return { chatHistory: next };
    }),
}));
