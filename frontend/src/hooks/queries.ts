'use client';

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';
import * as api from '@/api/crashes';
import type {
  CrashAnalysis,
  BatchAnalysisRequest,
  ChatRequest,
  SlackNotificationRequest,
  JiraIssueRequest,
  GitHubIssueRequest,
  SeverityClassificationRequest,
} from '@/types';

export const queryKeys = {
  crashes: ['crashes'] as const,
  crash: (id: string) => ['crashes', id] as const,
  similar: (id: string) => ['similar', id] as const,
};

export function useCrashList(params?: { skip?: number; limit?: number; status?: string }) {
  return useQuery({
    queryKey: [...queryKeys.crashes, params],
    queryFn: () => api.listCrashes(params),
    staleTime: 30_000,
  });
}

export function useCrashDetail(
  id: string,
  options?: Partial<UseQueryOptions<CrashAnalysis>>
) {
  return useQuery<CrashAnalysis>({
    queryKey: queryKeys.crash(id),
    queryFn: () => api.getCrash(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === 'completed' || status === 'failed') return false;
      return 3000;
    },
    ...options,
  });
}

export function useUploadCrash() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (p: number) => void;
    }) => api.uploadCrash(file, onProgress),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.crashes }),
  });
}

export function useDeleteCrash() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteCrash(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.crashes }),
  });
}

export function useBatchAnalysis() {
  return useMutation({
    mutationFn: (data: BatchAnalysisRequest) => api.batchAnalyze(data),
  });
}

export function useClusterCrashes() {
  return useMutation({
    mutationFn: (ids: string[] | undefined) => api.clusterCrashes(ids),
  });
}

export function useSimilarCrashes(
  crashId: string,
  enabled = true
) {
  return useQuery({
    queryKey: queryKeys.similar(crashId),
    queryFn: () => api.getSimilarCrashes(crashId),
    enabled,
    staleTime: 60_000,
  });
}

export function useCrashChat(crashId: string) {
  return useMutation({
    mutationFn: (data: ChatRequest) => api.chatWithCrash(crashId, data),
  });
}

export function useSlackNotification() {
  return useMutation({
    mutationFn: (data: SlackNotificationRequest) => api.sendSlackNotification(data),
  });
}

export function useJiraIssue() {
  return useMutation({
    mutationFn: (data: JiraIssueRequest) => api.createJiraIssue(data),
  });
}

export function useGitHubIssue() {
  return useMutation({
    mutationFn: (data: GitHubIssueRequest) => api.createGitHubIssue(data),
  });
}

export function useSeverityClassification() {
  return useMutation({
    mutationFn: (data: SeverityClassificationRequest) => api.classifySeverity(data),
  });
}
