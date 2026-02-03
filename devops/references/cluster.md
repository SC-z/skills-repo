# QDataMgr 使用

qdatamgr 是一体机集群管理的核心工具，在终端执行 qdatamgr 相关命令，可以获取到大部分一体机相关的信息

## 组件命令速查（只列常用/只读）

### conf

- `qdatamgr conf show -s` - 展示集群节点信息
- `qdatamgr conf show -t` - 展示集群所有节点上的 qlink 部署情况
- `qdatamgr conf time` - 展示集群数据库db文件的同步时间

### qlink

- `qdatamgr qlink show -t` - 展示qlink链路启动情况
- `qdatamgr qlink show -c` - 展示qlink链路挂载情况

### media

- `qdatamgr media show` - 展示节点所有磁盘信息
- `qdatamgr media show_disk` - 展示节点raid卡管理的 ssd、hdd 磁盘信息
- `qdatamgr media show_disk -p` - 展示节点raid卡管理的 ssd、hdd 磁盘物理信息
- `qdatamgr media show_nvme` - 展示节点上nvme磁盘信息

## qdatamgr 问题排查经验

### 日志排查

场景：

- 在终端执行 qdatamgr 相关命令出错时

排查：

- 日志位置
  - qdatamgr 客户端日志位置：/usr/local/sendoh/logs/qdatamgr_cli/qdatamgr_cli.log
  - qdatamgr 服务端日志位置：/usr/local/sendoh/logs/qdatamgr_server/xxxx
    - /usr/local/sendoh/logs/qdatamgr_server/module_xxx.log：每个模块的日志信息
    - /usr/local/sendoh/logs/qdatamgr_server/record_system_cmd.log：调用的系统底层命令记录，只有命令及时间信息
    - /usr/local/sendoh/logs/qdatamgr_server/execute_cmd.log：调用的系统底层命令及其输出记录
    - /usr/local/sendoh/logs/qdatamgr_server/record_web_request.log：服务端接收到的请求记录

        ```txt
        2026-01-05 20:21:24.469 | INFO     | 127.0.0.1:49292 - "GET /qdatamgr/api/v1/conf/node_type HTTP/1.1"  200 OK (19.47 ms)
        2026-01-05 20:21:24.470 | INFO     | 127.0.0.1:49294 - "GET /qdatamgr/api/v1/conf/node_type HTTP/1.1"  200 OK (19.65 ms)
        2026-01-05 20:21:24.480 | INFO     | 127.0.0.1:49316 - "GET /qdatamgr/api/v1/version/qdata HTTP/1.1" BEGIN
        2026-01-05 20:21:24.483 | INFO     | 127.0.0.1:49318 - "GET /qdatamgr/api/v1/version/qdata HTTP/1.1" BEGIN
        2026-01-05 20:21:24.484 | INFO     | 127.0.0.1:49316 - "GET /qdatamgr/api/v1/version/qdata HTTP/1.1"  200 OK (4.58 ms)
        2026-01-05 20:21:24.492 | INFO     | 127.0.0.1:49318 - "GET /qdatamgr/api/v1/version/qdata HTTP/1.1"  200 OK (9.17 ms)
        ```

- 排查过程
  - 执行 qdatamgr 终端命令发生错误时
  - 第一时间查看对应的服务端模块日志信息
  - 找到日志中的报错信息，并进行分析
  - 如果日志中没有有用信息，则需要进一步分析系统错误信息
