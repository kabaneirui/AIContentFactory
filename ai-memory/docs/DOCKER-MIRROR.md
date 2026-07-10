# Docker 镜像拉取失败 — 解决指南（国内 Windows / Mac）

报错类似：

```
failed to resolve reference "docker.io/library/postgres:16-alpine"
dial tcp ... registry-1.docker.io:443: connectex ...
```

或构建时报：

```
FROM python:3.12-slim
failed to fetch oauth token: Post "https://auth.docker.io/token": dial tcp ... connectex
```

说明 **连不上 Docker Hub**（含拉取镜像与构建时的基础镜像），不是 Dockerfile 写错。

---

## 方案 1：一键用国内镜像源启动（最快）

在项目目录执行：

**Windows（PowerShell）：**

```powershell
cd ai-memory
docker compose -f docker-compose.yml -f docker-compose.cn.yml up --build
```

**Mac / Linux：**

```bash
cd ai-memory
docker compose -f docker-compose.yml -f docker-compose.cn.yml up --build
```

`docker-compose.cn.yml` 会把以下镜像换成 DaoCloud 代理：

| 用途 | 镜像 |
|------|------|
| 数据库 | `postgres:16-alpine` |
| 缓存 | `redis:7-alpine` |
| 后端构建 | `python:3.12-slim` |
| 前端构建 | `node:22-alpine`、`nginx:alpine` |

无需改原 `docker-compose.yml` / `Dockerfile`。

---

## 方案 2：配置 Docker Desktop 全局镜像加速（推荐长期使用）

1. 打开 **Docker Desktop**
2. **Settings（设置）→ Docker Engine**
3. 在 JSON 中加入 `registry-mirrors`（保留原有字段，只追加）：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.m.daocloud.io"
  ]
}
```

4. 点击 **Apply & Restart**
5. 再执行：

```powershell
docker compose up --build
```

> 镜像站地址可能变动；若失效，搜索「Docker 镜像加速 2026」换最新可用源。  
> 阿里云用户可在容器镜像服务控制台获取**个人专属加速地址**（更稳定）。

---

## 方案 3：手动预拉镜像

配置加速后，先单独拉取：

```powershell
docker pull docker.m.daocloud.io/library/postgres:16-alpine
docker pull docker.m.daocloud.io/library/redis:7-alpine
docker pull docker.m.daocloud.io/library/python:3.12-slim
docker pull docker.m.daocloud.io/library/node:22-alpine
docker pull docker.m.daocloud.io/library/nginx:alpine

docker compose -f docker-compose.yml -f docker-compose.cn.yml up --build
```

---

## 方案 4：不用 Docker（彻底绕过镜像问题）

若仍拉不下来，**不必强求 Docker**：

**Windows：**

```powershell
cd ai-memory
.\setup.bat
.\start.bat
```

访问 http://localhost:5173

详见 [STANDALONE.md](STANDALONE.md)。

---

## 检查是否修好

```powershell
docker pull hello-world
```

成功则镜像加速生效。

```powershell
docker compose -f docker-compose.yml -f docker-compose.cn.yml config
```

应看到 postgres/redis 及 backend/frontend 的 build args 使用 `docker.m.daocloud.io/...` 地址。

---

## Docker Desktop 有用吗？能卸载吗？

| 你的情况 | 建议 |
|----------|------|
| 镜像已修好，想用一键部署 | **保留** Docker Desktop，用 `docker compose up` |
| 一直拉不下镜像，已用 `start.bat` 本地跑 | **可以卸载** Docker Desktop |
| 只是不想用 WSL 终端 | WSL 是 Docker 底层，**不必日常打开**；卸载 Docker 后 WSL 可单独保留或删除 |

### 卸载 Docker Desktop（Windows）

1. **设置 → 应用 → 已安装的应用 → Docker Desktop → 卸载**
2. （可选）若不再需要 WSL：PowerShell 管理员执行  
   `wsl --unregister Ubuntu`（会删除该 Linux 发行版数据）

### 卸载后怎么跑 AI Memory

只用本地脚本，需自行安装：

- Python 3.11+
- Node.js 18+
- PostgreSQL 16

然后 `setup.bat` → `start.bat`，**不依赖 Docker、不依赖 WSL**。

---

## 常见问题

**Q：配置了镜像还是慢？**  
A：换手机热点试；或直接用 `docker-compose.cn.yml` + 方案 4。

**Q：公司网络有代理？**  
A：Docker Desktop → Settings → Resources → Proxies，填写公司代理或关闭错误代理。

**Q：WSL 和 Docker 必须一起卸吗？**  
A：不必。卸 Docker Desktop 不影响 WSL；WSL 也可单独保留给别的开发用。
