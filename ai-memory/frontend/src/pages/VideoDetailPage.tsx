import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Video } from "../api/types";
import { Card, ErrorMessage, LifecycleBadge, Loading } from "../components/ui";

const LIFECYCLE_STEPS = [
  "created",
  "published",
  "syncing",
  "tagged",
  "learned",
  "archived",
];

export function VideoDetailPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!videoId) return;
    api
      .getVideo(Number(videoId))
      .then(setVideo)
      .catch((e) => setError(e instanceof ApiError ? String(e.message) : "加载失败"))
      .finally(() => setLoading(false));
  }, [videoId]);

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

        <Card title="表现数据">
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
              <dt>收藏</dt>
              <dd>{video.performance.collects}</dd>
            </dl>
          ) : (
            <p>暂无表现数据</p>
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
