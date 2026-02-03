# DHCP 分析

## 命令
- `--type dhcp`

## 输入
- `--pcap`：绝对路径或 HTTP URL
- 可选：`--max-packets`

## 输出（顶层字段）
- `file`
- `total_packets`
- `dhcp_packets_found`
- `dhcp_packets_analyzed`
- `statistics`
- `packets`
- `note`（可选：限包时）

## 统计字段
- `unique_clients_count`、`unique_servers_count`
- `unique_clients`、`unique_servers`
- `message_type_counts`
- `transaction_count`、`transactions`

## 包详情
- IP/UDP 元信息、DHCP 消息类型、事务 ID、客户端 MAC
- 解析后的 DHCP 选项（网关、DNS、租期、主机名等）

## 说明
- 若未包含 DHCP 流量，将返回 `message` 且 `dhcp_packets_found: 0`。
