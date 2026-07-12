import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { VideoImportResult } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage } from "../components/ui";

export function ImportPage() {
  const { accountId, currentAccount } = useAccount();
  const fileRef = useRef<HTMLInputElement>(null);
  const [jsonText, setJsonText] = useState("");
  const [result, setResult] = useState<VideoImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCsvUpload = async (file: File) => {
    if (!accountId) {
      setError("请先在侧边栏选择或创建账号");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await api.importVideosCsv(accountId, file);
      setResult(data);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "导入失败");
    } finally {
      setLoading(false);
    }
  };

  const handleJsonImport = async () => {
    if (!accountId) {
      setError("请先在侧边栏选择或创建账号");
      return;
    }
    if (!jsonText.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const parsed = JSON.parse(jsonText);
      const videos = Array.isArray(parsed) ? parsed : parsed.videos;
      if (!Array.isArray(videos)) {
        throw new Error("JSON 格式应为数组或 { videos: [...] }");
      }
      const data = await api.importVideosJson(accountId, videos);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "导入失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>数据导入</h1>
        <p className="page-sub">
          批量导入历史视频数据（CSV / JSON）
          {currentAccount && (
            <>
              {" "}
              · 当前账号：<strong>{currentAccount.name}</strong>（ID: {accountId}）
            </>
          )}
        </p>
      </header>

      <div className="grid-2">
        <Card title="CSV 上传">
          <p className="hint">
            支持 UTF-8 编码 CSV，字段参考 backend/docs/video_import_template.md
          </p>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleCsvUpload(file);
            }}
            disabled={loading}
          />
        </Card>

        <Card title="JSON 导入">
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={8}
            placeholder={'[{"title": "视频标题", "views": 500, "template": "口诀", ...}]'}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={handleJsonImport}
            disabled={loading || !jsonText.trim()}
          >
            {loading ? "导入中…" : "导入 JSON"}
          </button>
        </Card>
      </div>

      {error && <ErrorMessage message={error} />}

      {result && (
        <Card title="导入结果">
          <div className="import-result">
            <span className="result-ok">成功 {result.imported} 条</span>
            <span>跳过 {result.skipped} 条</span>
            {result.errors.length > 0 && (
              <span className="result-err">错误 {result.errors.length} 条</span>
            )}
          </div>
          {result.imported > 0 && accountId && (
            <p className="hint">
              已写入账号 ID {accountId}。
              {result.video_ids.length > 0 && (
                <> 视频 ID：{result.video_ids.join(", ")}。</>
              )}
              {" "}
              <Link to="/videos" className="link">
                前往视频记忆查看
              </Link>
              （请确认侧边栏仍是同一账号，状态筛选选「全部状态」）
            </p>
          )}
          {result.errors.length > 0 && (
            <ul className="error-list">
              {result.errors.map((err, i) => (
                <li key={i}>
                  行 {err.row}: {err.message}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </div>
  );
}
