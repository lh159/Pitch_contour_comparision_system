#!/bin/bash

# 阿里云服务器环境配置脚本
# 在服务器上运行此脚本来配置环境

echo "🔧 配置阿里云服务器环境..."

# 1. 更新系统
echo "📦 更新系统包..."
apt update && apt upgrade -y

# 2. 安装Python和必要工具
echo "🐍 安装Python 3.9和开发工具..."
apt install -y python3.9 python3.9-pip python3.9-dev python3.9-venv
apt install -y build-essential ffmpeg git curl

# 3. 安装系统级音频库
echo "🎵 安装音频处理库..."
apt install -y libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0
apt install -y alsa-utils alsa-oss pulseaudio

# 4. 创建Python虚拟环境
echo "📂 创建虚拟环境..."
cd /opt/pitch_system
python3.9 -m venv venv
source venv/bin/activate

# 5. 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 6. 安装项目依赖
echo "📚 安装项目依赖..."
pip install -r requirements.txt

# 7. 创建必要目录
echo "📁 创建目录结构..."
mkdir -p data/{uploads,outputs,temp,cache}
mkdir -p src/{uploads,outputs,temp}
mkdir -p {uploads,outputs,temp,cache}

# 8. 配置防火墙
echo "🔥 配置防火墙..."
ufw allow 22      # SSH
ufw allow 5000    # Flask应用端口
ufw allow 80      # HTTP
ufw allow 443     # HTTPS

# 9. 创建系统服务文件
echo "🔧 创建系统服务..."
cat > /etc/systemd/system/pitch-system.service << EOF
[Unit]
Description=Pitch Comparison System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pitch_system
Environment=PATH=/opt/pitch_system/venv/bin
ExecStart=/opt/pitch_system/venv/bin/python web_interface.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 10. 启用服务
systemctl daemon-reload
systemctl enable pitch-system

echo ""
echo "✅ 服务器环境配置完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 编辑配置文件: cp config_template.py config.py && nano config.py"
echo "2. 启动服务: systemctl start pitch-system"
echo "3. 查看状态: systemctl status pitch-system"
echo "4. 查看日志: journalctl -u pitch-system -f"
echo ""
echo "🌐 服务将在以下地址可用:"
echo "   http://8.148.200.151:5000"
echo ""
echo "🔧 常用命令:"
echo "   重启服务: systemctl restart pitch-system"
echo "   停止服务: systemctl stop pitch-system"
echo "   查看日志: journalctl -u pitch-system"
