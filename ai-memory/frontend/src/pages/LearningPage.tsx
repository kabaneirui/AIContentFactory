import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { BrainLearning } from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, Loading } from "../components/ui";

export function LearningPage() {
  const { accountId } = useAccount();
  const [learning, setLearning] = useState<BrainLearning | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!accountId) return;
    api
      .getLatestLearning(accountId)
      .then(setLearning)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setLearning(null);
        } else {
          setError(e instanceof ApiError ? String(e.message) : "加载失败");
        }
      })
      .finally(() => setLoading(false));
  }, [accountId]);

  if (loading) return <Loading />;

  return (
    <div className="page">
      <header className="page-header">
        <h1>学习报告</h1>
        <p className="page-sub">Brain Learning 每日自动学习 + 策略优化建议</p>
      </header>

      {error && <ErrorMessage message={error} />}

      {!learning ? (
        <Card title="暂无报告">
          <p>账号尚无学习报告。请确保有已打标的视频，并等待每日凌晨 02:00 自动学习任务运行。</p>
        </Card>
      ) : (
        <>
          <Card title={`${learning.learning_date} 学习报告`}>
            <div className="report-meta">
              <span>样本量 {learning.sample_size}</span>
              {learning.prompt_version && <span>Prompt {learning.prompt_version}</span>}
            </div>
          </Card>

          <div className="grid-2">
            {[
              { title: "总结", content: learning.summary },
              { title: "优势", content: learning.strength },
              { title: "弱项", content: learning.weakness },
              { title: "趋势", content: learning.trend },
              { title: "建议", content: learning.suggestion },
              { title: "策略优化", content: learning.optimization },
            ].map((section) => (
              <Card key={section.title} title={section.title}>
                <p className="report-text">{section.content}</p>
              </Card>
            ))}
          </div>

          {learning.stats_snapshot && (
            <Card title="统计快照">
              <pre className="stats-json">
                {JSON.stringify(learning.stats_snapshot, null, 2)}
              </pre>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
