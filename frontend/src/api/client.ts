/**
 * PHASE 3: API Client
 * Handles all backend API communication
 */
import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

export interface CrashAnalysis {
  id: string;
  filename: string;
  file_size: number;
  file_hash: string;
  status: 'queued' | 'parsing' | 'analyzing' | 'completed' | 'failed';
  error_message?: string;
  
  // Parsed data
  exception_code?: string;
  exception_message?: string;
  faulting_module?: string;
  faulting_address?: string;
  stack_trace?: StackFrame[];
  loaded_modules?: ModuleInfo[];
  threads?: ThreadInfo[];
  
  // LLM analysis (nested object to match backend response)
  llm_analysis?: {
    root_cause: string;
    explanation?: string;
    severity: 'critical' | 'high' | 'medium' | 'low' | 'unknown';
    confidence: number;
    solutions: Solution[];
    references?: string[];
  };
  
  // Similar crashes
  similar_crash_ids?: string[];
  similar_crashes?: Array<{
    id: string;
    filename: string;
    similarity: number;
  }>;
  
  // Metadata
  platform?: string;
  architecture?: string;
  os_version?: string;
  
  // Timing
  parse_duration_seconds?: number;
  analysis_duration_seconds?: number;
  
  // Timestamps
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

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

export interface UploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        if (typeof window !== 'undefined') {
          const token = localStorage.getItem('auth_token');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  /**
   * Upload crash dump file
   */
  async uploadCrashDump(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<UploadResponse>(
      '/crashes/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * Get crash analysis by ID
   */
  async getCrashAnalysis(crashId: string): Promise<CrashAnalysis> {
    const response = await this.client.get<CrashAnalysis>(
      `/crashes/${crashId}`
    );
    return response.data;
  }

  /**
   * List all crash analyses
   */
  async listCrashAnalyses(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<CrashAnalysis[]> {
    const response = await this.client.get<CrashAnalysis[]>('/crashes/', {
      params,
    });
    return response.data;
  }

  /**
   * Delete crash analysis
   */
  async deleteCrashAnalysis(crashId: string): Promise<void> {
    await this.client.delete(`/crashes/${crashId}`);
  }

  /**
   * Poll for analysis status updates
   */
  async pollAnalysisStatus(
    crashId: string,
    onUpdate: (analysis: CrashAnalysis) => void,
    interval: number = 2000
  ): Promise<CrashAnalysis> {
    return new Promise((resolve, reject) => {
      const poll = setInterval(async () => {
        try {
          const analysis = await this.getCrashAnalysis(crashId);
          onUpdate(analysis);

          if (analysis.status === 'completed' || analysis.status === 'failed') {
            clearInterval(poll);
            resolve(analysis);
          }
        } catch (error) {
          clearInterval(poll);
          reject(error);
        }
      }, interval);
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
