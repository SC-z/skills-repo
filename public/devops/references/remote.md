# Remote 工具使用

## 必须遵守

- 始终使用 REMOTE_BEAUTY_LEVEL=1
- 每条命令必须包含该环境变量，并使用 scripts/
- 避免破坏性命令；如需高风险操作，先征求用户确认。

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-executor.sh "<server>" "<command>"
```

## 可选环境变量

- REMOTE_SSH_USER：SSH 用户名；当 <server> 不含 user@ 时使用，默认 root。
- REMOTE_SSH_PASSWORD：设置后仅使用该密码进行密码登录尝试（仍先尝试密钥）。
- REMOTE_SSH_PORT：SSH 端口（等价于 ssh -p）。

示例：

```bash
REMOTE_SSH_USER=root REMOTE_SSH_PORT=2222 REMOTE_SSH_PASSWORD="secret" \
REMOTE_BEAUTY_LEVEL=1 scripts/remote-executor.sh "10.0.0.1" "whoami"
```

## 执行模式

### 单命令

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-executor.sh "<server>" "<command>"
```

### 并行多命令

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-parallel.sh "<server>" "cmd1" "cmd2" "cmd3"
```

### 并行详细（调试）

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-parallel.sh -v "<server>" "cmd1" "cmd2"
```

## 任务理解规范

### 应做

- 先理解意图，不照抄命令
- 首轮收集完整数据（不先 grep/head/tail）
- 多维检查用并行
- 先全面诊断，再针对性补充

### 不应做

- 首轮过滤数据
- 可并行却串行
- 信息不全就结论
- 遗漏 REMOTE_BEAUTY_LEVEL=1

## 常见任务事例

### 系统健康检查

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-parallel.sh "<server>" \
    "uptime && free -h && df -h" \
    "ps aux --sort=-%cpu | head -20" \
    "ps aux --sort=-%mem | head -20" \
    "systemctl list-units --failed" \
    "dmesg | tail -50"
```

### 磁盘空间分析

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-parallel.sh "<server>" \
    "df -h && df -i" \
    "du -sh /* 2>/dev/null | sort -hr | head -20" \
    "lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSUSE%"
```

### CPU 性能检查

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-parallel.sh "<server>" \
    "uptime && mpstat -P ALL 1 3" \
    "ps aux --sort=-%cpu | head -30" \
    "top -b -n 1 | head -50"
```

### 网络诊断

```bash
REMOTE_BEAUTY_LEVEL=1 scripts/remote-parallel.sh "<server>" \
    "ss -tunlp && ss -s" \
    "ip addr show && ip route show" \
    "netstat -i && iptables -L -n -v | head -50"
```
