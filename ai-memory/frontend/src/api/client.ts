const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new ApiError(String(detail), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

import type {
  Account,
  AccountCreate,
  AccountProfile,
  AccountUpdate,
  BrainLearning,
  DecideTodayResponse,
  PerformanceUpdate,
  GenerateScriptRequest,
  GenerateScriptResponse,
  PipelinePublishResponse,
  PredictApiResponse,
  ProfileUpdate,
  PromptEvolveResponse,
  PromptVersion,
  PromptVersionCreate,
  PromptVersionListResponse,
  SyncLogListResponse,
  SyncTriggerResponse,
  TrendImportResult,
  TrendTopic,
  TrendTopicCreate,
  TrendTopicListResponse,
  TrendTopicUpdate,
  Video,
  VideoCreate,
  VideoImportResult,
  VideoListResponse,
  VideoMetadataUpdate,
} from "./types";

export const api = {
  listAccounts: () => request<Account[]>("/accounts"),

  createAccount: (data: AccountCreate) =>
    request<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateAccount: (id: number, data: AccountUpdate) =>
    request<Account>(`/accounts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteAccount: (id: number) =>
    request<void>(`/accounts/${id}`, { method: "DELETE" }),

  getProfile: (accountId: number) =>
    request<AccountProfile>(`/accounts/${accountId}/profile`),

  updateProfile: (accountId: number, data: ProfileUpdate) =>
    request<AccountProfile>(`/accounts/${accountId}/profile`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getLatestLearning: (accountId: number) =>
    request<BrainLearning>(`/accounts/${accountId}/learning/latest`),

  decideToday: (
    accountId: number,
    data: { season?: string; festival?: string; count?: number },
  ) =>
    request<DecideTodayResponse>(`/accounts/${accountId}/decide/today`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listVideos: (
    accountId: number,
    params: {
      page?: number;
      page_size?: number;
      lifecycle_status?: string;
      sort_by?: "created_at" | "publish_time" | "views" | "title";
      sort_order?: "asc" | "desc";
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.page_size) query.set("page_size", String(params.page_size));
    if (params.lifecycle_status) query.set("lifecycle_status", params.lifecycle_status);
    if (params.sort_by) query.set("sort_by", params.sort_by);
    if (params.sort_order) query.set("sort_order", params.sort_order);
    const qs = query.toString();
    return request<VideoListResponse>(
      `/accounts/${accountId}/videos${qs ? `?${qs}` : ""}`,
    );
  },

  getVideo: (videoId: number) => request<Video>(`/videos/${videoId}`),

  deleteVideo: (videoId: number) =>
    request<void>(`/videos/${videoId}`, { method: "DELETE" }),

  createVideo: (accountId: number, data: VideoCreate) =>
    request<Video>(`/accounts/${accountId}/videos`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateVideoPerformance: (videoId: number, data: PerformanceUpdate) =>
    request<Video>(`/videos/${videoId}/performance`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  updateVideoMetadata: (videoId: number, data: VideoMetadataUpdate) =>
    request<Video>(`/videos/${videoId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  syncVideoPerformance: (videoId: number) =>
    request<SyncTriggerResponse>(`/videos/${videoId}/sync`, {
      method: "POST",
    }),

  listVideoSyncLogs: (videoId: number, limit = 10) =>
    request<SyncLogListResponse>(`/videos/${videoId}/sync-logs?limit=${limit}`),

  predict: (
    accountId: number,
    data: {
      title: string;
      script?: string;
      hook?: string;
      template?: string;
      knowledge_source?: string;
      scene_style?: string;
      duration?: number;
      cta?: string;
    },
  ) =>
    request<PredictApiResponse>(`/accounts/${accountId}/predict`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listPrompts: (accountId: number) =>
    request<PromptVersionListResponse>(`/accounts/${accountId}/prompts`),

  getActivePrompt: (accountId: number) =>
    request<PromptVersion>(`/accounts/${accountId}/prompts/active`),

  evolvePrompt: (accountId: number, force = false) =>
    request<PromptEvolveResponse>(`/accounts/${accountId}/prompts/evolve`, {
      method: "POST",
      body: JSON.stringify({ force }),
    }),

  activatePrompt: (accountId: number, versionId: number) =>
    request<{ activated_version: string; previous_version: string | null }>(
      `/accounts/${accountId}/prompts/${versionId}/activate`,
      { method: "POST" },
    ),

  createPromptVersion: (accountId: number, data: PromptVersionCreate) =>
    request<PromptVersion>(`/accounts/${accountId}/prompts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listTrends: (
    params: {
      category?: string;
      season?: string;
      festival?: string;
      source?: string;
      date_from?: string;
      date_to?: string;
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.category) query.set("category", params.category);
    if (params.season) query.set("season", params.season);
    if (params.festival) query.set("festival", params.festival);
    if (params.source) query.set("source", params.source);
    if (params.date_from) query.set("date_from", params.date_from);
    if (params.date_to) query.set("date_to", params.date_to);
    if (params.limit) query.set("limit", String(params.limit));
    if (params.offset) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<TrendTopicListResponse>(`/trends${qs ? `?${qs}` : ""}`);
  },

  createTrend: (data: TrendTopicCreate) =>
    request<TrendTopic>("/trends", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateTrend: (id: number, data: TrendTopicUpdate) =>
    request<TrendTopic>(`/trends/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteTrend: (id: number) =>
    request<void>(`/trends/${id}`, { method: "DELETE" }),

  importTrendsCsv: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_BASE}/trends/import/csv`, {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(body.detail ?? response.statusText, response.status);
    }
    return response.json() as Promise<TrendImportResult>;
  },

  importVideosJson: (
    accountId: number,
    videos: Record<string, unknown>[],
  ) =>
    request<VideoImportResult>(`/accounts/${accountId}/videos/import`, {
      method: "POST",
      body: JSON.stringify({ videos }),
    }),

  importVideosCsv: async (accountId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${API_BASE}/accounts/${accountId}/videos/import/csv`,
      { method: "POST", body: form },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(body.detail ?? response.statusText, response.status);
    }
    return response.json() as Promise<VideoImportResult>;
  },

  generateScript: (accountId: number, data: GenerateScriptRequest) =>
    request<GenerateScriptResponse>(`/accounts/${accountId}/workflow/generate-script`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  pipelinePublish: (
    accountId: number,
    data: {
      title: string;
      script?: string;
      hook?: string;
      template?: string;
      knowledge_source?: string;
      scene_style?: string;
      duration?: number;
      cta?: string;
      season?: string;
      festival?: string;
      category?: string;
      require_prediction_pass?: boolean;
      tag_inline?: boolean;
    },
  ) =>
    request<PipelinePublishResponse>(`/accounts/${accountId}/pipeline/publish`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export { ApiError };
