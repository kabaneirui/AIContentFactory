import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { TrendTopic, TrendTopicCreate } from "../api/types";
import {
  Card,
  ConfirmDialog,
  ErrorMessage,
  FormField,
  Loading,
  Modal,
} from "../components/ui";

type FormMode = "create" | "edit" | null;

const emptyForm = (): TrendTopicCreate => ({
  topic: "",
  category: "",
  heat_score: 50,
  source: "manual",
  season: "",
  festival: "",
});

export function TrendsPage() {
  const [items, setItems] = useState<TrendTopic[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [seasonFilter, setSeasonFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const [formMode, setFormMode] = useState<FormMode>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TrendTopicCreate>(emptyForm());
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const loadTrends = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listTrends({
        season: seasonFilter || undefined,
        category: categoryFilter || undefined,
        limit: 100,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [seasonFilter, categoryFilter]);

  useEffect(() => {
    loadTrends();
  }, [loadTrends]);

  const openCreate = () => {
    setForm(emptyForm());
    setEditingId(null);
    setFormError("");
    setFormMode("create");
  };

  const openEdit = (item: TrendTopic) => {
    setForm({
      topic: item.topic,
      category: item.category ?? "",
      heat_score: item.heat_score,
      source: item.source,
      season: item.season ?? "",
      festival: item.festival ?? "",
      trend_date: item.trend_date,
    });
    setEditingId(item.id);
    setFormError("");
    setFormMode("edit");
  };

  const closeForm = () => {
    if (submitting) return;
    setFormMode(null);
    setFormError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.topic.trim()) {
      setFormError("请输入热点话题");
      return;
    }

    setSubmitting(true);
    setFormError("");
    try {
      const payload: TrendTopicCreate = {
        topic: form.topic.trim(),
        heat_score: form.heat_score ?? 50,
        source: form.source?.trim() || "manual",
      };
      if (form.category?.trim()) payload.category = form.category.trim();
      if (form.season?.trim()) payload.season = form.season.trim();
      if (form.festival?.trim()) payload.festival = form.festival.trim();
      if (form.trend_date) payload.trend_date = form.trend_date;

      if (formMode === "create") {
        await api.createTrend(payload);
        setMessage("热点已创建");
      } else if (formMode === "edit" && editingId != null) {
        await api.updateTrend(editingId, payload);
        setMessage("热点已更新");
      }
      setFormMode(null);
      await loadTrends();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (deleteId == null) return;
    setDeleting(true);
    try {
      await api.deleteTrend(deleteId);
      setMessage("热点已删除");
      setDeleteId(null);
      await loadTrends();
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "删除失败");
    } finally {
      setDeleting(false);
    }
  };

  const handleCsvUpload = async (file: File) => {
    setImporting(true);
    setError("");
    setMessage("");
    try {
      const result = await api.importTrendsCsv(file);
      setMessage(`导入完成：成功 ${result.imported} 条，跳过 ${result.skipped} 条`);
      await loadTrends();
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "导入失败");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>热点管理</h1>
        <p className="page-sub">全网热点录入 · 共 {total} 条 · 供决策中心 30% 权重使用</p>
      </header>

      <div className="toolbar">
        <input
          placeholder="筛选节气"
          value={seasonFilter}
          onChange={(e) => setSeasonFilter(e.target.value)}
        />
        <input
          placeholder="筛选分类"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        />
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          + 新建热点
        </button>
        <button
          type="button"
          className="btn"
          disabled={importing}
          onClick={() => fileRef.current?.click()}
        >
          {importing ? "导入中…" : "CSV 导入"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleCsvUpload(file);
          }}
        />
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <ErrorMessage message={error} />}

      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <Card title="暂无热点">
          <p>点击「新建热点」录入，或上传 CSV 批量导入。</p>
        </Card>
      ) : (
        <div className="video-table">
          <table>
            <thead>
              <tr>
                <th>话题</th>
                <th>分类</th>
                <th>热度</th>
                <th>节气</th>
                <th>节日</th>
                <th>趋势</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.topic}</td>
                  <td>{item.category ?? "—"}</td>
                  <td>{item.heat_score.toFixed(0)}</td>
                  <td>{item.season ?? "—"}</td>
                  <td>{item.festival ?? "—"}</td>
                  <td>{item.trend_direction ?? "—"}</td>
                  <td className="table-actions">
                    <button type="button" className="btn btn-sm" onClick={() => openEdit(item)}>
                      编辑
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      onClick={() => setDeleteId(item.id)}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={formMode !== null}
        title={formMode === "create" ? "新建热点" : "编辑热点"}
        onClose={closeForm}
        footer={
          <>
            <button type="button" className="btn" onClick={closeForm} disabled={submitting}>
              取消
            </button>
            <button
              type="submit"
              form="trend-form"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? "保存中…" : "保存"}
            </button>
          </>
        }
      >
        <form id="trend-form" className="form-stack" onSubmit={handleSubmit}>
          {formError && <ErrorMessage message={formError} />}
          <FormField label="话题 *" htmlFor="trend-topic">
            <input
              id="trend-topic"
              value={form.topic}
              onChange={(e) => setForm({ ...form, topic: e.target.value })}
              placeholder="例如：夏季养心"
              required
            />
          </FormField>
          <div className="form-row">
            <FormField label="分类" htmlFor="trend-category">
              <input
                id="trend-category"
                value={form.category ?? ""}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                placeholder="养生"
              />
            </FormField>
            <FormField label="热度分" htmlFor="trend-heat">
              <input
                id="trend-heat"
                type="number"
                min="0"
                step="1"
                value={form.heat_score ?? 50}
                onChange={(e) => setForm({ ...form, heat_score: Number(e.target.value) })}
              />
            </FormField>
          </div>
          <div className="form-row">
            <FormField label="节气" htmlFor="trend-season">
              <input
                id="trend-season"
                value={form.season ?? ""}
                onChange={(e) => setForm({ ...form, season: e.target.value })}
                placeholder="夏至"
              />
            </FormField>
            <FormField label="节日" htmlFor="trend-festival">
              <input
                id="trend-festival"
                value={form.festival ?? ""}
                onChange={(e) => setForm({ ...form, festival: e.target.value })}
                placeholder="端午节"
              />
            </FormField>
          </div>
          <FormField label="来源" htmlFor="trend-source">
            <input
              id="trend-source"
              value={form.source ?? "manual"}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
            />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteId !== null}
        title="删除热点"
        message="确定删除此热点？此操作不可恢复。"
        confirmLabel="删除"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => {
          if (!deleting) setDeleteId(null);
        }}
      />
    </div>
  );
}
