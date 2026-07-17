import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAccount } from "../context/AccountContext";
import { ConfirmDialog, ErrorMessage, FormField, Loading, Modal } from "./ui";

const navItems = [
  { to: "/", label: "账号画像", end: true },
  { to: "/decision", label: "创作工作流" },
  { to: "/videos", label: "视频记忆" },
  { to: "/trends", label: "热点管理" },
  { to: "/learning", label: "学习报告" },
  { to: "/predict", label: "预测拦截" },
  { to: "/prompts", label: "Prompt 管理" },
  { to: "/import", label: "数据导入" },
];

const PLATFORMS = [
  { value: "wechat_channels", label: "视频号" },
  { value: "douyin", label: "抖音" },
  { value: "kuaishou", label: "快手" },
  { value: "bilibili", label: "B站" },
];

type ModalMode = "create" | "edit" | null;

export function Layout() {
  const { accounts, accountId, setAccountId, currentAccount, loading, refreshAccounts } =
    useAccount();

  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [platform, setPlatform] = useState(PLATFORMS[0].value);
  const [predictThreshold, setPredictThreshold] = useState("");
  const [autoEvolve, setAutoEvolve] = useState(false);

  const openCreate = () => {
    setName("");
    setPlatform(PLATFORMS[0].value);
    setPredictThreshold("");
    setAutoEvolve(false);
    setError("");
    setModalMode("create");
  };

  const openEdit = () => {
    if (!currentAccount) return;
    setName(currentAccount.name);
    setPlatform(currentAccount.platform);
    setPredictThreshold(
      currentAccount.predict_threshold != null
        ? String(currentAccount.predict_threshold)
        : "",
    );
    setAutoEvolve(currentAccount.auto_evolve);
    setError("");
    setModalMode("edit");
  };

  const closeModal = () => {
    if (submitting) return;
    setModalMode(null);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("请输入账号名称");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      if (modalMode === "create") {
        const created = await api.createAccount({ name: name.trim(), platform });
        await refreshAccounts();
        setAccountId(created.id);
      } else if (modalMode === "edit" && currentAccount) {
        const payload: {
          name: string;
          predict_threshold?: number | null;
          auto_evolve: boolean;
        } = {
          name: name.trim(),
          auto_evolve: autoEvolve,
        };
        if (predictThreshold.trim()) {
          payload.predict_threshold = Number(predictThreshold);
        } else {
          payload.predict_threshold = null;
        }
        await api.updateAccount(currentAccount.id, payload);
        await refreshAccounts();
      }
      setModalMode(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!currentAccount) return;
    setDeleting(true);
    setError("");
    try {
      await api.deleteAccount(currentAccount.id);
      setDeleteOpen(false);
      await refreshAccounts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败，请重试");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <Loading text="初始化账号…" />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">🧠</span>
          <div>
            <div className="brand-name">AI Memory</div>
            <div className="brand-sub">个人内容大脑</div>
          </div>
        </div>

        <div className="account-picker">
          <label htmlFor="account-select">当前账号</label>
          <select
            id="account-select"
            value={accountId ?? ""}
            onChange={(e) => setAccountId(Number(e.target.value))}
          >
            {accounts.length === 0 && <option value="">暂无账号</option>}
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.platform})
              </option>
            ))}
          </select>
          {currentAccount && (
            <div className="account-meta">ID: {currentAccount.id}</div>
          )}
          <div className="account-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
              + 创建
            </button>
            <button
              type="button"
              className="btn btn-sm"
              onClick={openEdit}
              disabled={!currentAccount}
            >
              编辑
            </button>
            <button
              type="button"
              className="btn btn-sm btn-danger"
              onClick={() => {
                setError("");
                setDeleteOpen(true);
              }}
              disabled={!currentAccount}
            >
              删除
            </button>
          </div>
        </div>

        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        {!accountId ? (
          <div className="page">
            <h1>欢迎使用 AI Memory</h1>
            <p>请先在侧边栏创建或选择账号。</p>
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              + 创建第一个账号
            </button>
          </div>
        ) : (
          <Outlet />
        )}
      </main>

      <Modal
        open={modalMode !== null}
        title={modalMode === "create" ? "创建账号" : "编辑账号"}
        onClose={closeModal}
        footer={
          <>
            <button type="button" className="btn" onClick={closeModal} disabled={submitting}>
              取消
            </button>
            <button
              type="submit"
              form="account-form"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? "保存中…" : "保存"}
            </button>
          </>
        }
      >
        <form id="account-form" className="form-stack" onSubmit={handleSubmit}>
          {error && <ErrorMessage message={error} />}
          <FormField label="账号名称" htmlFor="account-name">
            <input
              id="account-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：美食探店号"
              required
            />
          </FormField>
          {modalMode === "create" && (
            <FormField label="平台" htmlFor="account-platform">
              <select
                id="account-platform"
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
              >
                {PLATFORMS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </FormField>
          )}
          {modalMode === "edit" && (
            <>
              <FormField label="预测拦截阈值（播放量）" htmlFor="predict-threshold">
                <input
                  id="predict-threshold"
                  type="number"
                  min="0"
                  value={predictThreshold}
                  onChange={(e) => setPredictThreshold(e.target.value)}
                  placeholder="留空则使用近 30 条 P25"
                />
              </FormField>
              <FormField label="自动激活 Prompt 进化" htmlFor="auto-evolve">
                <label className="checkbox-label">
                  <input
                    id="auto-evolve"
                    type="checkbox"
                    checked={autoEvolve}
                    onChange={(e) => setAutoEvolve(e.target.checked)}
                  />
                  <span>Prompt 进化后自动激活（默认需人工审核）</span>
                </label>
              </FormField>
            </>
          )}
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteOpen}
        title="删除账号"
        message={
          currentAccount
            ? `确定删除账号「${currentAccount.name}」？此操作不可恢复，关联的视频与画像数据将一并删除。`
            : ""
        }
        confirmLabel="删除"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => {
          if (!deleting) setDeleteOpen(false);
        }}
      />
    </div>
  );
}
