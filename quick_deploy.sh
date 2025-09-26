#!/bin/bash

# 快速部署脚本 - 音高曲线比对系统
# 使用方法: ./quick_deploy.sh

SERVER_IP="8.148.200.151"
SERVER_USER="root"  # 请根据实际情况修改用户名

echo "🚀 快速部署到阿里云服务器..."

# 方法1: 使用rsync (推荐)
echo "📦 使用rsync同步..."
rsync -avz --progress \
    --exclude-from='.gitignore' \
    --exclude='.git/' \
    --exclude='third_party/' \
    . $SERVER_USER@$SERVER_IP:/opt/pitch_system/

echo "✅ 部署完成！接下来请SSH到服务器进行环境配置"
echo "ssh $SERVER_USER@$SERVER_IP"
