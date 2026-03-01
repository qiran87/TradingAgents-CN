# MongoDB 数据迁移完整手册

## 📋 目录

1. [迁移前准备](#迁移前准备)
2. [方案一：使用 mongodump/mongorestore（推荐）](#方案一使用-mongodumpmongorestore推荐)
3. [方案二：直接复制数据卷（快速）](#方案二直接复制数据卷快速)
4. [方案三：使用 mongoexport/mongoimport（灵活）](#方案三使用-mongoexportmongoimport灵活)
5. [迁移后验证](#迁移后验证)
6. [常见问题排查](#常见问题排查)

---

⏺ ✅ 迁移手册已创建完成

  我已经为你创建了完整的MongoDB数据迁移方案，包含以下文件：

  📄 文件清单

  ┌─────────────────────────────────┬────────────────────────────┐
  │              文件               │            说明            │
  ├─────────────────────────────────┼────────────────────────────┤
  │ docs/MONGODB_MIGRATION_GUIDE.md │ 详细的迁移手册（图文并茂） │
  ├─────────────────────────────────┼────────────────────────────┤
  │ scripts/mongodb_export.sh       │ 一键导出脚本               │
  ├─────────────────────────────────┼────────────────────────────┤
  │ scripts/mongodb_import.sh       │ 一键导入脚本               │
  └─────────────────────────────────┴────────────────────────────┘

  ---
  🚀 最简单的操作流程（小白版）

  第一步：在源服务器导出数据

  cd /Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN
  ./scripts/mongodb_export.sh

  执行后会：
  1. 自动检查MongoDB容器状态
  2. 执行数据导出
  3. 打包成 .tar.gz 文件
  4. 显示备份文件位置

  第二步：传输文件到目标服务器

  # 将备份文件传输到目标服务器（修改用户名和IP）
  scp ~/mongodb_backup/mongodb_backup_*.tar.gz user@目标服务器IP:/tmp/

  第三步：在目标服务器导入数据

  # 1. 先把项目代码部署到目标服务器
  # 2. 启动数据库
  docker-compose up -d mongodb

  # 3. 执行导入脚本
  ./scripts/mongodb_import.sh /tmp/mongodb_backup_*.tar.gz

  ---
  📖 详细手册位置

  完整文档已保存在：docs/MONGODB_MIGRATION_GUIDE.md

  手册包含：
  - ✅ 三种迁移方案对比
  - ✅ 每个命令的详细说明
  - ✅ 常见问题解决方案
  - ✅ 快速命令参考卡
  - ✅ 迁移后验证步骤

  ---
  ⚠️  注意事项

  1. 导出前：建议停止后端服务，避免数据变更
  docker-compose stop backend
  2. 版本兼容：确保源和目标的MongoDB版本一致（当前是 mongo:4.4）
  3. 磁盘空间：目标服务器需要有足够空间（至少是数据库大小的2倍）
  4. 备份保留：迁移成功前，不要删除源服务器上的备份文件


## 迁移前准备

### 1.1 确认当前 MongoDB 配置

在源服务器上执行以下命令确认配置：

```bash
# 查看 MongoDB 容器状态
docker ps | grep mongodb

# 输出示例：
# CONTAINER ID   IMAGE          COMMAND                  CREATED         STATUS
# abc123def456   mongo:4.4      "docker-entrypoint.s…"   2 weeks ago     Up
```

**当前项目的配置信息：**
| 配置项 | 值 |
|--------|-----|
| 容器名称 | `tradingagents-mongodb` |
| 数据库名称 | `tradingagents` |
| 用户名 | `admin` |
| 密码 | `tradingagents123` |
| 端口 | `27017` |
| 数据卷名称 | `tradingagents_mongodb_data` |

### 1.2 检查数据大小

```bash
# 进入 MongoDB 容器
docker exec -it tradingagents-mongodb bash

# 在容器内执行，查看数据库大小
mongosh -u admin -p tradingagents123 --authenticationDatabase admin --eval "db.stats()"

# 退出容器
exit
```

### 1.3 准备目标服务器

确保目标服务器已安装：
- Docker（版本 20.10+）
- Docker Compose（版本 2.0+）
- 至少有源数据库数据量 2 倍的可用磁盘空间

```bash
# 检查 Docker 版本
docker --version
docker-compose --version

# 检查磁盘空间
df -h
```

### 1.4 停止应用服务（避免数据变更）

**在源服务器上执行：**

```bash
# 停止后端服务，保留数据库运行
docker-compose stop backend

# 确认数据库仍在运行
docker ps | grep mongodb
```

---

## 方案一：使用 mongodump/mongorestore（推荐）

**优点**：官方工具，稳定可靠，支持增量备份
**适用场景**：生产环境、大型数据库

### 步骤 1：在源服务器导出数据

```bash
# 创建备份目录
mkdir -p ~/mongodb_backup
cd ~/mongodb_backup

# 执行 mongodump（完整备份）
docker exec tradingagents-mongodb mongodump \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --gzip

# 从容器复制备份文件到宿主机
docker cp tradingagents-mongodb:/dump ./dump

# 打包压缩（便于传输）
tar -czf mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz dump
```

**命令说明：**
| 参数 | 说明 |
|------|------|
| `--uri` | MongoDB 连接字符串 |
| `--gzip` | 压缩输出，节省空间 |
| `--archive` | 可选，输出到单个归档文件 |

**如果只想导出特定集合（表）：**

```bash
# 只导出股票信息和分析任务
docker exec tradingagents-mongodb mongodump \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --gzip \
  --collection=stock_info \
  --collection=analysis_tasks
```

### 步骤 2：传输数据到目标服务器

**方法 A：使用 scp（推荐）**

```bash
# 在源服务器上，将备份文件传输到目标服务器
# 替换 target_user 和 target_server_ip 为实际值
scp mongodb_backup_*.tar.gz target_user@target_server_ip:/tmp/
```

**方法 B：使用 rsync（大文件推荐，支持断点续传）**

```bash
# 在源服务器上执行
rsync -avz --progress \
  mongodb_backup_*.tar.gz \
  target_user@target_server_ip:/tmp/
```

**方法 C：使用中间服务器**

```bash
# 先上传到云存储（如阿里云OSS、腾讯云COS）
# 然后在目标服务器下载
```

### 步骤 3：在目标服务器导入数据

**3.1 部署项目**

```bash
# 在目标服务器上
cd /path/to/TradingAgents-CN

# 启动数据库服务（不启动应用）
docker-compose up -d mongodb redis

# 等待数据库健康检查通过
docker-compose ps
```

**3.2 解压备份文件**

```bash
cd /tmp
tar -xzf mongodb_backup_*.tar.gz
```

**3.3 导入数据**

```bash
# 将备份文件复制到容器内
docker cp dump tradingagents-mongodb:/tmp/

# 执行 mongorestore
docker exec tradingagents-mongodb mongorestore \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --gzip \
  /tmp/dump

# 等待导入完成，查看输出确认
```

### 步骤 4：验证导入结果

```bash
# 在目标服务器上连接数据库
docker exec -it tradingagents-mongodb mongosh \
  -u admin \
  -p tradingagents123 \
  --authenticationDatabase admin

# 在 mongosh 中执行
use tradingagents
show collections
db.stock_info.countDocuments()
db.analysis_tasks.countDocuments()

# 退出
exit
```

---

## 方案二：直接复制数据卷（快速）

**优点**：最快的方式，直接复制整个数据目录
**适用场景**：同版本 MongoDB、快速迁移

### 步骤 1：在源服务器导出数据卷

```bash
# 停止 MongoDB 容器（确保数据一致性）
docker-compose stop mongodb

# 查找数据卷位置
docker volume inspect tradingagents_mongodb_data

# 备份数据卷
docker run --rm \
  -v tradingagents_mongodb_data:/data/db \
  -v ~/mongodb_volume_backup:/backup \
  alpine tar -czf /backup/mongodb_volume_$(date +%Y%m%d).tar.gz /data/db

# 重启 MongoDB
docker-compose start mongodb
```

### 步骤 2：传输数据

```bash
# 传输到目标服务器
scp ~/mongodb_volume_backup/mongodb_volume_*.tar.gz \
  target_user@target_server_ip:/tmp/
```

### 步骤 3：在目标服务器导入

```bash
# 在目标服务器上，先启动一次数据库（初始化数据卷）
docker-compose up -d mongodb
docker-compose stop mongodb

# 删除现有数据卷（谨慎操作！）
docker volume rm tradingagents_mongodb_data

# 创建新数据卷并导入数据
docker volume create tradingagents_mongodb_data
docker run --rm \
  -v tradingagents_mongodb_data:/data/db \
  -v /tmp:/backup \
  alpine sh -c "cd /data/db && tar -xzf /backup/mongodb_volume_*.tar.gz --strip 1"

# 启动数据库
docker-compose start mongodb
```

---

## 方案三：使用 mongoexport/mongoimport（灵活）

**优点**：可选择性导出，支持 JSON/CSV 格式
**适用场景**：部分数据迁移、数据转换

### 步骤 1：导出特定集合

```bash
# 创建导出目录
mkdir -p ~/mongodb_export

# 导出为 JSON 格式（单个集合）
docker exec tradingagents-mongodb mongoexport \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --collection=stock_info \
  --out=/tmp/stock_info.json \
  --jsonArray

# 复制到宿主机
docker cp tradingagents-mongodb:/tmp/stock_info.json ~/mongodb_export/

# 导出为 CSV 格式（可在 Excel 中查看）
docker exec tradingagents-mongodb mongoexport \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --collection=stock_info \
  --out=/tmp/stock_info.csv \
  --type=csv \
  --fields=symbol,name,market,industry

# 复制到宿主机
docker cp tradingagents-mongodb:/tmp/stock_info.csv ~/mongodb_export/
```

### 步骤 2：导入数据

```bash
# 先复制文件到目标服务器的容器
docker cp ~/mongodb_export/stock_info.json tradingagents-mongodb:/tmp/

# 导入 JSON 数据
docker exec tradingagents-mongodb mongoimport \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --collection=stock_info \
  --file=/tmp/stock_info.json \
  --jsonArray \
  --mode=upsert
```

---

## 迁移后验证

### 4.1 数据完整性验证

```bash
# 在目标服务器上执行
docker exec -it tradingagents-mongodb mongosh \
  -u admin \
  -p tradingagents123 \
  --authenticationDatabase admin

# 在 mongosh 中执行
use tradingagents

// 查看所有集合
show collections

// 统计各集合文档数量
db.stock_info.countDocuments()
db.analysis_tasks.countDocuments()
db.trading_calendar.countDocuments()
db.backtest_results.countDocuments()

// 查看最新数据
db.stock_info.find().sort({created_at: -1}).limit(1)

// 查看数据大小
db.stats()
```

### 4.2 应用连接测试

```bash
# 在目标服务器上启动完整服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend

# 测试 API 健康检查
curl http://localhost:8000/api/health

# 预期响应
# {"success":true,"data":{"status":"healthy","timestamp":"..."}}
```

### 4.3 前端功能测试

1. 访问前端地址：`http://target_server_ip:3000`
2. 登录系统
3. 测试关键功能：
   - 股票搜索
   - 查看分析历史
   - 提交新的分析任务

---

## 常见问题排查

### 问题 1：mongorestore 提示认证失败

**错误信息：** `Authentication failed`

**解决方案：**
```bash
# 确认连接字符串正确，注意 authSource 参数
--uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin"
```

### 问题 2：数据卷权限问题

**错误信息：** `Permission denied`

**解决方案：**
```bash
# 修复数据卷权限
docker run --rm \
  -v tradingagents_mongodb_data:/data/db \
  alpine chown -R 999:999 /data/db
```

### 问题 3：MongoDB 版本不兼容

**解决方案：**
```bash
# 确认两边的 MongoDB 版本一致
docker exec tradingagents-mongodb mongosh --eval "db.version()"

# 如果版本不同，使用 mongodump --forceTableScan
docker exec tradingagents-mongodb mongodump \
  --forceTableScan \
  --uri="mongodb://..."
```

### 问题 4：导入后数据不完整

**解决方案：**
```bash
# 检查 mongorestore 日志，查看是否有错误
# 重新执行导入，添加 --drop 参数（先删除现有数据）
docker exec tradingagents-mongodb mongorestore \
  --drop \
  --uri="mongodb://..." \
  --gzip \
  /tmp/dump
```

### 问题 5：容器内无 mongosh 命令

**解决方案：**
```bash
# mongo:4.4 镜像可能没有 mongosh，使用 mongo 代替
docker exec -it tradingagents-mongodb mongo \
  -u admin \
  -p tradingagents123 \
  --authenticationDatabase admin
```

---

## 📝 快速命令参考卡

### 源服务器（导出）

```bash
# 一键导出脚本
#!/bin/bash
BACKUP_DIR=~/mongodb_backup
mkdir -p $BACKUP_DIR
docker exec tradingagents-mongodb mongodump \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --gzip
docker cp tradingagents-mongodb:/dump $BACKUP_DIR/
cd $BACKUP_DIR
tar -czf mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz dump
echo "备份完成: mongodb_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
```

### 目标服务器（导入）

```bash
# 一键导入脚本
#!/bin/bash
BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
  echo "用法: $0 <备份文件路径>"
  exit 1
fi
tar -xzf $BACKUP_FILE
docker cp dump tradingagents-mongodb:/tmp/
docker exec tradingagents-mongodb mongorestore \
  --uri="mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin" \
  --gzip \
  /tmp/dump
echo "导入完成"
```

---

## ⚠️ 注意事项

1. **数据一致性**：导出数据前停止应用服务，避免数据变更
2. **网络带宽**：大型数据库迁移可能需要较长时间，建议在低峰期进行
3. **备份保留**：迁移成功前，不要删除源服务器上的备份文件
4. **密码安全**：传输过程中注意保护数据库密码
5. **版本兼容**：确保源和目标 MongoDB 版本兼容
6. **磁盘空间**：目标服务器需要有足够空间（至少是数据库大小的2倍）

---

**文档版本**：v1.0
**最后更新**：2026-02-28
**适用版本**：TradingAgents-CN v1.0.0-preview
