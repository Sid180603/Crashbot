export type AnalysisStatus = 'queued' | 'parsing' | 'analyzing' | 'completed' | 'failed';
export type CrashSeverity = 'critical' | 'high' | 'medium' | 'low' | 'unknown';

export interface StackFrame {
  index: number;
  module?: string;
  function?: string;
  address?: string;
  offset?: string;
  source_file?: string;
  line_number?: number;
}

export interface ThreadInfo {
  thread_id: number;
  is_current: boolean;
  stack_frames: StackFrame[];
}

export interface ModuleInfo {
  name: string;
  base_address?: string;
  size?: number;
  version?: string;
  path?: string;
}

export interface Solution {
  title: string;
  description: string;
  priority: number;
  code_example?: string;
  references?: string[];
}

export interface LLMAnalysis {
  root_cause: string;
  explanation?: string;
  severity: CrashSeverity;
  confidence: number;
  solutions: Solution[];
  references?: string[];
}

export interface CrashAnalysis {
  id: string;
  filename: string;
  file_size: number;
  file_hash: string;
  status: AnalysisStatus;
  error_message?: string;
  exception_code?: string;
  exception_message?: string;
  faulting_module?: string;
  faulting_address?: string;
  stack_trace?: StackFrame[];
  loaded_modules?: ModuleInfo[];
  threads?: ThreadInfo[];
  llm_analysis?: LLMAnalysis;
  root_cause?: string;
  explanation?: string;
  solutions?: Solution[];
  severity?: CrashSeverity;
  confidence_score?: number;
  references?: string[];
  similar_crash_ids?: string[];
  similar_crashes?: Array<{
    id: string;
    filename: string;
    similarity: number;
    exception_code?: string;
    faulting_module?: string;
    platform?: string;
  }>;
  platform?: string;
  architecture?: string;
  os_version?: string;
  parse_duration_seconds?: number;
  analysis_duration_seconds?: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface UploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

export interface ClusterInfo {
  cluster_id: number;
  crash_count: number;
  crash_ids: string[];
  pattern: string;
}

export interface BatchAnalysisRequest {
  crash_ids: string[];
}

export interface BatchAnalysisResponse {
  total_crashes: number;
  common_exceptions: Record<string, number>;
  common_modules: Record<string, number>;
  clusters: ClusterInfo[];
  regression_detected: boolean;
  timeline: Array<Record<string, unknown>>;
}

export interface SimilarCrashResult {
  crash_id: string;
  similarity: number;
  exception_code?: string;
  faulting_module?: string;
  platform?: string;
}

export interface SimilarCrashesResponse {
  crash_id: string;
  similar_crashes: SimilarCrashResult[];
  count: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  question: string;
}

export interface ChatResponse {
  answer: string;
  conversation_history: ChatMessage[];
}

export interface SlackNotificationRequest {
  crash_id: string;
  channel?: string;
}

export interface JiraIssueRequest {
  crash_id: string;
  project_key: string;
  issue_type?: string;
  priority?: string;
}

export interface JiraIssueResponse {
  issue_key: string;
  issue_url: string;
  created: boolean;
}

export interface GitHubIssueRequest {
  crash_id: string;
  repository: string;
  labels?: string[];
}

export interface GitHubIssueResponse {
  issue_number: number;
  issue_url: string;
  created: boolean;
}

export interface IntegrationResponse {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export interface SeverityResult {
  crash_id: string;
  severity: string;
  confidence: number;
  explanation: string;
}

export interface SeverityClassificationRequest {
  crash_ids: string[];
}

export interface SeverityClassificationResponse {
  results: SeverityResult[];
  distribution: Record<string, number>;
}
