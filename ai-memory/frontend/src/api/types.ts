export interface Account {
  id: number;
  name: string;
  platform: string;
  predict_threshold: number | null;
  auto_evolve: boolean;
  created_at: string;
}

export interface AccountCreate {
  name: string;
  platform: string;
}

export interface AccountUpdate {
  name?: string;
  platform?: string;
  predict_threshold?: number | null;
  auto_evolve?: boolean;
}

export interface AccountProfile {
  id: number;
  account_id: number;
  platform: string | null;
  account_type: string | null;
  best_category: string | null;
  best_scene: string | null;
  best_duration: string | null;
  best_publish_time: string | null;
  best_cta: string | null;
  best_hook: string | null;
  best_knowledge_source: string | null;
  locked_fields: string[] | null;
  updated_at: string;
}

export interface ProfileUpdate {
  locked_fields?: string[] | null;
}

export interface BrainLearning {
  id: number;
  account_id: number;
  learning_date: string;
  sample_size: number;
  summary: string;
  strength: string;
  weakness: string;
  trend: string;
  suggestion: string;
  optimization: string;
  prompt_version: string | null;
  stats_snapshot: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface VideoPerformance {
  views: number;
  finish_rate: number | null;
  rate_3s: number | null;
  likes: number;
  comments: number;
  shares: number;
  collects: number;
}

export interface VideoCreate {
  title: string;
  platform?: string;
  platform_video_id?: string;
  script?: string;
  hook?: string;
  template?: string;
  knowledge_source?: string;
  prompt?: string;
  scene_style?: string;
  duration?: number;
  cta?: string;
  publish_time?: string;
  season?: string;
  festival?: string;
  weather?: string;
  keyword?: string;
  category?: string;
  dna_tags?: Record<string, string>;
}

export interface PerformanceUpdate {
  views?: number;
  ctr?: number;
  rate_3s?: number;
  finish_rate?: number;
  average_watch?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  collects?: number;
  forwards?: number;
  fans_increase?: number;
  reach_level?: string;
  recommend_rate?: number;
  engagement_rate?: number;
}

export interface Video {
  id: number;
  account_id: number;
  platform: string;
  platform_video_id: string | null;
  title: string;
  hook: string | null;
  template: string | null;
  knowledge_source: string | null;
  prompt: string | null;
  scene_style: string | null;
  duration: number | null;
  cta: string | null;
  publish_time: string | null;
  dna_tags: Record<string, string> | null;
  lifecycle_status: string;
  created_at: string;
  performance: VideoPerformance | null;
}

export interface VideoMetadataUpdate {
  platform_video_id?: string | null;
}

export interface SyncLogEntry {
  id: number;
  content_memory_id: number;
  account_id: number;
  adapter: string;
  checkpoint: string | null;
  status: "success" | "no_data" | "failed" | "skipped";
  error: string | null;
  synced_at: string;
}

export interface SyncTriggerResponse {
  video_id: number;
  sync_log: SyncLogEntry;
  performance_updated: boolean;
}

export interface SyncLogListResponse {
  items: SyncLogEntry[];
  total: number;
}

export interface VideoListResponse {
  items: Video[];
  total: number;
  page: number;
  page_size: number;
}

export interface DecisionRecommendation {
  rank: number;
  title: string;
  predict_level: number;
  predict_view: number;
  suggested_publish_time: string;
  reasons: string[];
  combined_score: number;
  account_weight_score?: number;
  trend_weight_score?: number;
  matched_trend: string | null;
  template: string | null;
  hook: string | null;
  knowledge_source: string | null;
  scene_style: string | null;
  duration: number | null;
  cta: string | null;
}

export interface DecideTodayResponse {
  account_id: number;
  generated_at: string;
  season: string | null;
  festival: string | null;
  platform: string | null;
  recommendations: DecisionRecommendation[];
}

export interface GenerateScriptRequest {
  title: string;
  hook?: string;
  template?: string;
  knowledge_source?: string;
  scene_style?: string;
  duration?: number;
  cta?: string;
  season?: string;
  festival?: string;
  matched_trend?: string;
  reasons?: string[];
}

export interface GenerateScriptResponse {
  title: string;
  script: string;
  hook: string | null;
  template: string | null;
  knowledge_source: string | null;
  scene_style: string | null;
  duration: number | null;
  cta: string | null;
  season: string | null;
  festival: string | null;
  matched_trend: string | null;
  prompt_version: string | null;
  generated_by: "llm" | "rule";
}

export interface PipelinePublishResponse {
  success: boolean;
  video_id: number | null;
  lifecycle_status: string | null;
  dna_tags: Record<string, string> | null;
  sync_tasks_scheduled: number;
  prompt_version: string | null;
  message: string | null;
  steps: {
    prediction_checked: boolean;
    prediction_passed: boolean | null;
    content_memory_created: boolean;
    sync_tasks_scheduled: number;
    dna_tagged: boolean;
    performance_updated: boolean;
  };
}

export interface PredictionResult {
  predict_view: number;
  predict_finish_rate: number;
  predict_level: number;
  confidence: number;
  reason: string[];
  threshold: number;
  passed: boolean;
}

export interface PredictApiResponse {
  pass: boolean;
  prediction: PredictionResult;
  prediction_id: number;
}

export interface PromptVersion {
  id: number;
  account_id: number;
  version: string;
  prompt_content: string;
  change_log: string | null;
  video_count: number;
  avg_view: number;
  avg_finish_rate: number;
  recommend_score: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptVersionListResponse {
  items: PromptVersion[];
  active_version: string | null;
}

export interface PromptEvolveResponse {
  evolved: boolean;
  reason: string;
  new_version: PromptVersion | null;
  pending_review: boolean;
}

export interface VideoImportResult {
  imported: number;
  skipped: number;
  errors: { row: number; field: string | null; message: string }[];
  video_ids: number[];
}

export interface TrendTopic {
  id: number;
  topic: string;
  category: string | null;
  heat_score: number;
  source: string;
  trend_date: string;
  season: string | null;
  festival: string | null;
  trend_direction: "rising" | "falling" | "stable" | null;
  created_at: string;
  updated_at: string;
}

export interface TrendTopicCreate {
  topic: string;
  category?: string;
  heat_score?: number;
  source?: string;
  trend_date?: string;
  season?: string;
  festival?: string;
}

export interface TrendTopicUpdate {
  topic?: string;
  category?: string;
  heat_score?: number;
  source?: string;
  trend_date?: string;
  season?: string;
  festival?: string;
}

export interface TrendTopicListResponse {
  items: TrendTopic[];
  total: number;
}

export interface TrendImportResult {
  imported: number;
  skipped: number;
  errors: { row: number; field: string | null; message: string }[];
}

export interface PromptVersionCreate {
  prompt_content: string;
  change_log?: string;
  activate?: boolean;
}
