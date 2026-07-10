import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { PredictApiResponse } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, Loading, Stars } from "../components/ui";

export function PredictPage() {
  const { accountId } = useAccount();
  const [title, setTitle] = useState("");
  const [script, setScript] = useState("");
  const [hook, setHook] = useState("");
  const [template, setTemplate] = useState("");
  const [result, setResult] = useState<PredictApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePredict = async () => {
    if (!accountId || !title.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await api.predict(accountId, {
        title: title.trim(),
        script: script || undefined,
        hook: hook || undefined,
        template: template || undefined,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "预测失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>预测拦截</h1>
        <p className="page-sub">发布前预测播放量，低于阈值建议重新生成</p>
      </header>

      <Card title="待发布文案">
        <div className="form-stack">
          <label>
            标题 *
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入视频标题"
            />
          </label>
          <label>
            脚本
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              rows={4}
              placeholder="口播脚本（可选）"
            />
          </label>
          <div className="form-row">
            <label>
              Hook
              <input
                value={hook}
                onChange={(e) => setHook(e.target.value)}
                placeholder="如：老祖宗"
              />
            </label>
            <label>
              栏目
              <input
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                placeholder="如：口诀"
              />
            </label>
          </div>
        </div>
        <button
          className="btn btn-primary"
          onClick={handlePredict}
          disabled={loading || !title.trim()}
        >
          {loading ? "预测中…" : "开始预测"}
        </button>
      </Card>

      {error && <ErrorMessage message={error} />}
      {loading && <Loading text="预测引擎分析中…" />}

      {result && (
        <Card
          title="预测结果"
          className={result.pass ? "result-pass" : "result-fail"}
        >
          <div className="predict-header">
            <span className={`verdict ${result.pass ? "pass" : "fail"}`}>
              {result.pass ? "✓ 通过" : "✗ 建议重生成"}
            </span>
            <Stars level={result.prediction.predict_level} />
          </div>

          <div className="predict-stats">
            <div className="stat-box">
              <span className="stat-label">预计播放</span>
              <span className="stat-value">
                {result.prediction.predict_view.toLocaleString()}
              </span>
            </div>
            <div className="stat-box">
              <span className="stat-label">预计完播率</span>
              <span className="stat-value">
                {(result.prediction.predict_finish_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="stat-box">
              <span className="stat-label">置信度</span>
              <span className="stat-value">
                {(result.prediction.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="stat-box">
              <span className="stat-label">拦截线</span>
              <span className="stat-value">
                {result.prediction.threshold.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="report-section">
            <strong>预测理由</strong>
            <ul className="reason-list">
              {result.prediction.reason.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <p className="meta-text">预测 ID: {result.prediction_id}</p>
        </Card>
      )}
    </div>
  );
}
