# TCP 重传分析

## 命令
- `--type tcp-retransmissions`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 可选：`--server-ip`、`--threshold`

## 输出（顶层字段）
- `analysis_timestamp`
- `total_packets`、`total_retransmissions`、`retransmission_rate`
- `threshold`、`exceeds_threshold`
- `by_connection`：重传率最高的前 10 条连接
- `summary`：最差连接与超阈值连接数
