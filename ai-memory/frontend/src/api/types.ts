export interface Account {
  id: number;
  name: string;
  platform: string;
  predict_threshold: number | null;
  auto_evolve: boolean;
  created_at: string;
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

export interface Video {
  id: number;
  account_id: number;
  platform: string;
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
  template: string | null;
  hook: string | null;
  matched_trend: string | null;
}

export interface DecideTodayResponse {
  account_id: number;
  generated_at: string;
  season: string | null;
  festival: string | null;
  recommendations: DecisionRecommendation[];
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
