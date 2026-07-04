#!/bin/bash
# G1小智助手安装脚本
# 用于设置开机自启动

echo "========================================"
echo "G1小智助手 - 安装开机自启动服务"
echo "========================================"

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "错误: 请使用sudo运行此脚本"
    echo "用法: sudo ./install_service.sh"
    exit 1
fi

# 获取当前用户
CURRENT_USER=${SUDO_USER:-unitree}
echo "当前用户: $CURRENT_USER"

# 项目路径
PROJECT_DIR="/home/unitree/tang/WK/PythonProject/py-xiaozhi-main"
SERVICE_FILE="$PROJECT_DIR/g1-xiaozhi.service"
START_SCRIPT="$PROJECT_DIR/start_g1.sh"

# 检查文件是否存在
if [ ! -f "$SERVICE_FILE" ]; then
    echo "错误: 找不到服务文件 $SERVICE_FILE"
    exit 1
fi

if [ ! -f "$START_SCRIPT" ]; then
    echo "错误: 找不到启动脚本 $START_SCRIPT"
    exit 1
fi

# 设置启动脚本执行权限
chmod +x "$START_SCRIPT"
echo "✓ 启动脚本权限已设置"

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"
chown -R $CURRENT_USER:$CURRENT_USER "$PROJECT_DIR/logs"
echo "✓ 日志目录已创建"

# 安装systemd服务文件
SYSTEMD_DIR="/etc/systemd/system"
cp "$SERVICE_FILE" "$SYSTEMD_DIR/g1-xiaozhi.service"
echo "✓ 服务文件已安装到 $SYSTEMD_DIR"

# 重新加载systemd配置
systemctl daemon-reload
echo "✓ systemd配置已重新加载"

# 启用服务（开机自启动）
systemctl enable g1-xiaozhi.service
echo "✓ 服务已设置为开机自启动"

# 询问是否立即启动服务
echo ""
echo "是否立即启动服务？(y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    systemctl start g1-xiaozhi.service
    echo "✓ 服务已启动"
    
    # 显示服务状态
    echo ""
    echo "服务状态:"
    systemctl status g1-xiaozhi.service --no-pager -l
fi

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "常用命令:"
echo "  启动服务: sudo systemctl start g1-xiaozhi"
echo "  停止服务: sudo systemctl stop g1-xiaozhi"
echo "  重启服务: sudo systemctl restart g1-xiaozhi"
echo "  查看状态: sudo systemctl status g1-xiaozhi"
echo "  查看日志: sudo journalctl -u g1-xiaozhi -f"
echo "  禁用自启动: sudo systemctl disable g1-xiaozhi"
echo "  启用自启动: sudo systemctl enable g1-xiaozhi"
echo ""
echo "应用日志位置:"
echo "  $PROJECT_DIR/logs/startup.log"
echo ""
