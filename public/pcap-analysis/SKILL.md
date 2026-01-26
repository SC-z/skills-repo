---
name: pcap-analysis
description: 使用内置的 DNS、DHCP、ICMP、TCP 与 CapInfos 分析器对本地路径的 PCAP/PCAPNG 抓包进行离线分析（不依赖 mcpcap 模块，也不使用 MCP；不支持 HTTP URL）。适用于：1) 网络排障（握手失败、RST、重传、流量不对称）；2) 安全取证（可疑域名、异常连接模式、设备指纹）；3) 运维统计（抓包元数据、协议分布与关键指标）。TCP 场景细化：三次握手成功率、SYN/SYN-ACK 比例、连接异常终止（RST/FIN）、重传率与连接质量、流量方向不对称、客户端/服务端 RST 源定位、疑似扫描/洪泛/连接异常模式等。支持 .pcap/.pcapng/.cap。
---

# PCAP 分析

## 快速开始

- 通过 `scripts/pcap_analyze.py` 分析抓包；不要使用 MCP。
- `--pcap` 必须是本地绝对路径（不支持 HTTP URL）。
- 确保依赖已安装（`scapy`）。

## 工作流

1. 确定分析类型（`dns`、`dhcp`、`icmp`、`capinfos`、`tcp-*` 或 `all`）。
2. 准备输入（PCAP 本地路径、TCP 过滤参数、限制参数）。
3. 运行脚本并获取 JSON 输出。
4. 汇总结果，标出 `error` 或 `note` 字段。

## 命令示例

```bash
python skills/pcap-analysis/scripts/pcap_analyze.py --type dns --pcap /abs/path/file.pcap --pretty
python skills/pcap-analysis/scripts/pcap_analyze.py --type tcp-connections --pcap /abs/path/file.pcap --server-ip 10.0.0.5 --detailed
python skills/pcap-analysis/scripts/pcap_analyze.py --type tcp-retransmissions --pcap /abs/path/file.pcap --threshold 0.05
python skills/pcap-analysis/scripts/pcap_analyze.py --type all --pcap /abs/path/file.pcap --no-traffic-flow
```

## 参考文档

- DNS 输出：`references/dns.md`
- DHCP 输出：`references/dhcp.md`
- ICMP 输出：`references/icmp.md`
- CapInfos 输出：`references/capinfos.md`
- TCP 连接分析：`references/tcp-connections.md`
- TCP 异常/模式：`references/tcp-anomalies.md`
- TCP 重传分析：`references/tcp-retransmissions.md`
- TCP 流量方向：`references/tcp-traffic-flow.md`
