# Multiagent Peer Review DeepAgent

固定维度的论文评审工作流，使用 LangGraph 负责编排，LangChain 官方 Deep Agents 负责维度评审、critic 审核和评分校准。

## 本地配置

1. 复制 `.env.example` 为 `.env`。
2. 只在 `.env` 中填写真实的 API key、base URL 和数据库连接串。
3. 不要提交 `.env`、`outputs*`、虚拟环境、缓存目录或真实论文样例。

## GitHub 上传前检查

本仓库的 `.gitignore` 已默认排除本地密钥、运行输出、日志、数据库、私有数据文件、证书以及 `examples/paper_*.md` 这类真实论文输入。公开仓库建议只保留脱敏后的 `examples/sample_paper.md`。
