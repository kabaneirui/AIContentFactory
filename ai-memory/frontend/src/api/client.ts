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
  AccountProfile,
  BrainLearning,
  DecideTodayResponse,
  PredictApiResponse,
  PromptEvolveResponse,
  PromptVersion,
  PromptVersionListResponse,
  Video,
  VideoImportResult,
  VideoListResponse,
} from "./types";

export const api = {
  listAccounts: () => request<Account[]>("/accounts"),

  createAccount: (data: { name: string; platform: string }) =>
    request<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getProfile: (accountId: number) =>
    request<AccountProfile>(`/accounts/${accountId}/profile`),

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
    params: { page?: number; page_size?: number; lifecycle_status?: string } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.page) query.set("page", String(params.page));
    if (params.page_size) query.set("page_size", String(params.page_size));
    if (params.lifecycle_status) query.set("lifecycle_status", params.lifecycle_status);
    const qs = query.toString();
    return request<VideoListResponse>(
      `/accounts/${accountId}/videos${qs ? `?${qs}` : ""}`,
    );
  },

  getVideo: (videoId: number) => request<Video>(`/videos/${videoId}`),

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
};

export { ApiError };
