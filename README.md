# ReName

ReName 是一个面向 BT 下载影视资源的 Web 工具，用于扫描下载目录、借助 LLM 解析资源名称、查询 TMDB 元数据，并生成符合 Emby/Jellyfin/Plex 习惯的媒体库命名结构。项目支持硬链接、复制和移动文件，适合把下载目录整理到媒体库目录。

## 功能特性

- 扫描电影、电视剧、动漫资源目录
- 支持常见视频格式：`mkv`、`mp4`、`avi`、`ts`、`m2ts`、`mov`、`wmv`、`flv`、`webm`
- OpenAI 兼容 LLM 解析
  - 支持 `/chat/completions`
  - 支持流式输出展示
  - 支持获取 `/models` 模型列表
- TMDB 搜索与候选选择
  - 支持电影和剧集搜索
  - 显示 TMDB 海报
- 自动过滤非正片内容
  - `menu`
  - `BDMenu`
  - `PV`
  - `CM`
  - `NCOP`
  - `NCED`
  - `特典`
  - `Tokuten`
  - `Fonts`
  - `MANGA`
  - `sample`
  - `trailer`
- 生成重命名预览
- 执行文件操作
  - 硬链接
  - 复制
  - 移动
- 支持电影、电视剧、动漫独立媒体库目录
- 支持 Windows 和 Linux

## 技术栈

### 后端

- Python 3.12+
- FastAPI
- SQLModel
- SQLite
- httpx
- Pydantic Settings

### 前端

- React
- TypeScript
- Vite
- Ant Design

## 项目结构

```text
ReName/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── .env.example
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── start-backend.ps1
├── start-frontend.ps1
└── .gitignore
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/fuunylmz/ReName.git
cd ReName
```

### 2. 启动后端

#### Windows PowerShell

```powershell
.\start-backend.ps1
```

或手动启动：

```powershell
cd backend
python -m pip install -e .[dev]
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Linux / macOS

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端

#### Windows PowerShell

```powershell
.\start-frontend.ps1
```

或手动启动：

```powershell
cd frontend
npm install
npm run dev
```

#### Linux / macOS

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

前端默认地址：

```text
http://localhost:5173
```

后端默认地址：

```text
http://localhost:8000
```

## 配置说明

可以通过 WebUI 的“设置”页面配置，也可以通过后端 `.env` 配置默认值。

复制环境变量示例：

```bash
cp backend/.env.example backend/.env
```

`.env.example` 内容：

```env
TMDB_API_KEY=
TMDB_LANGUAGE=zh-CN
LLM_API_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
MOVIE_LIBRARY_PATH=
TV_LIBRARY_PATH=
ANIME_LIBRARY_PATH=
DEFAULT_OPERATION=hardlink
```

### TMDB

需要配置 TMDB API Key：

```text
TMDB_API_KEY
```

WebUI 设置页中的 TMDB 配置优先级高于 `.env`。

### LLM

LLM 接口要求兼容 OpenAI 格式：

```text
POST {LLM_API_BASE_URL}/chat/completions
GET  {LLM_API_BASE_URL}/models
```

例如：

```text
https://api.openai.com/v1
https://api.deepseek.com/v1
http://localhost:11434/v1
http://localhost:1234/v1
```

需要配置：

```text
LLM_API_BASE_URL
LLM_API_KEY
LLM_MODEL
```

如果没有配置 LLM，系统会回退到本地规则解析。

## 使用流程

1. 打开 WebUI
2. 进入“设置”页面
3. 配置：
   - TMDB API Key
   - LLM API Base URL
   - LLM API Key
   - LLM 模型
   - 电影媒体库目录
   - 电视剧媒体库目录
   - 动漫媒体库目录
   - 默认文件操作
4. 进入“媒体扫描”页面
5. 输入下载目录并扫描
6. 选择资源进入“识别与预览”
7. 点击“LLM / 规则解析”
8. 点击“查询 TMDB”
9. 选择正确的 TMDB 候选
10. 选择硬链接、复制或移动
11. 点击“生成预览”
12. 确认目标路径无误后点击“执行硬链接”或“执行操作”

## 硬链接说明

硬链接不会复制文件内容，创建速度快且节省空间。源文件和目标文件会指向同一份实际数据。

限制：

- 源路径和目标路径必须在同一个文件系统/分区
- Windows 下不能对目录创建硬链接，本项目只对文件创建硬链接
- 如果目标文件已存在，当前实现会跳过，不会覆盖

跨盘或跨挂载点时，硬链接可能失败，例如：

```text
Invalid cross-device link
```

这种情况下请使用“复制”。

## Linux 路径示例

下载目录：

```text
/data/download/番剧
```

动漫媒体库：

```text
/data/media/anime
```

电影媒体库：

```text
/data/media/movies
```

电视剧媒体库：

```text
/data/media/tv
```

## Windows 路径示例

下载目录：

```text
D:\Downloads
```

动漫媒体库：

```text
D:\Media\Anime
```

电影媒体库：

```text
D:\Media\Movies
```

电视剧媒体库：

```text
D:\Media\TV Shows
```

## 开发命令

### 后端检查

```bash
cd backend
python -m ruff check app
python -m mypy app
```

### 前端检查

```bash
cd frontend
npm run lint
npm run build
```

## 注意事项

- 不要提交 `.env` 文件
- 不要提交媒体文件
- 建议先生成预览并确认目标路径，再执行硬链接、复制或移动
- 执行“移动”会移动原文件，请谨慎使用
- LLM 解析结果可能不完全准确，TMDB 候选需要人工确认
- 已生成的旧重命名计划不会自动更新，如果修改配置或解析规则，请重新生成预览

## License

暂未指定 License。
