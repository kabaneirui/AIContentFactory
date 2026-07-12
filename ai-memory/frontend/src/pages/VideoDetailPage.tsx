import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { PerformanceUpdate, Video } from "../api/types";
import { Card, ErrorMessage, FormField, LifecycleBadge, Loading } from "../components/ui";

const LIFECYCLE_STEPS = [
  "created",
  "published",
  "syncing",
  "tagged",
  "learned",
  "archived",
];

function toInputRate(value: number | null | undefined): string {
  if (value == null) return "";
  return String(Math.round(value * 1000) / 10);
}

function fromInputRate(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const n = Number(value);
  if (Number.isNaN(n)) return undefined;
  return n / 100;
}

export function VideoDetailPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [editingPerformance, setEditingPerformance] = useState(false);
  const [views, setViews] = useState("");
  const [finishRate, setFinishRate] = useState("");
  const [rate3s, setRate3s] = useState("");
  const [likes, setLikes] = useState("");
  const [comments, setComments] = useState("");
  const [collects, setCollects] = useState("");
  const [savingPerformance, setSavingPerformance] = useState(false);
  const [performanceError, setPerformanceError] = useState("");

  const loadVideo = async (id: number) => {
    const data = await api.getVideo(id);
    setVideo(data);
    return data;
  };

  useEffect(() => {
    if (!videoId) return;
    setLoading(true);
    loadVideo(Number(videoId))
      .catch((e) => setError(e instanceof ApiError ? String(e.message) : "加载失败"))
      .finally(() => setLoading(false));
  }, [videoId]);

  const startEditPerformance = () => {
    if (!video) return;
    const p = video.performance;
    setViews(p ? String(p.views) : "0");
    setFinishRate(toInputRate(p?.finish_rate));
    setRate3s(toInputRate(p?.rate_3s));
    setLikes(p ? String(p.likes) : "0");
    setComments(p ? String(p.comments) : "0");
    setCollects(p ? String(p.collects) : "0");
    setPerformanceError("");
    setEditingPerformance(true);
  };

  const handleSavePerformance = async () => {
    if (!videoId) return;
    setSavingPerformance(true);
    setPerformanceError("");
    try {
      const payload: PerformanceUpdate = {
        views: Number(views) || 0,
        likes: Number(likes) || 0,
        comments: Number(comments) || 0,
        collects: Number(collects) || 0,
      };
      const fr = fromInputRate(finishRate);
      const r3 = fromInputRate(rate3s);
      if (fr != null) payload.finish_rate = fr;
      if (r3 != null) payload.rate_3s = r3;

      const updated = await api.updateVideoPerformance(Number(videoId), payload);
      setVideo(updated);
      setEditingPerformance(false);
    } catch (e) {
      setPerformanceError(e instanceof ApiError ? String(e.message) : "保存失败");
    } finally {
      setSavingPerformance(false);
    }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;
  if (!video) return <ErrorMessage message="视频不存在" />;

  const currentIdx = LIFECYCLE_STEPS.indexOf(video.lifecycle_status);

  return (
    <div className="page">
      <Link to="/videos" className="back-link">
        ← 返回列表
      </Link>

      <header className="page-header">
        <h1>{video.title}</h1>
        <LifecycleBadge status={video.lifecycle_status} />
      </header>

      <Card title="生命周期">
        <div className="timeline">
          {LIFECYCLE_STEPS.map((step, idx) => (
            <div
              key={step}
              className={`timeline-step ${idx <= currentIdx ? "done" : ""} ${idx === currentIdx ? "current" : ""}`}
            >
              <div className="timeline-dot" />
              <span>{step}</span>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid-2">
        <Card title="内容信息">
          <dl className="detail-list">
            <dt>Hook</dt>
            <dd>{video.hook ?? "—"}</dd>
            <dt>栏目</dt>
            <dd>{video.template ?? "—"}</dd>
            <dt>画面</dt>
            <dd>{video.scene_style ?? "—"}</dd>
            <dt>知识来源</dt>
            <dd>{video.knowledge_source ?? "—"}</dd>
            <dt>CTA</dt>
            <dd>{video.cta ?? "—"}</dd>
            <dt>时长</dt>
            <dd>{video.duration ? `${video.duration}s` : "—"}</dd>
            <dt>Prompt 版本</dt>
            <dd>{video.prompt ?? "—"}</dd>
          </dl>
        </Card>

        <Card
          title="表现数据"
          className="performance-card"
        >
          {!editingPerformance ? (
            <>
              {video.performance ? (
                <dl className="detail-list">
                  <dt>播放量</dt>
                  <dd>{video.performance.views.toLocaleString()}</dd>
                  <dt>完播率</dt>
                  <dd>
                    {video.performance.finish_rate != null
                      ? `${(video.performance.finish_rate * 100).toFixed(1)}%`
                      : "—"}
                  </dd>
                  <dt>3秒留存</dt>
                  <dd>
                    {video.performance.rate_3s != null
                      ? `${(video.performance.rate_3s * 100).toFixed(1)}%`
                      : "—"}
                  </dd>
                  <dt>点赞</dt>
                  <dd>{video.performance.likes}</dd>
                  <dt>评论</dt>
                  <dd>{video.performance.comments}</dd>
                  <dt>收藏</dt>
                  <dd>{video.performance.collects}</dd>
                </dl>
              ) : (
                <p>暂无表现数据，点击下方编辑录入。</p>
              )}
              <button type="button" className="btn btn-sm" onClick={startEditPerformance}>
                编辑表现数据
              </button>
            </>
          ) : (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                handleSavePerformance();
              }}
            >
              {performanceError && <ErrorMessage message={performanceError} />}
              <FormField label="播放量" htmlFor="perf-views">
                <input
                  id="perf-views"
                  type="number"
                  min="0"
                  value={views}
                  onChange={(e) => setViews(e.target.value)}
                />
              </FormField>
              <div className="form-row">
                <FormField label="完播率 (%)" htmlFor="perf-finish">
                  <input
                    id="perf-finish"
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={finishRate}
                    onChange={(e) => setFinishRate(e.target.value)}
                    placeholder="28.5"
                  />
                </FormField>
                <FormField label="3秒留存 (%)" htmlFor="perf-3s">
                  <input
                    id="perf-3s"
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={rate3s}
                    onChange={(e) => setRate3s(e.target.value)}
                  />
                </FormField>
              </div>
              <div className="form-row">
                <FormField label="点赞" htmlFor="perf-likes">
                  <input
                    id="perf-likes"
                    type="number"
                    min="0"
                    value={likes}
                    onChange={(e) => setLikes(e.target.value)}
                  />
                </FormField>
                <FormField label="评论" htmlFor="perf-comments">
                  <input
                    id="perf-comments"
                    type="number"
                    min="0"
                    value={comments}
                    onChange={(e) => setComments(e.target.value)}
                  />
                </FormField>
                <FormField label="收藏" htmlFor="perf-collects">
                  <input
                    id="perf-collects"
                    type="number"
                    min="0"
                    value={collects}
                    onChange={(e) => setCollects(e.target.value)}
                  />
                </FormField>
              </div>
              <div className="form-actions">
                <button
                  type="button"
                  className="btn"
                  onClick={() => setEditingPerformance(false)}
                  disabled={savingPerformance}
                >
                  取消
                </button>
                <button type="submit" className="btn btn-primary" disabled={savingPerformance}>
                  {savingPerformance ? "保存中…" : "保存"}
                </button>
              </div>
            </form>
          )}
        </Card>
      </div>

      {video.dna_tags && (
        <Card title="Content DNA">
          <div className="dna-tags">
            {Object.entries(video.dna_tags).map(([k, v]) => (
              <span key={k} className="tag">
                {k}: {v}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
