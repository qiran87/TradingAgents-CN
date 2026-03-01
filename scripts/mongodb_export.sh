#!/bin/bash
# MongoDB 数据导出脚本
# 用于从 Docker 容器中导出 MongoDB 数据

set -e  # 遇到错误立即退出

# ==================== 配置区 ====================

# MongoDB 连接配置（根据 docker-compose.yml 修改）
MONGO_CONTAINER="tradingagents-mongodb"
MONGO_USERNAME="admin"
MONGO_PASSWORD="tradingagents123"
MONGO_DATABASE="tradingagents"

# 备份配置
BACKUP_DIR="${HOME}/mongodb_backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="mongodb_backup_${TIMESTAMP}.tar.gz"

# ==================== 函数定义 ====================

log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# ==================== 前置检查 ====================

log_info "开始执行 MongoDB 数据导出..."

# 检查 Docker 是否运行
if ! docker ps &> /dev/null; then
    log_error "Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查 MongoDB 容器是否存在
if ! docker ps --format '{{.Names}}' | grep -q "^${MONGO_CONTAINER}$"; then
    log_error "MongoDB 容器 '${MONGO_CONTAINER}' 未运行"
    log_info "请先执行: docker-compose up -d mongodb"
    exit 1
fi

# 创建备份目录
log_info "创建备份目录: ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"

# ==================== 执行导出 ====================

# 检查容器内是否有 mongodump 命令
log_info "检查 mongodump 工具..."
if ! docker exec ${MONGO_CONTAINER} which mongodump &> /dev/null; then
    log_error "容器内没有 mongodump 工具，请检查 MongoDB 镜像版本"
    exit 1
fi

# 在容器内执行 mongodump
log_info "正在导出数据库..."
docker exec ${MONGO_CONTAINER} mongodump \
    --uri="mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@localhost:27017/${MONGO_DATABASE}?authSource=admin" \
    --gzip

# 从容器复制备份文件到宿主机
log_info "复制备份文件到宿主机..."
rm -rf "${BACKUP_DIR}/dump"
docker cp ${MONGO_CONTAINER}:/dump "${BACKUP_DIR}/"

# 打包压缩
log_info "压缩备份文件..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_FILE}" dump

# 清理临时文件
rm -rf dump

# ==================== 导出完成 ====================

# 显示备份文件信息
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

log_info "导出完成！"
echo ""
echo "备份文件信息："
echo "  路径: ${BACKUP_PATH}"
echo "  大小: ${BACKUP_SIZE}"
echo ""
echo "下一步操作："
echo "  1. 传输到目标服务器: scp ${BACKUP_PATH} user@server:/tmp/"
echo "  2. 在目标服务器使用 mongodb_import.sh 导入"
echo ""

# 询问是否查看备份内容
read -p "是否查看备份内容详情？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "正在解压查看内容..."
    cd "${BACKUP_DIR}"
    tar -tzf "${BACKUP_FILE}" | head -20
    echo "..."
    log_info "更多内容可以使用: tar -tzf ${BACKUP_FILE}"
fi
