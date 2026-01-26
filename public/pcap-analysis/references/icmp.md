# ICMP 分析

## 命令
- `--type icmp`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 可选：`--max-packets`

## 输出（顶层字段）
- `file`
- `analysis_timestamp`
- `total_packets`
- `icmp_packets_found`
- `icmp_packets_analyzed`
- `statistics`
- `packets`
- `note`（可选：限包时）

## 统计字段
- Echo 请求/响应数量与配对情况
- 不可达目的、TTL 指标

## 包详情
- `packet_number`、`timestamp`
- `src_ip`、`dst_ip`、`ip_version`、`ttl`、`packet_size`
- ICMP `type`、`code`、`identifier`、`sequence`、payload 信息

## 说明
- 若未包含 ICMP 流量，将返回 `message` 且 `icmp_packets_found: 0`。
