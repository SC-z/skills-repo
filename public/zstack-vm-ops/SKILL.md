---
name: zstack-vm-ops
description: 通过 ZStack REST API 执行虚拟机运维：查询 VM 状态/网卡与 L3 网络、开关机、添加/删除/替换 L3 网卡；支持根据部分主机名或网段做模糊匹配并进行网卡变更。用于管理 ZStack VM 电源状态、网卡绑定或输出 VM+NIC 状态列表。
---

# ZStack VM 运维

## 概览

使用本技能配套脚本通过 REST API 操作 ZStack 虚拟机。

## 快速开始

- 设置环境变量或直接传参：
  - `ZSTACK_HOST`（默认8080端口，示例：`http://10.10.20.30:8080`）
  - `ZSTACK_USERNAME`（默认：`admin`）
  - `ZSTACK_PASSWORD`（默认：`password`，明文，脚本内部会做 SHA-512）
- 运行脚本：`scripts/zstack_vm_ops.py`。
- 注意：全局参数必须放在子命令前。

## 交互与默认策略

- 先使用传入ip 使用默认账号密码：`admin/password`登陆，无法登入询问确认。
- 使用模糊匹配解析 VM 名称和 L3 网络：优先精确匹配，其次前缀匹配，再次包含匹配；匹配只保留最可能候选。
- 只有当候选不止一个时才发起确认；需要确认时合并为一次问题（同时确认主机名与网段）。
- 当用户只给出网段号或子网（如“170 网段”），通过 L3 列表的 `ipRanges` 或名称包含关系定位；唯一命中则直接使用。

## 网卡默认策略（替换/删除）

- 视 `L3-novlan-20` 为默认网卡，通常保留不动。
- 当 VM 只有两张网卡且其中一张是 `L3-novlan-20` 时，替换/删除默认作用于另一张网卡，无需重复确认。
- 若存在多张非 20 网卡或未发现 20 网卡，必须询问目标网卡（一次性确认）。

## 任务

### 查询 VM 状态与网卡

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password list-vms
```

输出：JSON 列表，包含 `name`、`state` 和 `nics`（`name` 为 L3 网络名称，`ip` 为 IP 地址）。
可选过滤：`--state Running`、`--name <vm-name>`。

### 查询 L3 网络与网段

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password list-l3
```

输出：JSON 列表，包含 `name`、`uuid`、`ipRanges`。
可选过滤：`--name <l3-name>`。

### 开机 / 关机

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password start-vm --vm-name polar1
```

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password stop-vm --vm-name polar1 --type grace
```

`--type` 支持 `grace` 或 `cold`。

### 添加网卡（关机 -> 绑定 L3 -> 开机）

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password add-nic --vm-name polar1 --l3-name L3-novlan-20
```

行为：若 VM 正在运行，会先关机，绑定 L3 网络后再开机。
如果部署环境对该接口返回 404/405，可加 `--allow-get-fallback` 重试。

### 更换网卡（关机 -> 解绑 -> 绑定 -> 开机）

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password replace-nic \
  --vm-name polar1 --from-l3-name L3-VLAN-150 --to-l3-name L3-VLAN-170
```

行为：若 VM 正在运行，会先关机，解绑旧网卡，绑定新 L3 后再开机。
若目标 L3 已存在，则只移除旧网卡并开机（避免重复绑定）。

### 删除网卡（关机 -> 解绑网卡 -> 开机）

优先使用网卡 UUID：

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password remove-nic --vm-name polar1 --nic-uuid <nic-uuid>
```

或用 L3 网络匹配（仅当该 VM 在该 L3 上只有一张网卡时）：

```bash
python3 scripts/zstack_vm_ops.py --host http://10.10.20.30:8080 \
  --username admin --password password remove-nic --vm-name polar1 --l3-name L3-novlan-20
```

行为：若 VM 正在运行，会先关机，解绑网卡后再开机。

### 更换网卡（常用流程）

1. 解析 VM 与目标 L3（遵循“交互与默认策略”）。
2. 如需替换非 20 网卡：优先使用 `replace-nic`（单次关机/开机）。
3. 若 VM 仅两张网卡且一张为 `L3-novlan-20`，默认替换另一张。

## 参考

阅读 `references/api.md` 获取接口细节、异步任务说明以及网卡绑定/解绑注意事项。
