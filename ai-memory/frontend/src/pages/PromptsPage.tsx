import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { PromptVersion } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, FormField, Loading, Modal, Stars } from "../components/ui";

export function PromptsPage() {
  const { accountId } = useAccount();
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [activeVersion, setActiveVersion] = useState<string | null>(null);
  const [selected, setSelected] = useState<PromptVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [promptContent, setPromptContent] = useState("");
  const [changeLog, setChangeLog] = useState("");
  const [activateOnCreate, setActivateOnCreate] = useState(false);
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);

  const loadPrompts = useCallback(async () => {
    if (!accountId) return;
    setLoading(true);
    try {
      const data = await api.listPrompts(accountId);
      setVersions(data.items);
      setActiveVersion(data.active_version);
      if (data.items.length > 0) {
        setSelected((prev) => {
          if (prev && data.items.some((v) => v.id === prev.id)) return prev;
          const active = data.items.find((v) => v.is_active);
          return active ?? data.items[data.items.length - 1];
        });
      }
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handleEvolve = async (force = false) => {
    if (!accountId) return;
    setActionLoading(true);
    setMessage("");
    setError("");
    try {
      const result = await api.evolvePrompt(accountId, force);
      if (result.evolved) {
        setMessage(
          result.pending_review
            ? `已生成 ${result.new_version?.version}，待人工审核激活`
            : `已进化并激活 ${result.new_version?.version}`,
        );
        await loadPrompts();
      } else {
        setMessage(result.reason);
      }
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "进化失败");
    } finally {
      setActionLoading(false);
    }
  };

  const handleActivate = async (versionId: number) => {
    if (!accountId) return;
    setActionLoading(true);
    setError("");
    try {
      const result = await api.activatePrompt(accountId, versionId);
      setMessage(`已激活 ${result.activated_version}`);
      await loadPrompts();
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "激活失败");
    } finally {
      setActionLoading(false);
    }
  };

  const openCreate = () => {
    setPromptContent("");
    setChangeLog("");
    setActivateOnCreate(false);
    setCreateError("");
    setCreateOpen(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accountId || promptContent.trim().length < 10) {
      setCreateError("Prompt 内容至少 10 个字符");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      await api.createPromptVersion(accountId, {
        prompt_content: promptContent.trim(),
        change_log: changeLog.trim() || undefined,
        activate: activateOnCreate,
      });
      setMessage(activateOnCreate ? "新版本已创建并激活" : "新版本已创建，待审核激活");
      setCreateOpen(false);
      await loadPrompts();
    } catch (e) {
      setCreateError(e instanceof ApiError ? String(e.message) : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Prompt 管理</h1>
        <p className="page-sub">
          版本追踪与进化 · 当前活跃：{activeVersion ?? "无"}
        </p>
      </header>

      <div className="toolbar">
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          + 创建版本
        </button>
        <button
          className="btn btn-primary"
          onClick={() => handleEvolve(false)}
          disabled={actionLoading}
        >
          检查进化
        </button>
        <button
          className="btn"
          onClick={() => handleEvolve(true)}
          disabled={actionLoading}
        >
          强制进化
        </button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <ErrorMessage message={error} />}

      <div className="prompt-layout">
        <Card title="版本列表" className="prompt-list-card">
          <div className="version-list">
            {versions.map((v) => (
              <button
                key={v.id}
                className={`version-item ${selected?.id === v.id ? "selected" : ""} ${v.is_active ? "active" : ""}`}
                onClick={() => setSelected(v)}
              >
                <div className="version-header">
                  <strong>{v.version}</strong>
                  {v.is_active && <span className="active-badge">活跃</span>}
                </div>
                <div className="version-stats">
                  <Stars level={v.recommend_score} />
                  <span>{v.video_count} 条</span>
                  <span>均播 {v.avg_view.toFixed(0)}</span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        {selected && (
          <Card title={`${selected.version} 详情`} className="prompt-detail-card">
            <div className="detail-metrics">
              <span>样本 {selected.video_count}</span>
              <span>均播 {selected.avg_view.toFixed(0)}</span>
              <span>完播 {(selected.avg_finish_rate * 100).toFixed(1)}%</span>
              <Stars level={selected.recommend_score} />
            </div>

            {selected.change_log && (
              <div className="report-section">
                <strong>变更说明</strong>
                <p>{selected.change_log}</p>
              </div>
            )}

            <div className="report-section">
              <strong>Prompt 全文</strong>
              <pre className="prompt-content">{selected.prompt_content}</pre>
            </div>

            {!selected.is_active && (
              <button
                className="btn btn-primary"
                onClick={() => handleActivate(selected.id)}
                disabled={actionLoading}
              >
                激活此版本
              </button>
            )}
          </Card>
        )}
      </div>

      <Modal
        open={createOpen}
        title="创建 Prompt 版本"
        onClose={() => {
          if (!creating) setCreateOpen(false);
        }}
        footer={
          <>
            <button
              type="button"
              className="btn"
              onClick={() => setCreateOpen(false)}
              disabled={creating}
            >
              取消
            </button>
            <button
              type="submit"
              form="prompt-create-form"
              className="btn btn-primary"
              disabled={creating}
            >
              {creating ? "创建中…" : "创建"}
            </button>
          </>
        }
      >
        <form id="prompt-create-form" className="form-stack" onSubmit={handleCreate}>
          {createError && <ErrorMessage message={createError} />}
          <FormField label="Prompt 内容 *" htmlFor="prompt-content">
            <textarea
              id="prompt-content"
              rows={10}
              value={promptContent}
              onChange={(e) => setPromptContent(e.target.value)}
              placeholder="输入完整 Prompt 模板…"
              required
            />
          </FormField>
          <FormField label="变更说明" htmlFor="prompt-changelog">
            <input
              id="prompt-changelog"
              value={changeLog}
              onChange={(e) => setChangeLog(e.target.value)}
              placeholder="例如：强化前 3 秒钩子"
            />
          </FormField>
          <FormField label="立即激活" htmlFor="prompt-activate">
            <label className="checkbox-label">
              <input
                id="prompt-activate"
                type="checkbox"
                checked={activateOnCreate}
                onChange={(e) => setActivateOnCreate(e.target.checked)}
              />
              <span>创建后立即设为活跃版本（默认需人工审核）</span>
            </label>
          </FormField>
        </form>
      </Modal>
    </div>
  );
}
