# 航站楼联合巡检 · 单文件展示页

`index.html` 是一个可以直接部署的单文件页面，已经内置三维机场画面、三路同步视角、8 台设备状态、三个作业区、任务节点、现场记录和 JSON 导出。

## 使用方式

最简单的方式是直接双击 `index.html`，或把它上传到任意静态网站托管：

- Nginx / Apache / IIS：把 `index.html` 放到站点目录；
- Vercel / Netlify / GitHub Pages：把这个文件作为静态站点入口；
- 本地预览：在当前目录运行 `python -m http.server 8093`，打开 `http://localhost:8093/`。

页面不依赖 Docker、ROS、Node.js、数据库或 API Key。点击“启动联合作业”后，页面按已记录的三维机场作业时间线播放；播放速度可选 1×、2×、4×，可拖动进度条或点击右侧关键节点跳转。现场记录可单张放大查看，报告按钮会下载当前进度的 JSON。

## 文件

- `index.html`：交付文件，单文件约 16 MB；部署时只需要这个文件。
- `build-manifest.json`：构建信息和内容统计。
- `build.py`、`source/`：重新生成页面时使用的构建源文件，可不上传。

这是一份离线录制的展示版，用于路演时稳定呈现已完成的机场三维协同作业。仓库中的 Docker 版本仍然保留 ROS 2 / Open-RMF / Gazebo 服务入口，见 `outputs/fire-repo/simulations/airport/README.zh-CN.md`。
