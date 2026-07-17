import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { VideoCreate } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, FormField } from "../components/ui";

export function VideoCreatePage() {
  const { accountId } = useAccount();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [hook, setHook] = useState("");
  const [template, setTemplate] = useState("");
  const [knowledgeSource, setKnowledgeSource] = useState("");
  const [sceneStyle, setSceneStyle] = useState("");
  const [duration, setDuration] = useState("");
  const [cta, setCta] = useState("");
  const [category, setCategory] = useState("");
  const [platformVideoId, setPlatformVideoId] = useState("");
  const [publishTime, setPublishTime] = useState("");
  const [script, setScript] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accountId || !title.trim()) return;

    setSubmitting(true);
    setError("");
    try {
      const payload: VideoCreate = {
        title: title.trim(),
      };
      if (hook.trim()) payload.hook = hook.trim();
      if (template.trim()) payload.template = template.trim();
      if (knowledgeSource.trim()) payload.knowledge_source = knowledgeSource.trim();
      if (sceneStyle.trim()) payload.scene_style = sceneStyle.trim();
      if (cta.trim()) payload.cta = cta.trim();
      if (category.trim()) payload.category = category.trim();
      if (platformVideoId.trim()) payload.platform_video_id = platformVideoId.trim();
      if (script.trim()) payload.script = script.trim();
      if (duration.trim()) payload.duration = Number(duration);
      if (publishTime) {
        payload.publish_time = new Date(publishTime).toISOString();
      }

      const video = await api.createVideo(accountId, payload);
      navigate(`/videos/${video.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "发布失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <Link to="/videos" className="back-link">
        ← 返回列表
      </Link>

      <header className="page-header">
        <h1>发布视频</h1>
        <p className="page-sub">写入 Video Memory 并自动排队 DNA 打标</p>
      </header>

      <Card title="视频信息">
        <form className="form-stack" onSubmit={handleSubmit}>
          {error && <ErrorMessage message={error} />}

          <FormField label="标题 *" htmlFor="video-title">
            <input
              id="video-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：老祖宗留下来的养阳口诀"
              required
            />
          </FormField>

          <div className="form-row">
            <FormField label="Hook" htmlFor="video-hook">
              <input
                id="video-hook"
                value={hook}
                onChange={(e) => setHook(e.target.value)}
                placeholder="例如：老祖宗"
              />
            </FormField>
            <FormField label="栏目/模板" htmlFor="video-template">
              <input
                id="video-template"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                placeholder="例如：口诀"
              />
            </FormField>
          </div>

          <div className="form-row">
            <FormField label="知识来源" htmlFor="video-knowledge">
              <input
                id="video-knowledge"
                value={knowledgeSource}
                onChange={(e) => setKnowledgeSource(e.target.value)}
                placeholder="例如：黄帝内经"
              />
            </FormField>
            <FormField label="画面风格" htmlFor="video-scene">
              <input
                id="video-scene"
                value={sceneStyle}
                onChange={(e) => setSceneStyle(e.target.value)}
                placeholder="例如：古风"
              />
            </FormField>
          </div>

          <div className="form-row">
            <FormField label="时长（秒）" htmlFor="video-duration">
              <input
                id="video-duration"
                type="number"
                min="1"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="32"
              />
            </FormField>
            <FormField label="CTA" htmlFor="video-cta">
              <input
                id="video-cta"
                value={cta}
                onChange={(e) => setCta(e.target.value)}
                placeholder="例如：收藏"
              />
            </FormField>
          </div>

          <div className="form-row">
            <FormField label="分类" htmlFor="video-category">
              <input
                id="video-category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="例如：养生"
              />
            </FormField>
            <FormField label="发布时间" htmlFor="video-publish-time">
              <input
                id="video-publish-time"
                type="datetime-local"
                value={publishTime}
                onChange={(e) => setPublishTime(e.target.value)}
              />
            </FormField>
          </div>

          <FormField label="平台视频ID（如 B站 BV号）" htmlFor="video-platform-id">
            <input
              id="video-platform-id"
              value={platformVideoId}
              onChange={(e) => setPlatformVideoId(e.target.value)}
              placeholder="例如：BV1xx4y1x7xx（填写后可在详情页一键同步播放数据）"
            />
          </FormField>

          <FormField label="口播稿" htmlFor="video-script">
            <textarea
              id="video-script"
              rows={6}
              value={script}
              onChange={(e) => setScript(e.target.value)}
              placeholder="完整口播文案（可选，有助于 DNA 打标）"
            />
          </FormField>

          <p className="hint">
            填写发布时间后，视频将进入已发布状态并创建 T+1h / T+24h / T+7d 同步任务。
          </p>

          <div className="form-actions">
            <Link to="/videos" className="btn">
              取消
            </Link>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "发布中…" : "发布视频"}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
