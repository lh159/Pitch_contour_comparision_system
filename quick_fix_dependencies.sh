#!/bin/bash
# 快速修复云端服务器依赖问题

echo "🔧 快速修复音高曲线比对系统依赖问题"
echo "=================================="

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 检测到虚拟环境: $VIRTUAL_ENV"
else
    echo "⚠️ 未检测到虚拟环境，请先激活:"
    echo "source /root/Pitch_contour_comparision_system/venv_fix/bin/activate"
    exit 1
fi

echo ""
echo "📦 安装基础依赖包..."

# 升级pip
echo "1. 升级pip..."
pip install --upgrade pip --no-cache-dir

# 安装最关键的依赖
echo "2. 安装Web框架依赖..."
pip install flask>=2.0.0 --no-cache-dir
pip install flask-cors>=3.0.10 --no-cache-dir
pip install python-dotenv>=0.19.0 --no-cache-dir
pip install requests>=2.25.0 --no-cache-dir

echo "3. 安装基础科学计算库..."
pip install numpy>=1.21.0 --no-cache-dir
pip install scipy>=1.7.0 --no-cache-dir
pip install matplotlib>=3.5.0 --no-cache-dir

echo "4. 安装音频处理库..."
pip install librosa>=0.8.1 --no-cache-dir
pip install pydub>=0.25.1 --no-cache-dir

echo "5. 安装其他工具库..."
pip install scikit-learn>=1.0.0 --no-cache-dir
pip install jieba>=0.42.1 --no-cache-dir

echo ""
echo "🧪 测试关键模块导入..."

# 测试导入
python -c "from flask import Flask; print('✅ Flask导入成功')" || echo "❌ Flask导入失败"
python -c "from dotenv import load_dotenv; print('✅ python-dotenv导入成功')" || echo "❌ python-dotenv导入失败"
python -c "import numpy; print('✅ numpy导入成功')" || echo "❌ numpy导入失败"
python -c "import dashscope; print('✅ dashscope导入成功')" || echo "❌ dashscope导入失败"

echo ""
echo "🚀 尝试启动web_interface.py..."
echo "=================================="

# 尝试启动
python -c "
try:
    from config import Config
    print('✅ config.py导入成功')
    print('📊 配置加载完成，可以启动Web界面')
except Exception as e:
    print(f'❌ config.py导入失败: {e}')
    print('需要进一步排查问题')
"

echo ""
echo "📋 修复完成！现在可以尝试:"
echo "python web_interface.py"
