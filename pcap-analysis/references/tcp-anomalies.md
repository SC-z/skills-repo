# TCP 异常/模式（基于统计观察）

## 命令
- `--type tcp-anomalies`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 可选：`--server-ip`、`--server-port`

## 输出（顶层字段）
- `analysis_timestamp`
- `filter`
- `statistics`：flag 计数、握手统计、RST 分布、重传率、连接状态
- `patterns`：可观察模式及其证据
- `summary`：模式数量与显著观察项

## 说明
- 本分析仅给出可观察模式（如 RST 偏向、重传率、握手失败率），不做根因诊断。
