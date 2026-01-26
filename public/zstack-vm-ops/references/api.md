# ZStack API 说明（本环境）

## 认证

- 登录接口：`PUT /zstack/v1/accounts/login`
- 默认账号密码：`admin/password`
- 密码需做 SHA-512 十六进制：

```json
{
  "logInByAccount": {
    "accountName": "admin",
    "password": "<sha512-hex>"
  }
}
```

- 返回 `inventory.uuid` 作为会话 ID。
- 认证头：`Authorization: OAuth <session-uuid>`。

## VM 查询

- 列表：`GET /zstack/v1/vm-instances`
- 按状态过滤：`GET /zstack/v1/vm-instances?q=state=Running`

## L3 网络

- 列表：`GET /zstack/v1/l3-networks`
- VM 网卡里通过 `l3NetworkUuid` 关联 L3 网络名称。

## 开机 / 关机

- 开机：`PUT /zstack/v1/vm-instances/{vmUuid}/actions`

```json
{ "startVmInstance": {} }
```

- 关机：`PUT /zstack/v1/vm-instances/{vmUuid}/actions`

```json
{ "stopVmInstance": { "type": "grace" } }
```

- 可能返回 `202`，带 `location` 指向异步任务。
- 异步任务轮询：`GET /zstack/v1/api-jobs/{jobUuid}`。

## 添加网卡（绑定 L3）

- 推荐接口：`POST /zstack/v1/vm-instances/{vmUuid}/l3-networks/{l3Uuid}`
- 部分环境允许 `GET` 作为兼容回退。
- 可能返回 `202` 异步任务。

## 删除网卡

- 优先：`DELETE /zstack/v1/vm-instances/nics/{vmNicUuid}`
- 备用：`DELETE /zstack/v1/vm-instances/{vmUuid}/nics/{vmNicUuid}`
- 可能返回 `202` 异步任务。
