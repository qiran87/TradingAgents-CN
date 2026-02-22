#!/bin/bash
###############################################################################
# MongoDB 跨平台迁移脚本
# 用途: 将 macOS Docker 中的 MongoDB 数据迁移到 Linux 服务器
###############################################################################

set -e

# 配置
BACKUP_DIR="${HOME}/mongodb_backup_$(date +%Y%m%d_%H%M%S)"
CONTAINER_NAME="tradingagents-mongodb"
MONGO_USER="admin"
MONGO_PASSWORD="tradingagents123"
MONGO_DB="tradingagents"
MONGO_URI="mongodb://${MONGO_USER}:${MONGO_PASSWORD}@localhost:27017/${MONGO_DB}?authSource=admin"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否运行
check_docker() {
    if ! docker ps &> /dev/null; then
        log_error "Docker 未运行，请先启动 Docker Desktop"
        exit 1
    fi
    log_info "Docker 运行正常"
}

# 检查 MongoDB 容器
check_mongo_container() {
    if ! docker ps | grep -q "${CONTAINER_NAME}"; then
        log_error "MongoDB 容器 ${CONTAINER_NAME} 未运行"
        exit 1
    fi
    log_info "MongoDB 容器运行正常"
}

# 导出数据
export_data() {
    log_info "开始导出 MongoDB 数据..."

    mkdir -p "${BACKUP_DIR}"

    # 方法 1: mongodump (推荐)
    log_info "使用 mongodump 导出数据..."
    docker exec ${CONTAINER_NAME} mongodump \
        --uri="${MONGO_URI}" \
        --archive=/data/mongodb_backup \
        --gzip

    docker cp ${CONTAINER_NAME}:/data/mongodb_backup "${BACKUP_DIR}/"

    # 方法 2: 导出 Volume (备用)
    log_info "导出 Docker Volume..."
    docker run --rm \
        -v tradingagents_mongodb_data:/data \
        -v "${BACKUP_DIR}":/backup \
        alpine tar czf /backup/mongodb_volume.tar.gz -C /data .

    log_info "数据导出完成: ${BACKUP_DIR}"
    ls -lh "${BACKUP_DIR}"
}

# 验证备份
verify_backup() {
    log_info "验证备份文件..."

    if [ -f "${BACKUP_DIR}/mongodb_backup" ]; then
        local size=$(du -h "${BACKUP_DIR}/mongodb_backup" | cut -f1)
        log_info "✓ mongodump 备份文件: ${size}"
    else
        log_error "✗ mongodump 备份文件不存在"
        return 1
    fi

    if [ -f "${BACKUP_DIR}/mongodb_volume.tar.gz" ]; then
        local size=$(du -h "${BACKUP_DIR}/mongodb_volume.tar.gz" | cut -f1)
        log_info "✓ Volume 备份文件: ${size}"
    else
        log_warn "✗ Volume 备份文件不存在"
    fi
}

# 生成 Linux 导入脚本
generate_import_script() {
    local import_script="${BACKUP_DIR}/import_to_linux.sh"

    cat > "${import_script}" <<'EOF'
#!/bin/bash
###############################################################################
# MongoDB 数据导入脚本 (Linux)
# 在目标 Linux 服务器上运行此脚本
###############################################################################

set -e

# 配置 (根据实际情况修改)
MONGO_USER="admin"
MONGO_PASSWORD="tradingagents123"
MONGO_DB="tradingagents"
MONGO_CONTAINER="mongodb"
BACKUP_DIR="$(pwd)"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 方法 1: mongorestore (推荐)
restore_with_mongorestore() {
    log_info "使用 mongorestore 导入数据..."

    if [ ! -f "mongodb_backup" ]; then
        log_error "备份文件 mongodb_backup 不存在"
        exit 1
    fi

    cat mongodb_backup | docker exec -i ${MONGO_CONTAINER} mongorestore \
        --uri="mongodb://${MONGO_USER}:${MONGO_PASSWORD}@localhost:27017/${MONGO_DB}?authSource=admin" \
        --archive \
        --gzip

    log_info "✓ 数据导入完成"
}

# 方法 2: Volume 恢复 (备用)
restore_volume() {
    log_info "使用 Volume 恢复数据..."

    if [ ! -f "mongodb_volume.tar.gz" ]; then
        log_error "备份文件 mongodb_volume.tar.gz 不存在"
        exit 1
    fi

    docker volume create tradingagents_mongodb_data

    docker run --rm \
        -v tradingagents_mongodb_data:/data \
        -v "${BACKUP_DIR}":/backup \
        alpine sh -c "cd /data && tar xzf /backup/mongodb_volume.tar.gz"

    log_info "✓ Volume 恢复完成"
}

# 主流程
log_info "MongoDB 数据导入脚本"
echo ""
echo "选择导入方式:"
echo "  1) mongorestore (推荐，逻辑备份)"
echo "  2) Volume 恢复 (物理备份)"
echo ""
read -p "请选择 [1-2]: " choice

case $choice in
    1)
        restore_with_mongorestore
        ;;
    2)
        restore_volume
        ;;
    *)
        log_error "无效选择"
        exit 1
        ;;
esac

log_info "所有操作完成！"
EOF

    chmod +x "${import_script}"

    log_info "已生成 Linux 导入脚本: ${import_script}"
}

# 显示统计信息
show_stats() {
    log_info "数据库统计信息..."

    echo ""
    echo "数据库列表:"
    docker exec ${CONTAINER_NAME} mongo \
        -u ${MONGO_USER} -p ${MONGO_PASSWORD} \
        --authenticationDatabase admin \
        --quiet --eval "db.adminCommand('listDatabases').databases.forEach(d => print('  - ' + d.name + ' (' + d.sizeOnDisk + ')'))"

    echo ""
    echo "tradingagents 数据库集合:"
    docker exec ${CONTAINER_NAME} mongo \
        -u ${MONGO_USER} -p ${MONGO_PASSWORD} \
        --authenticationDatabase admin \
        tradingagents --quiet --eval "db.getCollectionNames().forEach(c => print('  - ' + c))"
}

# 主流程
main() {
    log_info "=========================================="
    log_info "MongoDB 跨平台迁移工具"
    log_info "=========================================="
    echo ""

    check_docker
    check_mongo_container
    show_stats

    echo ""
    read -p "是否开始导出数据? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "已取消"
        exit 0
    fi

    export_data
    verify_backup
    generate_import_script

    echo ""
    log_info "=========================================="
    log_info "导出完成!"
    log_info "=========================================="
    echo ""
    log_info "备份目录: ${BACKUP_DIR}"
    log_info ""
    log_info "下一步操作:"
    log_info "  1. 将备份目录复制到 Linux 服务器:"
    log_info "     scp -r ${BACKUP_DIR} user@linux-server:/tmp/"
    log_info ""
    log_info "  2. 在 Linux 服务器上运行导入脚本:"
    log_info "     cd ${BACKUP_DIR}"
    log_info "     ./import_to_linux.sh"
    echo ""
}

main "$@"
