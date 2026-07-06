import { apiClient } from './client';
import type {
  CrashAnalysis,
  UploadResponse,
  BatchAnalysisRequest,
  BatchAnalysisResponse,
  SimilarCrashesResponse,
  ChatRequest,
  ChatResponse,
  SlackNotificationRequest,
  IntegrationResponse,
  JiraIssueRequest,
  JiraIssueResponse,
  GitHubIssueRequest,
  GitHubIssueResponse,
  SeverityClassificationRequest,
  SeverityClassificationResponse,
} from '@/types';

export async function uploadCrash(
  file: File,
  onUploadProgress?: (progress: number) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<UploadResponse>('/crashes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onUploadProgress && e.total) {
        onUploadProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return response.data;
}

export async function listCrashes(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<CrashAnalysis[]> {
  const response = await apiClient.get<CrashAnalysis[]>('/crashes/', { params });
  return response.data;
}

export async function getCrash(id: string): Promise<CrashAnalysis> {
  const response = await apiClient.get<CrashAnalysis>(`/crashes/${id}`);
  return response.data;
}

export async function deleteCrash(id: string): Promise<void> {
  await apiClient.delete(`/crashes/${id}`);
}

export async function batchAnalyze(data: BatchAnalysisRequest): Promise<BatchAnalysisResponse> {
  const response = await apiClient.post<BatchAnalysisResponse>('/crashes/batch/analyze', data);
  return response.data;
}

export async function clusterCrashes(crashIds?: string[]): Promise<BatchAnalysisResponse> {
  const response = await apiClient.post<BatchAnalysisResponse>('/crashes/batch/cluster', {
    crash_ids: crashIds ?? [],
  });
  return response.data;
}

export async function getSimilarCrashes(
  crashId: string,
  limit = 5,
  minSimilarity = 0.7
): Promise<SimilarCrashesResponse> {
  const response = await apiClient.post<SimilarCrashesResponse>('/crashes/similar', {
    crash_id: crashId,
    limit,
    min_similarity: minSimilarity,
  });
  return response.data;
}

export async function chatWithCrash(id: string, data: ChatRequest): Promise<ChatResponse> {
  const response = await apiClient.post<ChatResponse>(`/crashes/${id}/chat`, data);
  return response.data;
}

export async function sendSlackNotification(
  data: SlackNotificationRequest
): Promise<IntegrationResponse> {
  const response = await apiClient.post<IntegrationResponse>('/crashes/integrations/slack', data);
  return response.data;
}

export async function createJiraIssue(data: JiraIssueRequest): Promise<JiraIssueResponse> {
  const response = await apiClient.post<JiraIssueResponse>('/crashes/integrations/jira', data);
  return response.data;
}

export async function createGitHubIssue(data: GitHubIssueRequest): Promise<GitHubIssueResponse> {
  const response = await apiClient.post<GitHubIssueResponse>('/crashes/integrations/github', data);
  return response.data;
}

export async function classifySeverity(
  data: SeverityClassificationRequest
): Promise<SeverityClassificationResponse> {
  const response = await apiClient.post<SeverityClassificationResponse>(
    '/crashes/ml/classify-severity',
    data
  );
  return response.data;
}
