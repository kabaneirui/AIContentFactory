import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AccountProfile, BrainLearning } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, Loading } from "../components/ui";

export function HomePage() {
  const { accountId, currentAccount } = useAccount();
  const [profile, setProfile] = useState<AccountProfile | null>(null);
  const [learning, setLearning] = useState<BrainLearning | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!accountId) return;
    setLoading(true);
    setError("");

    Promise.allSettled([
      api.getProfile(accountId),
      api.getLatestLearning(accountId),
    ]).then(([profileResult, learningResult]) => {
      if (profileResult.status === "fulfilled") {
        setProfile(profileResult.value);
      } else if (profileResult.reason instanceof ApiError && profileResult.reason.status !== 404) {
        setError(String(profileResult.reason.message));
      } else {
        setProfile(null);
      }

      if (learningResult.status === "fulfilled") {
        setLearning(learningResult.value);
      } else {
        setLearning(null);
      }
      setLoading(false);
    });
  }, [accountId]);

  if (loading) return <Loading />;

  const profileFields = [
    { label: "最佳栏目", value: profile?.best_category },
    { label: "最佳画面", value: profile?.best_scene },
    { label: "最佳时长", value: profile?.best_duration },
    { label: "最佳发布时间", value: profile?.best_publish_time },
    { label: "最佳 Hook", value: profile?.best_hook },
    { label: "最佳 CTA", value: profile?.best_cta },
    { label: "最佳知识来源", value: profile?.best_knowledge_source },
    { label: "账号类型", value: profile?.account_type },
  ];

  return (
    <div className="page">
      <header className="page-header">
        <h1>账号画像</h1>
        <p className="page-sub">
          {currentAccount?.name} · {currentAccount?.platform}
        </p>
      </header>

      {error && <ErrorMessage message={error} />}

      {!profile ? (
        <Card title="暂无画像">
          <p>账号尚无学习数据。请先导入历史视频并等待 Brain Learning 生成报告。</p>
        </Card>
      ) : (
        <div className="grid-2">
          <Card title="核心画像">
            <div className="profile-grid">
              {profileFields.map((f) => (
                <div key={f.label} className="profile-item">
                  <span className="profile-label">{f.label}</span>
                  <span className="profile-value">{f.value ?? "—"}</span>
                </div>
              ))}
            </div>
            <p className="meta-text">最近更新：{new Date(profile.updated_at).toLocaleString("zh-CN")}</p>
          </Card>

          {learning && (
            <Card title="最新学习摘要">
              <p className="report-text">{learning.summary}</p>
              <div className="report-section">
                <strong>优势</strong>
                <p>{learning.strength}</p>
              </div>
              <div className="report-section">
                <strong>弱项</strong>
                <p>{learning.weakness}</p>
              </div>
              <p className="meta-text">
                样本 {learning.sample_size} 条 · {learning.learning_date}
                {learning.prompt_version && ` · Prompt ${learning.prompt_version}`}
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
