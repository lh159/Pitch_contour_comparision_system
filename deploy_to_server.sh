#!/bin/bash

# 音高曲线比对系统 - 服务器部署脚本
# 使用方法: ./deploy_to_server.sh

# 服务器配置
SERVER_IP="8.148.200.151"
SERVER_USER="root"  # 请修改为你的用户名
SERVER_PATH="/opt/pitch_comparison_system"  # 服务器上的目标路径

# 项目本地路径
LOCAL_PATH="/Users/lapulasiyao/Desktop/音高曲线比对系统"

echo "🚀 开始部署音高曲线比对系统到阿里云服务器..."

# 检查SSH连接
echo "📡 测试SSH连接..."
if ! ssh -o ConnectTimeout=10 -i ~/.ssh/aliyun_rsa $SERVER_USER@$SERVER_IP "echo '连接成功'"; then
    echo "❌ SSH连接失败，请检查:"
    echo "   1. 服务器IP地址是否正确"
    echo "   2. SSH密钥是否配置"
    echo "   3. 服务器防火墙是否开放22端口"
    exit 1
fi

# 在服务器上创建目标目录
echo "📁 创建服务器目录..."
ssh -i ~/.ssh/aliyun_rsa $SERVER_USER@$SERVER_IP "mkdir -p $SERVER_PATH"

# 使用rsync同步文件（排除不必要的文件）
echo "📦 同步项目文件..."
rsync -avz --progress \
    --exclude='__pycache__/' \
    --exclude='*.py[cod]' \
    --exclude='.DS_Store' \
    --exclude='.git/' \
    --exclude='.gitignore' \
    --exclude='venv/' \
    --exclude='env/' \
    --exclude='.venv/' \
    --exclude='uploads/' \
    --exclude='outputs/' \
    --exclude='temp/' \
    --exclude='cache/' \
    --exclude='data/cache/' \
    --exclude='data/temp/' \
    --exclude='data/outputs/' \
    --exclude='src/temp/' \
    --exclude='src/uploads/' \
    --exclude='src/outputs/' \
    --exclude='*.wav' \
    --exclude='*.mp3' \
    --exclude='*.m4a' \
    --exclude='*.flac' \
    --exclude='*.ogg' \
    --exclude='*.png' \
    --exclude='*.jpg' \
    --exclude='*.jpeg' \
    --exclude='*.gif' \
    --exclude='config.py' \
    --exclude='*.key' \
    --exclude='api_keys.txt' \
    --exclude='.env*' \
    --exclude='models/' \
    --exclude='*.pth' \
    --exclude='*.pt' \
    --exclude='*.ckpt' \
    --exclude='*.h5' \
    --exclude='all_wav_data*/' \
    --exclude='test_output*/' \
    --exclude='*.log' \
    --exclude='logs/' \
    --exclude='.cache/' \
    --exclude='*.cache' \
    --exclude='*.tmp' \
    --exclude='*.temp' \
    -e "ssh -i ~/.ssh/aliyun_rsa" \
    "$LOCAL_PATH/" $SERVER_USER@$SERVER_IP:$SERVER_PATH/

if [ $? -eq 0 ]; then
    echo "✅ 文件同步完成！"
else
    echo "❌ 文件同步失败！"
    exit 1
fi

# 在服务器上设置权限
echo "🔐 设置文件权限..."
ssh -i ~/.ssh/aliyun_rsa $SERVER_USER@$SERVER_IP "chmod +x $SERVER_PATH/*.py && chmod +x $SERVER_PATH/*.sh"

# 显示部署完成信息
echo ""
echo "🎉 部署完成！"
echo "📍 服务器路径: $SERVER_PATH"
echo "🔗 服务器IP: $SERVER_IP"
echo ""
echo "下一步操作："
echo "1. SSH连接到服务器: ssh -i ~/.ssh/aliyun_rsa $SERVER_USER@$SERVER_IP"
echo "2. 进入项目目录: cd $SERVER_PATH"
echo "3. 安装依赖: python3 install_dependencies.py"
echo "4. 配置环境: 复制并编辑 config_template.py 为 config.py"
echo "5. 启动服务: python3 web_interface.py"
echo ""
echo "🔧 如需更新代码，直接运行此脚本即可"
