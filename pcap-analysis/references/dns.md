# DNS 分析

## 命令
- `--type dns`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 可选：`--max-packets`（限制分析的 DNS 包数量）

## 输出（顶层字段）
- `file`：输入路径或 URL
- `analysis_timestamp`：ISO-8601 时间戳
- `total_packets_in_file`
- `dns_packets_found`
- `dns_packets_analyzed`
- `statistics`：查询/响应/唯一域名统计
- `packets`：逐包 DNS 解析详情
- `note`（可选）：当触发限包时出现

## 包详情（`packets` 中每条）
- `packet_number`、`timestamp`
- `src_ip`、`dst_ip`、`protocol`（UDP/TCP）
- `dns_id`、`flags`（请求/响应与递归标志）
- `question_count`、`answer_count`
- `questions`：`{name, type, class}`
- `answers`：`{name, type, class, ttl, address/cname/mx/data}`

## 说明
- 若未包含 DNS 流量，将返回 `message` 且 `dns_packets_found: 0`。
