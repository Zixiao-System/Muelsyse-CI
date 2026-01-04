// =============================================================================
// Type Definitions
// =============================================================================

export interface Pipeline {
  id: string;
  name: string;
  description: string;
  status: PipelineStatus;
  branch: string;
  trigger: TriggerType;
  createdAt: string;
  updatedAt: string;
  lastRunAt?: string;
  totalRuns: number;
  successRate: number;
  avgDuration: string;
  stages: PipelineStage[];
}

export interface PipelineStage {
  name: string;
  commands: string[];
  timeout?: number;
  environment?: Record<string, string>;
}

export interface Execution {
  id: string;
  pipelineId: string;
  pipelineName: string;
  status: ExecutionStatus;
  duration: string;
  startedAt: string;
  finishedAt?: string;
  commit: string;
  commitMessage: string;
  branch: string;
  author: string;
  runnerId?: string;
  runnerName?: string;
  jobs: Job[];
}

export interface Job {
  id: string;
  executionId: string;
  name: string;
  status: ExecutionStatus;
  duration: string;
  startedAt: string;
  finishedAt?: string;
  logs: LogEntry[];
}

export interface LogEntry {
  time: string;
  level: LogLevel;
  message: string;
}

export interface Runner {
  id: string;
  name: string;
  status: RunnerStatus;
  platform: Platform;
  arch: Architecture;
  version: string;
  labels: string[];
  lastSeenAt: string;
  currentJobId?: string;
  currentJobName?: string;
}

export interface Secret {
  id: string;
  name: string;
  scope: SecretScope;
  createdAt: string;
  updatedAt: string;
  usedIn: string[];
}

export interface User {
  id: string;
  username: string;
  email: string;
  avatarUrl?: string;
  role: UserRole;
}

export interface Workspace {
  id: string;
  name: string;
  defaultBranch: string;
  timezone: string;
  createdAt: string;
}

// =============================================================================
// Enums
// =============================================================================

export type PipelineStatus = "active" | "inactive" | "archived";
export type ExecutionStatus = "pending" | "running" | "success" | "failed" | "cancelled";
export type RunnerStatus = "online" | "offline" | "busy";
export type TriggerType = "push" | "pull_request" | "manual" | "schedule";
export type Platform = "Linux" | "macOS" | "Windows";
export type Architecture = "x86_64" | "arm64" | "arm";
export type SecretScope = "organization" | "repository" | "pipeline";
export type UserRole = "admin" | "member" | "viewer";
export type LogLevel = "info" | "warn" | "error" | "debug";

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// =============================================================================
// Request Types
// =============================================================================

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

export interface PipelineFilters extends PaginationParams {
  status?: PipelineStatus;
  search?: string;
}

export interface ExecutionFilters extends PaginationParams {
  pipelineId?: string;
  status?: ExecutionStatus;
  branch?: string;
  search?: string;
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  branch: string;
  trigger: TriggerType;
  stages: PipelineStage[];
}

export interface UpdatePipelineRequest {
  name?: string;
  description?: string;
  branch?: string;
  trigger?: TriggerType;
  stages?: PipelineStage[];
}

export interface CreateSecretRequest {
  name: string;
  value: string;
  scope: SecretScope;
}

export interface UpdateSecretRequest {
  value: string;
}

// =============================================================================
// API Client Configuration
// =============================================================================

const API_BASE_URL = typeof window !== "undefined"
  ? (window as unknown as { ENV?: { API_BASE_URL?: string } }).ENV?.API_BASE_URL || "/api"
  : process.env.API_BASE_URL || "/api";

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

// =============================================================================
// API Client Implementation
// =============================================================================

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { params, ...fetchOptions } = options;
    const url = this.buildUrl(path, params);

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...fetchOptions.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        code: "UNKNOWN_ERROR",
        message: response.statusText,
      }));
      throw new ApiClientError(error.message, error.code, response.status);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // ---------------------------------------------------------------------------
  // Pipelines
  // ---------------------------------------------------------------------------

  async getPipelines(filters?: PipelineFilters): Promise<ApiResponse<Pipeline[]>> {
    return this.request<ApiResponse<Pipeline[]>>("/pipelines", { params: filters as Record<string, string | number | boolean | undefined> });
  }

  async getPipeline(id: string): Promise<ApiResponse<Pipeline>> {
    return this.request<ApiResponse<Pipeline>>(`/pipelines/${id}`);
  }

  async createPipeline(data: CreatePipelineRequest): Promise<ApiResponse<Pipeline>> {
    return this.request<ApiResponse<Pipeline>>("/pipelines", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updatePipeline(id: string, data: UpdatePipelineRequest): Promise<ApiResponse<Pipeline>> {
    return this.request<ApiResponse<Pipeline>>(`/pipelines/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deletePipeline(id: string): Promise<void> {
    return this.request<void>(`/pipelines/${id}`, {
      method: "DELETE",
    });
  }

  async runPipeline(id: string, options?: { branch?: string }): Promise<ApiResponse<Execution>> {
    return this.request<ApiResponse<Execution>>(`/pipelines/${id}/run`, {
      method: "POST",
      body: JSON.stringify(options || {}),
    });
  }

  // ---------------------------------------------------------------------------
  // Executions
  // ---------------------------------------------------------------------------

  async getExecutions(filters?: ExecutionFilters): Promise<ApiResponse<Execution[]>> {
    return this.request<ApiResponse<Execution[]>>("/executions", { params: filters as Record<string, string | number | boolean | undefined> });
  }

  async getExecution(id: string): Promise<ApiResponse<Execution>> {
    return this.request<ApiResponse<Execution>>(`/executions/${id}`);
  }

  async cancelExecution(id: string): Promise<ApiResponse<Execution>> {
    return this.request<ApiResponse<Execution>>(`/executions/${id}/cancel`, {
      method: "POST",
    });
  }

  async rerunExecution(id: string): Promise<ApiResponse<Execution>> {
    return this.request<ApiResponse<Execution>>(`/executions/${id}/rerun`, {
      method: "POST",
    });
  }

  async getExecutionLogs(id: string, jobId?: string): Promise<ApiResponse<LogEntry[]>> {
    const path = jobId
      ? `/executions/${id}/jobs/${jobId}/logs`
      : `/executions/${id}/logs`;
    return this.request<ApiResponse<LogEntry[]>>(path);
  }

  // ---------------------------------------------------------------------------
  // Runners
  // ---------------------------------------------------------------------------

  async getRunners(): Promise<ApiResponse<Runner[]>> {
    return this.request<ApiResponse<Runner[]>>("/runners");
  }

  async getRunner(id: string): Promise<ApiResponse<Runner>> {
    return this.request<ApiResponse<Runner>>(`/runners/${id}`);
  }

  async deleteRunner(id: string): Promise<void> {
    return this.request<void>(`/runners/${id}`, {
      method: "DELETE",
    });
  }

  async getRunnerRegistrationToken(): Promise<ApiResponse<{ token: string }>> {
    return this.request<ApiResponse<{ token: string }>>("/runners/registration-token", {
      method: "POST",
    });
  }

  // ---------------------------------------------------------------------------
  // Secrets
  // ---------------------------------------------------------------------------

  async getSecrets(): Promise<ApiResponse<Secret[]>> {
    return this.request<ApiResponse<Secret[]>>("/secrets");
  }

  async createSecret(data: CreateSecretRequest): Promise<ApiResponse<Secret>> {
    return this.request<ApiResponse<Secret>>("/secrets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateSecret(id: string, data: UpdateSecretRequest): Promise<ApiResponse<Secret>> {
    return this.request<ApiResponse<Secret>>(`/secrets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteSecret(id: string): Promise<void> {
    return this.request<void>(`/secrets/${id}`, {
      method: "DELETE",
    });
  }

  // ---------------------------------------------------------------------------
  // User & Auth
  // ---------------------------------------------------------------------------

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.request<ApiResponse<User>>("/user");
  }

  async login(username: string, password: string): Promise<ApiResponse<{ token: string; user: User }>> {
    return this.request<ApiResponse<{ token: string; user: User }>>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  }

  async logout(): Promise<void> {
    return this.request<void>("/auth/logout", {
      method: "POST",
    });
  }

  // ---------------------------------------------------------------------------
  // Workspace
  // ---------------------------------------------------------------------------

  async getWorkspace(): Promise<ApiResponse<Workspace>> {
    return this.request<ApiResponse<Workspace>>("/workspace");
  }

  async updateWorkspace(data: Partial<Workspace>): Promise<ApiResponse<Workspace>> {
    return this.request<ApiResponse<Workspace>>("/workspace", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }
}

// =============================================================================
// Custom Error Class
// =============================================================================

export class ApiClientError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
  }
}

// =============================================================================
// Export singleton instance
// =============================================================================

export const api = new ApiClient();

// Export class for custom instances
export { ApiClient };
