#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DashScope模块导入问题诊断脚本
专门用于排查云端服务器上dashscope模块导入失败的问题
"""

import sys
import os
import subprocess
import importlib.util
import site
from pathlib import Path

def print_separator(title):
    """打印分隔符"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def check_python_environment():
    """检查Python环境"""
    print_separator("Python环境信息")
    
    print(f"Python版本: {sys.version}")
    print(f"Python可执行文件路径: {sys.executable}")
    print(f"Python安装路径: {sys.prefix}")
    print(f"当前工作目录: {os.getcwd()}")
    
    print("\nPython模块搜索路径:")
    for i, path in enumerate(sys.path, 1):
        print(f"  {i}. {path}")
    
    print(f"\nsite-packages路径:")
    for path in site.getsitepackages():
        print(f"  - {path}")
    
    user_site = site.getusersitepackages()
    print(f"用户site-packages: {user_site}")

def check_pip_info():
    """检查pip信息"""
    print_separator("pip信息")
    
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                              capture_output=True, text=True)
        print(f"pip版本: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ 获取pip版本失败: {e}")
    
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True)
        installed_packages = result.stdout
        
        # 查找dashscope相关包
        dashscope_packages = []
        for line in installed_packages.split('\n'):
            if 'dashscope' in line.lower():
                dashscope_packages.append(line.strip())
        
        if dashscope_packages:
            print("✅ 找到dashscope相关包:")
            for pkg in dashscope_packages:
                print(f"  - {pkg}")
        else:
            print("❌ 未找到dashscope包")
            
    except Exception as e:
        print(f"❌ 获取包列表失败: {e}")

def check_dashscope_installation():
    """检查dashscope安装情况"""
    print_separator("DashScope安装检查")
    
    # 方法1: 使用importlib检查
    spec = importlib.util.find_spec("dashscope")
    if spec is None:
        print("❌ importlib.util.find_spec('dashscope') 返回 None")
        print("   这意味着Python找不到dashscope模块")
    else:
        print("✅ importlib找到dashscope模块")
        print(f"   模块路径: {spec.origin}")
        print(f"   包路径: {spec.submodule_search_locations}")
    
    # 方法2: 直接导入测试
    print("\n尝试导入dashscope...")
    try:
        import dashscope
        print("✅ 成功导入dashscope")
        print(f"   dashscope版本: {getattr(dashscope, '__version__', '未知')}")
        print(f"   dashscope路径: {dashscope.__file__}")
        
        # 测试子模块
        try:
            from dashscope.audio.asr import Transcription
            print("✅ 成功导入 dashscope.audio.asr.Transcription")
        except ImportError as e:
            print(f"❌ 导入 dashscope.audio.asr.Transcription 失败: {e}")
            
    except ImportError as e:
        print(f"❌ 导入dashscope失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        
        # 检查可能的原因
        print("\n可能的原因分析:")
        
        # 检查是否存在dashscope目录
        for path in sys.path:
            dashscope_path = Path(path) / 'dashscope'
            if dashscope_path.exists():
                print(f"✅ 找到dashscope目录: {dashscope_path}")
                
                # 检查__init__.py
                init_file = dashscope_path / '__init__.py'
                if init_file.exists():
                    print(f"✅ 存在 __init__.py: {init_file}")
                else:
                    print(f"❌ 缺少 __init__.py: {init_file}")
                
                # 检查权限
                if os.access(dashscope_path, os.R_OK):
                    print("✅ dashscope目录可读")
                else:
                    print("❌ dashscope目录不可读")
                break
        else:
            print("❌ 在所有Python路径中都未找到dashscope目录")

def check_environment_variables():
    """检查环境变量"""
    print_separator("环境变量检查")
    
    relevant_vars = [
        'PYTHONPATH', 'PATH', 'DASHSCOPE_API_KEY', 
        'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV'
    ]
    
    for var in relevant_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: 未设置")

def check_virtual_environment():
    """检查虚拟环境"""
    print_separator("虚拟环境检查")
    
    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 当前在虚拟环境中")
        print(f"   虚拟环境路径: {sys.prefix}")
        if 'VIRTUAL_ENV' in os.environ:
            print(f"   VIRTUAL_ENV: {os.environ['VIRTUAL_ENV']}")
    else:
        print("❌ 当前不在虚拟环境中")
        print("   建议使用虚拟环境来避免包冲突")

def check_file_permissions():
    """检查文件权限"""
    print_separator("文件权限检查")
    
    # 检查当前目录权限
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    print(f"可读: {os.access(current_dir, os.R_OK)}")
    print(f"可写: {os.access(current_dir, os.W_OK)}")
    print(f"可执行: {os.access(current_dir, os.X_OK)}")
    
    # 检查Python可执行文件权限
    python_exe = Path(sys.executable)
    print(f"\nPython可执行文件: {python_exe}")
    print(f"存在: {python_exe.exists()}")
    print(f"可执行: {os.access(python_exe, os.X_OK)}")

def suggest_solutions():
    """提供解决方案建议"""
    print_separator("解决方案建议")
    
    print("基于诊断结果，建议尝试以下解决方案：")
    print()
    print("1. 🔄 重新安装dashscope")
    print("   pip uninstall dashscope -y")
    print("   pip install dashscope --no-cache-dir")
    print()
    print("2. 🌐 使用国内镜像源")
    print("   pip install dashscope -i https://pypi.tuna.tsinghua.edu.cn/simple/")
    print()
    print("3. 🐍 创建新的虚拟环境")
    print("   python3 -m venv new_venv")
    print("   source new_venv/bin/activate")
    print("   pip install dashscope")
    print()
    print("4. 🔧 检查系统依赖")
    print("   apt update && apt install python3-dev build-essential")
    print()
    print("5. 🔍 手动指定Python路径")
    print("   export PYTHONPATH=/usr/local/lib/python3.10/dist-packages:$PYTHONPATH")
    print()
    print("6. 👤 检查用户权限")
    print("   如果以root用户安装，确保运行时也使用相同用户")

def run_installation_test():
    """运行安装测试"""
    print_separator("安装测试")
    
    print("尝试重新安装dashscope...")
    try:
        # 卸载
        result = subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'dashscope', '-y'], 
                              capture_output=True, text=True)
        print("卸载结果:", "成功" if result.returncode == 0 else "失败")
        
        # 重新安装
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'dashscope', '--no-cache-dir'], 
                              capture_output=True, text=True)
        print("安装结果:", "成功" if result.returncode == 0 else "失败")
        
        if result.returncode != 0:
            print("安装错误输出:")
            print(result.stderr)
        
        # 测试导入
        print("\n测试导入...")
        result = subprocess.run([sys.executable, '-c', 'import dashscope; print("导入成功")'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 导入测试成功")
        else:
            print("❌ 导入测试失败")
            print("错误:", result.stderr)
            
    except Exception as e:
        print(f"安装测试异常: {e}")

def main():
    """主函数"""
    print("🚀 DashScope模块导入问题诊断工具")
    print("此工具将帮助诊断云端服务器上dashscope导入失败的问题")
    
    # 运行所有检查
    check_python_environment()
    check_pip_info()
    check_dashscope_installation()
    check_environment_variables()
    check_virtual_environment()
    check_file_permissions()
    
    # 询问是否运行安装测试
    print("\n" + "="*60)
    response = input("是否尝试重新安装dashscope? (y/N): ")
    if response.lower() in ['y', 'yes']:
        run_installation_test()
    
    suggest_solutions()
    
    print("\n" + "="*60)
    print("🎯 诊断完成")
    print("请将以上信息发送给技术支持以获得进一步帮助")
    print("="*60)

if __name__ == "__main__":
    main()
