import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Video } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, LifecycleBadge, Loading } from "../components/ui";

export function VideosPage() {
  const { accountId, currentAccount } = useAccount();
  const [videos, setVideos] = useState<Video[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!accountId) return;
    setLoading(true);
    api
      .listVideos(accountId, {
        page,
        page_size: 20,
        lifecycle_status: statusFilter || undefined,
      })
      .then((data) => {
        setVideos(data.items);
        setTotal(data.total);
      })
      .catch((e) => setError(e instanceof ApiError ? String(e.message) : "加载失败"))
      .finally(() => setLoading(false));
  }, [accountId, page, statusFilter]);

  const totalPages = Math.ceil(total / 20) || 1;

  return (
    <div className="page">
      <header className="page-header">
        <h1>视频记忆</h1>
        <p className="page-sub">
          共 {total} 条视频 · 生命周期追踪
          {currentAccount && (
            <>
              {" "}
              · 账号 {currentAccount.name}（ID: {accountId}）
            </>
          )}
        </p>
      </header>

      <div className="toolbar">
        <Link to="/videos/new" className="btn btn-primary">
          + 发布视频
        </Link>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">全部状态</option>
          <option value="created">已创建</option>
          <option value="published">已发布</option>
          <option value="syncing">同步中</option>
          <option value="tagged">已打标</option>
          <option value="learned">已学习</option>
          <option value="archived">已归档</option>
        </select>
      </div>

      {error && <ErrorMessage message={error} />}
      {loading ? (
        <Loading />
      ) : videos.length === 0 ? (
        <Card title="暂无视频">
          <p>请通过数据导入页上传历史视频，或点击「发布视频」录入新内容。</p>
          {statusFilter && (
            <p className="hint">
              当前筛选状态为「{statusFilter}」。历史导入视频多为「同步中」，请改选「全部状态」。
            </p>
          )}
        </Card>
      ) : (
        <>
          <div className="video-table">
            <table>
              <thead>
                <tr>
                  <th>标题</th>
                  <th>状态</th>
                  <th>播放</th>
                  <th>完播率</th>
                  <th>Prompt</th>
                  <th>发布时间</th>
                </tr>
              </thead>
              <tbody>
                {videos.map((v) => (
                  <tr key={v.id}>
                    <td>
                      <Link to={`/videos/${v.id}`} className="link">
                        {v.title}
                      </Link>
                    </td>
                    <td>
                      <LifecycleBadge status={v.lifecycle_status} />
                    </td>
                    <td>{v.performance?.views?.toLocaleString() ?? "—"}</td>
                    <td>
                      {v.performance?.finish_rate != null
                        ? `${(v.performance.finish_rate * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td>{v.prompt ?? "—"}</td>
                    <td>
                      {v.publish_time
                        ? new Date(v.publish_time).toLocaleDateString("zh-CN")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button
              className="btn"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              上一页
            </button>
            <span>
              {page} / {totalPages}
            </span>
            <button
              className="btn"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              下一页
            </button>
          </div>
        </>
      )}
    </div>
  );
}
