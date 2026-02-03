# TCP 流量方向分析

## 命令
- `--type tcp-traffic-flow`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 必填：`--server-ip`
- 可选：`--server-port`

## 输出（顶层字段）
- `analysis_timestamp`
- `server`："<ip>:<port|any>"
- `client_to_server`：包/字节统计与标志计数、重传数
- `server_to_client`：包/字节统计与标志计数、重传数
- `analysis`：不对称比例、主要 RST 来源、流量方向判断

## 说明
- 缺少 `server_ip` 时会返回错误。
