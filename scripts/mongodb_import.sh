#!/bin/bash
# MongoDB 数据导入脚本
# 用于将备份文件导入到 Docker 容器的 MongoDB

set -e  # 遇到错误立即退出

# ==================== 配置区 ====================

# MongoDB 连接配置（根据 docker-compose.yml 修改）
MONGO_CONTAINER="tradingagents-mongodb"
MONGO_USERNAME="admin"
MONGO_PASSWORD="tradingagents123"
MONGO_DATABASE="tradingagents"

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

confirm() {
    read -p "$1 (y/n) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# ==================== 前置检查 ====================

# 检查参数
if [ $# -eq 0 ]; then
    log_error "请提供备份文件路径"
    echo "用法: $0 <备份文件.tar.gz>"
    echo "示例: $0 /tmp/mongodb_backup_20260228_120000.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"

# 检查文件是否存在
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "备份文件不存在: ${BACKUP_FILE}"
    exit 1
fi

log_info "开始执行 MongoDB 数据导入..."
log_info "备份文件: ${BACKUP_FILE}"

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

# 检查 mongorestore 工具
if ! docker exec ${MONGO_CONTAINER} which mongorestore &> /dev/null; then
    log_error "容器内没有 mongorestore 工具，请检查 MongoDB 镜像版本"
    exit 1
fi

# ==================== 解压备份文件 ====================

TEMP_DIR="/tmp/mongodb_import_$$"
log_info "创建临时目录: ${TEMP_DIR}"
mkdir -p "${TEMP_DIR}"

log_info "解压备份文件..."
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"

if [ ! -d "${TEMP_DIR}/dump" ]; then
    log_error "备份文件格式不正确，找不到 dump 目录"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# 清理 macOS 元数据文件（Apple Double 格式）
log_info "清理 macOS 元数据文件..."
find "${TEMP_DIR}/dump" -name "._*" -type f -delete
find "${TEMP_DIR}/dump" -name ".DS_Store" -type f -delete

log_info "清理完成，继续导入..."

# ==================== 导入前确认 ====================

# 显示将要导入的数据库信息
log_info "备份内容预览："
ls -lh "${TEMP_DIR}/dump/" 2>/dev/null || echo "（无法列出）"

echo ""
log_warn "警告：导入将覆盖目标数据库中的同名集合！"

if ! confirm "确认要继续导入吗？"; then
    log_info "导入已取消"
    rm -rf "${TEMP_DIR}"
    exit 0
fi

# ==================== 执行导入 ====================

# 复制备份文件到容器
log_info "复制备份文件到容器..."
docker cp "${TEMP_DIR}/dump" ${MONGO_CONTAINER}:/tmp/

# 在容器内清理 macOS 元数据文件
log_info "清理容器内的 macOS 元数据文件..."
docker exec ${MONGO_CONTAINER} find /tmp/dump -type f -name "._*" -delete
docker exec ${MONGO_CONTAINER} find /tmp/dump -type f -name ".DS_Store" -delete

# 在容器内执行 mongorestore（使用 --nsInclude 避免 deprecated 警告）
log_info "正在导入数据，请稍候..."
docker exec ${MONGO_CONTAINER} mongorestore \
    --uri="mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@localhost:27017/${MONGO_DATABASE}?authSource=admin" \
    --nsInclude="${MONGO_DATABASE}.*" \
    --gzip \
    /tmp/dump

# 清理容器内的临时文件
log_info "清理容器内临时文件..."
docker exec ${MONGO_CONTAINER} rm -rf /tmp/dump

# 清理宿主机临时目录
rm -rf "${TEMP_DIR}"

# ==================== 导入完成 ====================

log_info "数据导入完成！"
echo ""

# 验证导入结果
log_info "验证导入结果..."

# 检查可用的 MongoDB shell 工具
MONGO_SHELL=""
if docker exec ${MONGO_CONTAINER} which mongosh &> /dev/null; then
    MONGO_SHELL="mongosh"
elif docker exec ${MONGO_CONTAINER} which mongo &> /dev/null; then
    MONGO_SHELL="mongo --quiet"
else
    log_warn "容器内未找到 MongoDB shell 工具，跳过详细验证"
    echo ""
    log_info "可以使用以下命令手动验证："
    echo "  docker exec -it ${MONGO_CONTAINER} mongosh"
    echo "  或者"
    echo "  docker exec -it ${MONGO_CONTAINER} mongo"
    MONGO_SHELL=""
fi

if [ -n "$MONGO_SHELL" ]; then
    echo ""
    # 使用 MongoDB 统计命令验证
    docker exec ${MONGO_CONTAINER} sh -c "$MONGO_SHELL \
        -u ${MONGO_USERNAME} \
        -p ${MONGO_PASSWORD} \
        --authenticationDatabase admin \
        ${MONGO_DATABASE} \
        --eval 'db.stats()'" 2>/dev/null || log_warn "验证查询执行失败，但数据可能已成功导入"
fi

echo ""
log_info "迁移成功完成！"
echo ""
echo "下一步操作："
echo "  1. 启动应用服务: docker-compose up -d"
echo "  2. 查看服务状态: docker-compose ps"
echo "  3. 查看后端日志: docker-compose logs -f backend"
echo ""

# 询问是否启动完整服务
if confirm "是否启动完整应用服务？"; then
    log_info "启动应用服务..."
    docker-compose up -d
    sleep 5
    docker-compose ps
fi
