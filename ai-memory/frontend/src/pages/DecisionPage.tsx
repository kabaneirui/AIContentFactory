import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type {
  DecisionRecommendation,
  DecideTodayResponse,
  GenerateScriptResponse,
  PipelinePublishResponse,
  PredictApiResponse,
} from "../api/types";
import { useAccount } from "../context/AccountContext";
import { Card, ErrorMessage, Loading, Stars } from "../components/ui";

type Step = 1 | 2 | 3 | 4;

const STEPS: { id: Step; label: string }[] = [
  { id: 1, label: "选题决策" },
  { id: 2, label: "生成文案" },
  { id: 3, label: "预测评估" },
  { id: 4, label: "发布入库" },
];

interface DraftContent {
  title: string;
  script: string;
  hook: string;
  template: string;
  knowledge_source: string;
  scene_style: string;
  duration: number;
  cta: string;
  season: string;
  festival: string;
  matched_trend: string;
  suggested_publish_time: string;
  prompt_version: string | null;
  generated_by: string | null;
}

function draftFromRecommendation(
  rec: DecisionRecommendation,
  season: string,
  festival: string,
): DraftContent {
  return {
    title: rec.title,
    script: "",
    hook: rec.hook ?? "",
    template: rec.template ?? "",
    knowledge_source: rec.knowledge_source ?? "",
    scene_style: rec.scene_style ?? "",
    duration: rec.duration ?? 32,
    cta: rec.cta ?? "",
    season,
    festival,
    matched_trend: rec.matched_trend ?? "",
    suggested_publish_time: rec.suggested_publish_time,
    prompt_version: null,
    generated_by: null,
  };
}

function draftFromScript(res: GenerateScriptResponse, prev: DraftContent): DraftContent {
  return {
    ...prev,
    title: res.title,
    script: res.script,
    hook: res.hook ?? prev.hook,
    template: res.template ?? prev.template,
    knowledge_source: res.knowledge_source ?? prev.knowledge_source,
    scene_style: res.scene_style ?? prev.scene_style,
    duration: res.duration ?? prev.duration,
    cta: res.cta ?? prev.cta,
    season: res.season ?? prev.season,
    festival: res.festival ?? prev.festival,
    matched_trend: res.matched_trend ?? prev.matched_trend,
    prompt_version: res.prompt_version,
    generated_by: res.generated_by,
  };
}

export function DecisionPage() {
  const { accountId } = useAccount();
  const [step, setStep] = useState<Step>(1);
  const [season, setSeason] = useState("");
  const [festival, setFestival] = useState("");
  const [decideResult, setDecideResult] = useState<DecideTodayResponse | null>(null);
  const [selectedRank, setSelectedRank] = useState<number | null>(null);
  const [draft, setDraft] = useState<DraftContent | null>(null);
  const [predictResult, setPredictResult] = useState<PredictApiResponse | null>(null);
  const [publishResult, setPublishResult] = useState<PipelinePublishResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedRec =
    decideResult?.recommendations.find((r) => r.rank === selectedRank) ?? null;

  const resetFromStep = (from: Step) => {
    if (from <= 1) {
      setDecideResult(null);
      setSelectedRank(null);
    }
    if (from <= 2) {
      setDraft(null);
    }
    if (from <= 3) {
      setPredictResult(null);
    }
    if (from <= 4) {
      setPublishResult(null);
    }
  };

  const handleDecide = async () => {
    if (!accountId) return;
    setLoading(true);
    setError("");
    resetFromStep(1);
    setStep(1);
    try {
      const data = await api.decideToday(accountId, {
        season: season || undefined,
        festival: festival || undefined,
        count: 5,
      });
      setDecideResult(data);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "决策失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRecommendation = (rec: DecisionRecommendation) => {
    setSelectedRank(rec.rank);
    setDraft(draftFromRecommendation(rec, season, festival));
    setPredictResult(null);
    setPublishResult(null);
  };

  const handleGenerateScript = async () => {
    if (!accountId || !selectedRec) return;
    setLoading(true);
    setError("");
    setPredictResult(null);
    setPublishResult(null);
    try {
      const data = await api.generateScript(accountId, {
        title: selectedRec.title,
        hook: selectedRec.hook ?? undefined,
        template: selectedRec.template ?? undefined,
        knowledge_source: selectedRec.knowledge_source ?? undefined,
        scene_style: selectedRec.scene_style ?? undefined,
        duration: selectedRec.duration ?? undefined,
        cta: selectedRec.cta ?? undefined,
        season: season || undefined,
        festival: festival || undefined,
        matched_trend: selectedRec.matched_trend ?? undefined,
        reasons: selectedRec.reasons,
      });
      setDraft((prev) =>
        draftFromScript(data, prev ?? draftFromRecommendation(selectedRec, season, festival)),
      );
      setStep(2);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "文案生成失败");
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async () => {
    if (!accountId || !draft?.title.trim()) return;
    setLoading(true);
    setError("");
    setPublishResult(null);
    try {
      const data = await api.predict(accountId, {
        title: draft.title.trim(),
        script: draft.script || undefined,
        hook: draft.hook || undefined,
        template: draft.template || undefined,
        knowledge_source: draft.knowledge_source || undefined,
        scene_style: draft.scene_style || undefined,
        duration: draft.duration || undefined,
        cta: draft.cta || undefined,
      });
      setPredictResult(data);
      setStep(3);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "预测失败");
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async (skipPredictionCheck = false) => {
    if (!accountId || !draft?.title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.pipelinePublish(accountId, {
        title: draft.title.trim(),
        script: draft.script || undefined,
        hook: draft.hook || undefined,
        template: draft.template || undefined,
        knowledge_source: draft.knowledge_source || undefined,
        scene_style: draft.scene_style || undefined,
        duration: draft.duration || undefined,
        cta: draft.cta || undefined,
        season: draft.season || undefined,
        festival: draft.festival || undefined,
        category: draft.template || undefined,
        require_prediction_pass: !skipPredictionCheck && predictResult !== null,
        tag_inline: true,
      });
      if (!data.success) {
        throw new Error(data.message ?? "发布失败");
      }
      setPublishResult(data);
      setStep(4);
    } catch (e) {
      setError(e instanceof Error ? e.message : "发布失败");
    } finally {
      setLoading(false);
    }
  };

  const handleAutoWorkflow = async () => {
    if (!accountId || !selectedRec) return;
    setLoading(true);
    setError("");
    resetFromStep(2);
    try {
      const scriptRes = await api.generateScript(accountId, {
        title: selectedRec.title,
        hook: selectedRec.hook ?? undefined,
        template: selectedRec.template ?? undefined,
        knowledge_source: selectedRec.knowledge_source ?? undefined,
        scene_style: selectedRec.scene_style ?? undefined,
        duration: selectedRec.duration ?? undefined,
        cta: selectedRec.cta ?? undefined,
        season: season || undefined,
        festival: festival || undefined,
        matched_trend: selectedRec.matched_trend ?? undefined,
        reasons: selectedRec.reasons,
      });
      const nextDraft = draftFromScript(
        scriptRes,
        draftFromRecommendation(selectedRec, season, festival),
      );
      setDraft(nextDraft);

      const predictRes = await api.predict(accountId, {
        title: nextDraft.title.trim(),
        script: nextDraft.script || undefined,
        hook: nextDraft.hook || undefined,
        template: nextDraft.template || undefined,
        knowledge_source: nextDraft.knowledge_source || undefined,
        scene_style: nextDraft.scene_style || undefined,
        duration: nextDraft.duration || undefined,
        cta: nextDraft.cta || undefined,
      });
      setPredictResult(predictRes);

      if (predictRes.pass) {
        const pub = await api.pipelinePublish(accountId, {
          title: nextDraft.title.trim(),
          script: nextDraft.script || undefined,
          hook: nextDraft.hook || undefined,
          template: nextDraft.template || undefined,
          knowledge_source: nextDraft.knowledge_source || undefined,
          scene_style: nextDraft.scene_style || undefined,
          duration: nextDraft.duration || undefined,
          cta: nextDraft.cta || undefined,
          season: nextDraft.season || undefined,
          festival: nextDraft.festival || undefined,
          category: nextDraft.template || undefined,
          require_prediction_pass: true,
          tag_inline: true,
        });
        if (!pub.success) {
          throw new Error(pub.message ?? "发布失败");
        }
        setPublishResult(pub);
        setStep(4);
      } else {
        setStep(3);
      }
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : e instanceof Error ? e.message : "工作流失败");
      if (draft) setStep(2);
      else if (selectedRec) setStep(1);
    } finally {
      setLoading(false);
    }
  };

  const updateDraft = (patch: Partial<DraftContent>) => {
    setDraft((prev) => (prev ? { ...prev, ...patch } : prev));
    setPredictResult(null);
    setPublishResult(null);
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>创作工作流</h1>
        <p className="page-sub">决策 → 生成文案 → 预测 → 发布，全程可介入调整</p>
      </header>

      <nav className="workflow-steps" aria-label="创作步骤">
        {STEPS.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`workflow-step ${step === s.id ? "active" : ""} ${step > s.id ? "done" : ""}`}
            onClick={() => step >= s.id && setStep(s.id)}
            disabled={step < s.id}
          >
            <span className="workflow-step-num">{s.id}</span>
            {s.label}
          </button>
        ))}
      </nav>

      {error && <ErrorMessage message={error} />}
      {loading && <Loading text="处理中…" />}

      {step === 1 && (
        <>
          <Card title="① 选题决策">
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
            <div className="form-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleDecide}
                disabled={loading || !accountId}
              >
                获取今日推荐
              </button>
            </div>
          </Card>

          {decideResult && (
            <div className="recommendations">
              <p className="meta-text">
                生成于 {new Date(decideResult.generated_at).toLocaleString("zh-CN")}
                ，请选择一条进入下一步
              </p>
              {decideResult.recommendations.map((rec) => (
                <Card
                  key={rec.rank}
                  className={`rec-card selectable ${selectedRank === rec.rank ? "selected" : ""}`}
                >
                  <label className="rec-select-label">
                    <input
                      type="radio"
                      name="recommendation"
                      checked={selectedRank === rec.rank}
                      onChange={() => handleSelectRecommendation(rec)}
                    />
                    <div className="rec-header">
                      <span className="rec-rank">#{rec.rank}</span>
                      <h3>{rec.title}</h3>
                      <Stars level={rec.predict_level} />
                    </div>
                  </label>
                  <div className="rec-stats">
                    <span>预计播放 {rec.predict_view.toLocaleString()}</span>
                    <span>建议 {rec.suggested_publish_time}</span>
                    <span>综合分 {(rec.combined_score * 100).toFixed(0)}%</span>
                  </div>
                  {(rec.template || rec.hook || rec.matched_trend) && (
                    <div className="rec-tags">
                      {rec.template && <span className="tag">{rec.template}</span>}
                      {rec.hook && <span className="tag">{rec.hook}</span>}
                      {rec.matched_trend && (
                        <span className="tag tag-hot">{rec.matched_trend}</span>
                      )}
                    </div>
                  )}
                  <ul className="reason-list">
                    {rec.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </Card>
              ))}
              <div className="form-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!selectedRec || loading}
                  onClick={handleGenerateScript}
                >
                  下一步：生成文案
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={!selectedRec || loading}
                  onClick={handleAutoWorkflow}
                >
                  一键完成（生成→预测→发布）
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {step === 2 && draft && (
        <Card title="② 生成 / 编辑文案">
          {draft.generated_by && (
            <p className="hint">
              文案来源：{draft.generated_by === "llm" ? "AI 生成" : "规则模板"}
              {draft.prompt_version && ` · Prompt ${draft.prompt_version}`}
            </p>
          )}
          <div className="form-stack">
            <label>
              标题
              <input
                value={draft.title}
                onChange={(e) => updateDraft({ title: e.target.value })}
              />
            </label>
            <label>
              口播稿
              <textarea
                rows={12}
                value={draft.script}
                onChange={(e) => updateDraft({ script: e.target.value })}
                placeholder="点击「重新生成」或手动撰写口播稿"
              />
            </label>
            <div className="form-row">
              <label>
                Hook
                <input
                  value={draft.hook}
                  onChange={(e) => updateDraft({ hook: e.target.value })}
                />
              </label>
              <label>
                模板
                <input
                  value={draft.template}
                  onChange={(e) => updateDraft({ template: e.target.value })}
                />
              </label>
            </div>
          </div>
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => setStep(1)}>
              返回选题
            </button>
            <button
              type="button"
              className="btn"
              disabled={loading || !selectedRec}
              onClick={handleGenerateScript}
            >
              重新生成
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={loading || !draft.title.trim()}
              onClick={handlePredict}
            >
              下一步：预测评估
            </button>
          </div>
        </Card>
      )}

      {step === 3 && draft && (
        <Card title="③ 预测评估">
          {!predictResult ? (
            <p className="hint">点击下方按钮评估这篇文案的预计表现。</p>
          ) : (
            <div className="predict-summary">
              <div className="predict-header">
                <Stars level={predictResult.prediction.predict_level} />
                <span
                  className={
                    predictResult.pass ? "result-ok" : "result-err"
                  }
                >
                  {predictResult.pass ? "建议发布" : "低于阈值，建议修改"}
                </span>
              </div>
              <p>
                预计播放 {predictResult.prediction.predict_view.toLocaleString()} · 完播率{" "}
                {(predictResult.prediction.predict_finish_rate * 100).toFixed(1)}% · 置信度{" "}
                {(predictResult.prediction.confidence * 100).toFixed(0)}%
              </p>
              <ul className="reason-list">
                {predictResult.prediction.reason.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => setStep(2)}>
              返回修改文案
            </button>
            {!predictResult && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loading}
                onClick={handlePredict}
              >
                开始预测
              </button>
            )}
            {predictResult?.pass && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={loading}
                onClick={() => setStep(4)}
              >
                下一步：发布入库
              </button>
            )}
            {predictResult && !predictResult.pass && (
              <>
                <button
                  type="button"
                  className="btn"
                  disabled={loading}
                  onClick={() => handlePublish(true)}
                >
                  仍要发布
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={loading}
                  onClick={() => {
                    setStep(2);
                    handleGenerateScript();
                  }}
                >
                  重新生成文案
                </button>
              </>
            )}
          </div>
        </Card>
      )}

      {step === 4 && publishResult && (
        <Card title="④ 发布完成">
          <p className="result-ok">视频已成功写入 Video Memory</p>
          <ul className="reason-list">
            <li>视频 ID：{publishResult.video_id}</li>
            <li>生命周期：{publishResult.lifecycle_status}</li>
            {publishResult.prompt_version && (
              <li>Prompt 版本：{publishResult.prompt_version}</li>
            )}
            <li>同步任务：{publishResult.sync_tasks_scheduled} 个</li>
            <li>DNA 打标：{publishResult.steps.dna_tagged ? "已完成" : "排队中"}</li>
          </ul>
          <div className="form-actions">
            {publishResult.video_id && (
              <Link to={`/videos/${publishResult.video_id}`} className="btn btn-primary">
                查看视频详情
              </Link>
            )}
            <Link to="/videos" className="btn">
              视频记忆列表
            </Link>
            <button
              type="button"
              className="btn"
              onClick={() => {
                resetFromStep(1);
                setStep(1);
                setSeason("");
                setFestival("");
              }}
            >
              开始新的创作
            </button>
          </div>
        </Card>
      )}

      {step === 4 && !publishResult && draft && (
        <Card title="④ 确认发布">
          <p className="hint">确认将以下内容写入视频记忆并触发 DNA 打标。</p>
          <p>
            <strong>{draft.title}</strong>
          </p>
          <p className="meta-text">{draft.script.slice(0, 200)}…</p>
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => setStep(3)}>
              返回
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={loading}
              onClick={() => handlePublish(false)}
            >
              确认发布
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
