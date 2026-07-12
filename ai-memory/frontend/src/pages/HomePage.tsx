import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AccountProfile, BrainLearning } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, Loading } from "../components/ui";

const LOCKABLE_FIELDS: { key: string; label: string }[] = [
  { key: "best_category", label: "最佳栏目" },
  { key: "best_scene", label: "最佳画面" },
  { key: "best_duration", label: "最佳时长" },
  { key: "best_publish_time", label: "最佳发布时间" },
  { key: "best_hook", label: "最佳 Hook" },
  { key: "best_cta", label: "最佳 CTA" },
  { key: "best_knowledge_source", label: "最佳知识来源" },
];

export function HomePage() {
  const { accountId, currentAccount } = useAccount();
  const [profile, setProfile] = useState<AccountProfile | null>(null);
  const [learning, setLearning] = useState<BrainLearning | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [editingLocks, setEditingLocks] = useState(false);
  const [lockedFields, setLockedFields] = useState<string[]>([]);
  const [savingLocks, setSavingLocks] = useState(false);
  const [lockMessage, setLockMessage] = useState("");
  const [lockError, setLockError] = useState("");

  const loadData = async (id: number) => {
    setLoading(true);
    setError("");
    const [profileResult, learningResult] = await Promise.allSettled([
      api.getProfile(id),
      api.getLatestLearning(id),
    ]);

    if (profileResult.status === "fulfilled") {
      setProfile(profileResult.value);
      setLockedFields(profileResult.value.locked_fields ?? []);
    } else if (
      profileResult.reason instanceof ApiError &&
      profileResult.reason.status !== 404
    ) {
      setError(String(profileResult.reason.message));
      setProfile(null);
    } else {
      setProfile(null);
      setLockedFields([]);
    }

    if (learningResult.status === "fulfilled") {
      setLearning(learningResult.value);
    } else {
      setLearning(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (!accountId) return;
    loadData(accountId);
  }, [accountId]);

  const toggleLockField = (key: string) => {
    setLockedFields((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  };

  const handleSaveLocks = async () => {
    if (!accountId) return;
    setSavingLocks(true);
    setLockError("");
    setLockMessage("");
    try {
      const updated = await api.updateProfile(accountId, {
        locked_fields: lockedFields,
      });
      setProfile(updated);
      setLockedFields(updated.locked_fields ?? []);
      setEditingLocks(false);
      setLockMessage("锁定字段已保存");
    } catch (e) {
      setLockError(e instanceof ApiError ? String(e.message) : "保存失败");
    } finally {
      setSavingLocks(false);
    }
  };

  if (loading) return <Loading />;

  const profileFields = [
    { label: "最佳栏目", value: profile?.best_category, key: "best_category" },
    { label: "最佳画面", value: profile?.best_scene, key: "best_scene" },
    { label: "最佳时长", value: profile?.best_duration, key: "best_duration" },
    {
      label: "最佳发布时间",
      value: profile?.best_publish_time,
      key: "best_publish_time",
    },
    { label: "最佳 Hook", value: profile?.best_hook, key: "best_hook" },
    { label: "最佳 CTA", value: profile?.best_cta, key: "best_cta" },
    {
      label: "最佳知识来源",
      value: profile?.best_knowledge_source,
      key: "best_knowledge_source",
    },
    { label: "账号类型", value: profile?.account_type, key: null },
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
      {lockMessage && <div className="success-banner">{lockMessage}</div>}

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
                  <span className="profile-label">
                    {f.label}
                    {f.key && profile.locked_fields?.includes(f.key) && (
                      <span className="lock-badge" title="已锁定">
                        🔒
                      </span>
                    )}
                  </span>
                  <span className="profile-value">{f.value ?? "—"}</span>
                </div>
              ))}
            </div>
            <p className="meta-text">
              最近更新：{new Date(profile.updated_at).toLocaleString("zh-CN")}
            </p>

            {!editingLocks ? (
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => {
                  setLockedFields(profile.locked_fields ?? []);
                  setLockError("");
                  setEditingLocks(true);
                }}
              >
                编辑锁定字段
              </button>
            ) : (
              <div className="lock-editor">
                <p className="hint">
                  锁定的字段在每日学习刷新画像时不会被自动覆盖。
                </p>
                {lockError && <ErrorMessage message={lockError} />}
                <div className="checkbox-group">
                  {LOCKABLE_FIELDS.map((f) => (
                    <label key={f.key} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={lockedFields.includes(f.key)}
                        onChange={() => toggleLockField(f.key)}
                      />
                      <span>{f.label}</span>
                    </label>
                  ))}
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => setEditingLocks(false)}
                    disabled={savingLocks}
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={handleSaveLocks}
                    disabled={savingLocks}
                  >
                    {savingLocks ? "保存中…" : "保存锁定"}
                  </button>
                </div>
              </div>
            )}
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
