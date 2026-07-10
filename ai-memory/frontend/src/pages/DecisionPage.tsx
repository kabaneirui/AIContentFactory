import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { DecideTodayResponse } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, Loading, Stars } from "../components/ui";

export function DecisionPage() {
  const { accountId } = useAccount();
  const [season, setSeason] = useState("");
  const [festival, setFestival] = useState("");
  const [result, setResult] = useState<DecideTodayResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleDecide = async () => {
    if (!accountId) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.decideToday(accountId, {
        season: season || undefined,
        festival: festival || undefined,
        count: 5,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "决策失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>决策中心</h1>
        <p className="page-sub">今天发什么 — 70% 账号经验 + 30% 全网热点</p>
      </header>

      <Card title="决策参数">
        <div className="form-row">
          <label>
            节气
            <input
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              placeholder="如：夏至"
            />
          </label>
          <label>
            节日
            <input
              value={festival}
              onChange={(e) => setFestival(e.target.value)}
              placeholder="如：端午节"
            />
          </label>
        </div>
        <button className="btn btn-primary" onClick={handleDecide} disabled={loading}>
          {loading ? "生成中…" : "今天发什么"}
        </button>
      </Card>

      {error && <ErrorMessage message={error} />}
      {loading && <Loading text="综合决策中…" />}

      {result && (
        <div className="recommendations">
          <p className="meta-text">
            生成于 {new Date(result.generated_at).toLocaleString("zh-CN")}
          </p>
          {result.recommendations.map((rec) => (
            <Card key={rec.rank} className="rec-card">
              <div className="rec-header">
                <span className="rec-rank">#{rec.rank}</span>
                <h3>{rec.title}</h3>
                <Stars level={rec.predict_level} />
              </div>
              <div className="rec-stats">
                <span>预计播放 {rec.predict_view.toLocaleString()}</span>
                <span>建议发布 {rec.suggested_publish_time}</span>
                <span>综合分 {(rec.combined_score * 100).toFixed(0)}%</span>
              </div>
              {(rec.template || rec.hook) && (
                <div className="rec-tags">
                  {rec.template && <span className="tag">{rec.template}</span>}
                  {rec.hook && <span className="tag">{rec.hook}</span>}
                  {rec.matched_trend && <span className="tag tag-hot">{rec.matched_trend}</span>}
                </div>
              )}
              <ul className="reason-list">
                {rec.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
