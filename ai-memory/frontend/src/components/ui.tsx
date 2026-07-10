import type { ReactNode } from "react";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {title && <h2 className="card-title">{title}</h2>}
      {children}
    </section>
  );
}

export function Stars({ level, max = 5 }: { level: number; max?: number }) {
  return (
    <span className="stars" aria-label={`${level} 星`}>
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className={i < level ? "star filled" : "star"}>
          ★
        </span>
      ))}
    </span>
  );
}

export function Loading({ text = "加载中…" }: { text?: string }) {
  return <div className="loading">{text}</div>;
}

export function ErrorMessage({ message }: { message: string }) {
  return <div className="error-banner">{message}</div>;
}

export function EmptyState({ message }: { message: string }) {
  return <p className="empty-state">{message}</p>;
}

export function Badge({ children, variant = "default" }: { children: ReactNode; variant?: string }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function LifecycleBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    created: "已创建",
    published: "已发布",
    syncing: "同步中",
    tagged: "已打标",
    learned: "已学习",
    archived: "已归档",
  };
  return <Badge variant={status}>{labels[status] ?? status}</Badge>;
}
