# CapInfos（抓包元数据）

## 命令
- `--type capinfos`

## 输入
- `--pcap`：绝对路径或 HTTP URL

## 输出（顶层字段）
- `file_size_bytes`、`filename`、`file_encapsulation`
- `packet_count`、`data_size_bytes`
- `capture_duration_seconds`
- `first_packet_time`、`last_packet_time`
- `data_rate_bytes`、`data_rate_bits`
- `average_packet_size_bytes`、`average_packet_rate`

## 说明
- 输出结构类似 Wireshark 的 `capinfos`。
