import { NavLink, Outlet } from "react-router-dom";
import { useAccount } from "../context/AccountContext";
import { Loading } from "./ui";

const navItems = [
  { to: "/", label: "账号画像", end: true },
  { to: "/decision", label: "决策中心" },
  { to: "/videos", label: "视频记忆" },
  { to: "/learning", label: "学习报告" },
  { to: "/predict", label: "预测拦截" },
  { to: "/prompts", label: "Prompt 管理" },
  { to: "/import", label: "数据导入" },
];

export function Layout() {
  const { accounts, accountId, setAccountId, currentAccount, loading } = useAccount();

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
            <p>请先在侧边栏创建或选择账号。可通过 API 创建账号后刷新页面。</p>
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
