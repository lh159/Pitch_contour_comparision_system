#!/usr/bin/env python3
"""
安全安装requirements.txt依赖
对于可能失败的包，会跳过并继续安装其他包
"""

import subprocess
import sys
import os

def run_pip_install(package, description=""):
    """安全安装单个包"""
    print(f"📦 安装 {package}...")
    if description:
        print(f"   {description}")
    
    try:
        cmd = [sys.executable, "-m", "pip", "install", package, "--no-cache-dir"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {package} 安装成功")
            return True
        else:
            print(f"❌ {package} 安装失败: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {package} 安装超时")
        return False
    except Exception as e:
        print(f"❌ {package} 安装异常: {e}")
        return False

def install_requirements_safe():
    """安全安装所有依赖"""
    print("🚀 安全安装音高曲线比对系统依赖")
    print("=" * 50)
    
    # 检查虚拟环境
    if os.environ.get('VIRTUAL_ENV'):
        print(f"✅ 虚拟环境: {os.environ.get('VIRTUAL_ENV')}")
    else:
        print("⚠️ 未检测到虚拟环境")
    
    # 核心依赖 - 必须成功
    core_packages = [
        ("python-dotenv>=0.19.0", "环境配置文件支持"),
        ("flask>=2.0.0", "Web框架"),
        ("flask-cors>=3.0.10", "跨域支持"),
        ("requests>=2.25.0", "HTTP请求库"),
        ("numpy>=1.21.0", "数值计算"),
    ]
    
    # 重要依赖 - 尽量成功
    important_packages = [
        ("matplotlib>=3.5.0", "图形绘制"),
        ("scipy>=1.7.0", "科学计算"),
        ("librosa>=0.8.1", "音频处理"),
        ("scikit-learn>=1.0.0", "机器学习"),
        ("pydub>=0.25.1", "音频格式处理"),
        ("jieba>=0.42.1", "中文分词"),
        ("dashscope>=1.0.0", "阿里云语音服务"),
    ]
    
    # 可选依赖 - 失败也无妨
    optional_packages = [
        ("parselmouth>=0.4.2", "Praat音频分析"),
        ("funasr>=1.0.0", "达摩院语音识别"),
        ("edge-tts>=6.1.0", "Edge TTS语音合成"),
        ("dtaidistance>=2.3.4", "时间序列距离计算"),
        ("soundfile>=0.10.3.post1", "音频文件IO"),
        ("audioread>=2.1.9", "音频格式支持"),
        ("resampy>=0.2.2", "音频重采样"),
        ("pandas>=1.3.0", "数据处理"),
        ("seaborn>=0.11.0", "数据可视化"),
        ("flask-socketio>=5.3.0", "WebSocket支持"),
        ("eventlet>=0.33.0", "异步网络库"),
        ("pypinyin>=0.44.0", "拼音转换"),
        ("psutil>=5.8.0", "系统监控"),
        ("colorlog>=6.6.0", "彩色日志"),
    ]
    
    # 统计结果
    core_success = 0
    important_success = 0
    optional_success = 0
    
    print("\n🔧 安装核心依赖...")
    print("-" * 30)
    for package, desc in core_packages:
        if run_pip_install(package, desc):
            core_success += 1
    
    print(f"\n核心依赖安装结果: {core_success}/{len(core_packages)}")
    
    if core_success < len(core_packages):
        print("❌ 核心依赖安装不完整，系统可能无法正常运行")
        return False
    
    print("\n📦 安装重要依赖...")
    print("-" * 30)
    for package, desc in important_packages:
        if run_pip_install(package, desc):
            important_success += 1
    
    print(f"\n重要依赖安装结果: {important_success}/{len(important_packages)}")
    
    print("\n🎁 安装可选依赖...")
    print("-" * 30)
    for package, desc in optional_packages:
        if run_pip_install(package, desc):
            optional_success += 1
    
    print(f"\n可选依赖安装结果: {optional_success}/{len(optional_packages)}")
    
    # 最终测试
    print("\n🧪 测试关键模块导入...")
    print("-" * 30)
    
    test_modules = [
        ("flask", "from flask import Flask"),
        ("dotenv", "from dotenv import load_dotenv"),
        ("numpy", "import numpy"),
        ("requests", "import requests"),
        ("config", "from config import Config"),
    ]
    
    test_success = 0
    for name, import_cmd in test_modules:
        try:
            subprocess.run([sys.executable, "-c", import_cmd], 
                         check=True, capture_output=True, timeout=10)
            print(f"✅ {name} 导入成功")
            test_success += 1
        except:
            print(f"❌ {name} 导入失败")
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 安装总结")
    print("=" * 50)
    print(f"核心依赖: {core_success}/{len(core_packages)} ({'✅' if core_success == len(core_packages) else '❌'})")
    print(f"重要依赖: {important_success}/{len(important_packages)} ({'✅' if important_success >= len(important_packages)*0.7 else '⚠️'})")
    print(f"可选依赖: {optional_success}/{len(optional_packages)}")
    print(f"模块测试: {test_success}/{len(test_modules)} ({'✅' if test_success >= 4 else '❌'})")
    
    if core_success == len(core_packages) and test_success >= 4:
        print("\n🎉 依赖安装完成！可以启动系统:")
        print("python web_interface.py")
        return True
    else:
        print("\n⚠️ 依赖安装不完整，请检查错误信息")
        return False

if __name__ == "__main__":
    success = install_requirements_safe()
    sys.exit(0 if success else 1)
