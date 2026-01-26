# TCP 连接分析

## 命令
- `--type tcp-connections`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 可选：`--server-ip`、`--server-port`、`--detailed`、`--max-packets`

## 输出（顶层字段）
- `analysis_timestamp`
- `total_packets`、`tcp_packets_found`
- `filter`（server_ip/server_port）
- `summary`：连接总数、握手成功/失败、RST/正常关闭等
- `connections`：连接概要列表（默认仅前 10，`--detailed` 全量）
- `issues`：人类可读的摘要问题

## 连接条目字段
- `client`、`server`
- `state`、`handshake_completed`
- `syn_count`、`syn_ack_count`、`ack_count`
- `rst_count`、`fin_count`、`data_packets`、`retransmissions`
- `close_reason`、`packet_count`
