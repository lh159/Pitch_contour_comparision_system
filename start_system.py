# -*- coding: utf-8 -*-
"""
系统启动脚本
检查依赖并启动音高曲线比对系统
"""
import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """检查关键依赖是否已安装"""
    required_modules = [
        'parselmouth', 'numpy', 'matplotlib', 'flask', 'scipy'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    return missing_modules

def install_dependencies():
    """安装缺失的依赖"""
    print("🔧 检测到缺失依赖，正在安装...")
    
    try:
        result = subprocess.run([sys.executable, 'install_dependencies.py'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"安装失败: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    directories = ['uploads', 'outputs', 'temp', 'static', 'templates']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def start_web_server():
    """启动Web服务器"""
    try:
        print("🚀 启动音高曲线比对系统...")
        print("请等待系统初始化...")
        
        # 启动Flask应用
        process = subprocess.Popen([sys.executable, 'web_interface.py'])
        
        # 等待服务器启动
        time.sleep(3)
        
        # 自动打开浏览器
        url = "http://localhost:5000"
        print(f"🌐 系统地址: {url}")
        
        try:
            webbrowser.open(url)
            print("✅ 已自动打开浏览器")
        except:
            print("请手动在浏览器中访问上述地址")
        
        print("\n" + "="*50)
        print("音高曲线比对系统已启动！")
        print("=" * 50)
        print("📝 使用说明:")
        print("  1. 在网页中输入要练习的中文词汇")
        print("  2. 点击'生成标准发音'获取标准音频")
        print("  3. 点击'开始录音'录制您的发音")
        print("  4. 点击'开始比对分析'查看结果")
        print("\n💡 提示:")
        print("  - 支持的词汇: 你好、早上好、欢迎光临等")
        print("  - 建议在安静环境中录音")
        print("  - 按Ctrl+C可停止系统")
        print("=" * 50)
        
        # 等待用户中断
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n\n👋 正在关闭系统...")
            process.terminate()
            print("✅ 系统已关闭")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def main():
    """主函数"""
    print("音高曲线比对系统 - 启动器")
    print("=" * 50)
    
    # 检查依赖
    missing = check_dependencies()
    if missing:
        print(f"⚠️  缺少依赖: {', '.join(missing)}")
        
        response = input("是否自动安装缺失的依赖? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            if not install_dependencies():
                print("❌ 依赖安装失败，请手动运行 python install_dependencies.py")
                return
        else:
            print("请先安装依赖: python install_dependencies.py")
            return
    
    # 检查关键文件
    required_files = [
        'web_interface.py', 'config.py', 'tts_module.py', 
        'pitch_comparison.py', 'scoring_algorithm.py', 'visualization.py'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"❌ 缺少关键文件: {', '.join(missing_files)}")
        print("请确保所有系统文件都已下载")
        return
    
    # 创建目录
    create_directories()
    
    # 启动系统
    start_web_server()

if __name__ == '__main__':
    main()
