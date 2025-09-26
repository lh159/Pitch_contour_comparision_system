#!/usr/bin/env python3
"""
云端服务器依赖安装脚本
自动安装音高曲线比对系统所需的所有依赖包
"""

import subprocess
import sys
import os

def run_command(cmd, description=""):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("✅ 执行成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
            return True, result.stdout
        else:
            print("❌ 执行失败")
            if result.stderr.strip():
                print(f"错误: {result.stderr.strip()}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
        return False, "命令执行超时"
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False, str(e)

def check_virtual_env():
    """检查是否在虚拟环境中"""
    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path:
        print("⚠️ 警告：未检测到虚拟环境")
        print("建议先激活虚拟环境:")
        print("source /root/Pitch_contour_comparision_system/venv_fix/bin/activate")
        return False
    else:
        print(f"✅ 检测到虚拟环境: {venv_path}")
        return True

def install_dependencies():
    """安装依赖包"""
    print("🚀 云端服务器依赖安装工具")
    print("此工具将安装音高曲线比对系统所需的所有依赖包")
    print("=" * 60)
    
    # 检查虚拟环境
    print("步骤 1: 检查虚拟环境")
    print("=" * 60)
    is_venv = check_virtual_env()
    
    # 获取Python路径
    python_cmd = sys.executable
    pip_cmd = f"{python_cmd} -m pip"
    
    print(f"Python路径: {python_cmd}")
    print(f"Pip命令: {pip_cmd}")
    
    # 步骤2: 升级pip
    print("\n步骤 2: 升级pip")
    print("=" * 60)
    success, _ = run_command(f"{pip_cmd} install --upgrade pip", "升级pip到最新版本")
    if not success:
        print("⚠️ pip升级失败，继续安装依赖...")
    
    # 步骤3: 安装基础Web依赖
    print("\n步骤 3: 安装Web框架依赖")
    print("=" * 60)
    web_packages = [
        "flask>=2.0.0",
        "flask-cors>=3.0.10", 
        "flask-socketio>=5.3.0",
        "requests>=2.25.0",
        "python-dotenv>=0.19.0"
    ]
    
    for package in web_packages:
        success, _ = run_command(f"{pip_cmd} install '{package}' --no-cache-dir", f"安装 {package}")
        if not success:
            print(f"⚠️ {package} 安装失败，继续安装其他包...")
    
    # 步骤4: 安装音频处理依赖
    print("\n步骤 4: 安装音频处理依赖")
    print("=" * 60)
    audio_packages = [
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "matplotlib>=3.5.0",
        "librosa>=0.8.1",
        "pydub>=0.25.1",
        "parselmouth>=0.4.2"
    ]
    
    for package in audio_packages:
        success, _ = run_command(f"{pip_cmd} install '{package}' --no-cache-dir", f"安装 {package}")
        if not success:
            print(f"⚠️ {package} 安装失败，继续安装其他包...")
    
    # 步骤5: 安装机器学习依赖
    print("\n步骤 5: 安装机器学习依赖")
    print("=" * 60)
    ml_packages = [
        "scikit-learn>=1.0.0",
        "dtaidistance>=2.3.4"
    ]
    
    for package in ml_packages:
        success, _ = run_command(f"{pip_cmd} install '{package}' --no-cache-dir", f"安装 {package}")
        if not success:
            print(f"⚠️ {package} 安装失败，继续安装其他包...")
    
    # 步骤6: 安装TTS和其他工具
    print("\n步骤 6: 安装TTS和工具库")
    print("=" * 60)
    tool_packages = [
        "edge-tts>=6.1.0",
        "pyttsx3>=2.90",
        "jieba>=0.42.1"
    ]
    
    for package in tool_packages:
        success, _ = run_command(f"{pip_cmd} install '{package}' --no-cache-dir", f"安装 {package}")
        if not success:
            print(f"⚠️ {package} 安装失败，继续安装其他包...")
    
    # 步骤7: 尝试安装funasr（可能失败）
    print("\n步骤 7: 安装FunASR（可选）")
    print("=" * 60)
    success, _ = run_command(f"{pip_cmd} install funasr --no-cache-dir", "安装 funasr")
    if not success:
        print("⚠️ funasr安装失败，这是正常的，系统仍可运行")
    
    # 步骤8: 从requirements.txt安装剩余依赖
    print("\n步骤 8: 从requirements.txt安装剩余依赖")
    print("=" * 60)
    if os.path.exists("requirements.txt"):
        success, _ = run_command(f"{pip_cmd} install -r requirements.txt --no-cache-dir", "从requirements.txt安装依赖")
        if not success:
            print("⚠️ requirements.txt安装部分失败，继续测试...")
    else:
        print("⚠️ requirements.txt文件不存在")
    
    # 步骤9: 测试关键导入
    print("\n步骤 9: 测试关键模块导入")
    print("=" * 60)
    
    test_imports = [
        ("flask", "from flask import Flask"),
        ("dashscope", "import dashscope"),
        ("numpy", "import numpy"),
        ("matplotlib", "import matplotlib"),
        ("librosa", "import librosa"),
        ("scipy", "import scipy")
    ]
    
    success_count = 0
    total_count = len(test_imports)
    
    for name, import_cmd in test_imports:
        success, _ = run_command(f"{python_cmd} -c \"{import_cmd}; print('✅ {name}导入成功')\"", f"测试{name}导入")
        if success:
            success_count += 1
    
    # 最终结果
    print("\n" + "=" * 60)
    print("📊 安装结果总结")
    print("=" * 60)
    print(f"成功导入模块: {success_count}/{total_count}")
    
    if success_count >= 4:  # 至少4个核心模块成功
        print("🎉 依赖安装基本完成！")
        print("\n📝 下一步:")
        print("1. 测试启动Web界面: python web_interface.py")
        print("2. 如果遇到问题，检查具体的错误信息")
        print("3. 可能需要手动安装个别失败的包")
        
        # 创建启动脚本
        create_startup_script(python_cmd)
        
    else:
        print("⚠️ 多个核心依赖安装失败，请检查网络连接和权限")
        print("建议手动安装失败的包或联系管理员")

def create_startup_script(python_cmd):
    """创建启动脚本"""
    startup_script = f"""#!/bin/bash
# 音高曲线比对系统启动脚本

echo "🚀 启动音高曲线比对系统"

# 激活虚拟环境（如果需要）
if [ -f "venv_fix/bin/activate" ]; then
    echo "激活虚拟环境..."
    source venv_fix/bin/activate
fi

# 设置Python路径（如果需要）
if [ -f "set_pythonpath.sh" ]; then
    echo "设置Python路径..."
    source set_pythonpath.sh
fi

# 启动Web界面
echo "启动Web界面..."
{python_cmd} web_interface.py
"""
    
    with open("start_system.sh", "w", encoding="utf-8") as f:
        f.write(startup_script)
    
    # 给脚本执行权限
    os.chmod("start_system.sh", 0o755)
    print("✅ 已创建启动脚本: start_system.sh")
    print("使用方法: ./start_system.sh")

if __name__ == "__main__":
    install_dependencies()
