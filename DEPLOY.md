# 部署指南

## 免费部署方案（Vercel + Render）

### 1. 部署后端到 Render

1. 访问 https://dashboard.render.com/
2. 点击 **New +** → **Web Service**
3. 选择你的 GitHub 仓库 `mingxin/zizi`
4. 配置选项：
   - **Name**: `zizi-backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. 点击 **Create Web Service**
6. 等待部署完成，记录分配的域名（如 `https://zizi-backend.onrender.com`）

### 2. 部署前端到 Vercel

1. 访问 https://vercel.com/new
2. 导入你的 GitHub 仓库 `mingxin/zizi`
3. 配置选项：
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Environment Variables**: 添加 `NEXT_PUBLIC_API_URL=https://你的后端域名`（上一步的后端地址）
4. 点击 **Deploy**

### 3. 配置 CORS（如果需要）

部署后，更新 `backend/main.py` 中的 CORS 配置，添加前端域名：

```python
allow_origins=[
    "https://你的前端域名.vercel.app",
    "http://localhost:3000",
]
```

然后提交代码，Render 会自动重新部署。

---

## 本地开发

```bash
# 启动后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000
