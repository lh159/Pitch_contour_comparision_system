#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端服务器DashScope问题修复脚本
专门解决云端服务器上dashscope导入失败的问题
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def print_step(step, description):
    """打印步骤"""
    print(f"\n{'='*60}")
    print(f"步骤 {step}: {description}")
    print('='*60)

def run_command(cmd, description=""):
    """运行命令并返回结果"""
    print(f"🔧 {description}")
    print(f"执行命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 执行成功")
            if result.stdout.strip():
                print("输出:", result.stdout.strip())
        else:
            print("❌ 执行失败")
            print("错误:", result.stderr.strip())
        
        return result.returncode == 0, result
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False, None

def check_current_environment():
    """检查当前环境"""
    print_step(1, "检查当前环境")
    
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"工作目录: {os.getcwd()}")
    
    # 检查是否为root用户
    if os.geteuid() == 0:
        print("⚠️ 当前以root用户运行")
    else:
        print(f"👤 当前用户: {os.getenv('USER', 'unknown')}")
    
    # 检查虚拟环境
    if 'VIRTUAL_ENV' in os.environ:
        print(f"🐍 虚拟环境: {os.environ['VIRTUAL_ENV']}")
    else:
        print("⚠️ 未使用虚拟环境")

def clean_python_cache():
    """清理Python缓存"""
    print_step(2, "清理Python缓存")
    
    # 清理__pycache__
    success, _ = run_command("find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true", 
                           "清理__pycache__目录")
    
    # 清理.pyc文件
    success, _ = run_command("find . -name '*.pyc' -delete 2>/dev/null || true", 
                           "清理.pyc文件")
    
    # 清理pip缓存
    success, _ = run_command([sys.executable, '-m', 'pip', 'cache', 'purge'], 
                           "清理pip缓存")

def uninstall_dashscope():
    """卸载现有的dashscope"""
    print_step(3, "卸载现有的dashscope")
    
    success, _ = run_command([sys.executable, '-m', 'pip', 'uninstall', 'dashscope', '-y'], 
                           "卸载dashscope")
    
    # 检查是否还有残留
    success, result = run_command([sys.executable, '-c', 'import dashscope'], 
                                 "检查是否完全卸载")
    if success:
        print("⚠️ dashscope仍然可以导入，可能有残留")
    else:
        print("✅ dashscope已完全卸载")

def install_system_dependencies():
    """安装系统依赖"""
    print_step(4, "安装系统依赖")
    
    # 检查是否为Ubuntu/Debian系统
    if shutil.which('apt'):
        commands = [
            "apt update",
            "apt install -y python3-dev build-essential",
            "apt install -y libffi-dev libssl-dev",
            "apt install -y pkg-config"
        ]
        
        for cmd in commands:
            success, _ = run_command(cmd, f"执行: {cmd}")
    
    # 检查是否为CentOS/RHEL系统
    elif shutil.which('yum'):
        commands = [
            "yum update -y",
            "yum groupinstall -y 'Development Tools'",
            "yum install -y python3-devel libffi-devel openssl-devel"
        ]
        
        for cmd in commands:
            success, _ = run_command(cmd, f"执行: {cmd}")
    
    else:
        print("⚠️ 未识别的系统类型，跳过系统依赖安装")

def create_virtual_environment():
    """创建虚拟环境"""
    print_step(5, "创建虚拟环境")
    
    if 'VIRTUAL_ENV' in os.environ:
        print("✅ 已在虚拟环境中，跳过创建")
        return True
    
    venv_path = Path.cwd() / 'venv_fix'
    
    if venv_path.exists():
        print("🗑️ 删除现有虚拟环境")
        shutil.rmtree(venv_path)
    
    success, _ = run_command([sys.executable, '-m', 'venv', str(venv_path)], 
                           "创建新虚拟环境")
    
    if success:
        print(f"✅ 虚拟环境已创建: {venv_path}")
        print("⚠️ 请激活虚拟环境后重新运行此脚本:")
        print(f"   source {venv_path}/bin/activate")
        print(f"   python {__file__}")
        return False
    
    return success

def install_dashscope_fresh():
    """全新安装dashscope"""
    print_step(6, "全新安装dashscope")
    
    # 升级pip
    success, _ = run_command([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                           "升级pip")
    
    # 尝试多种安装方式
    install_methods = [
        {
            'cmd': [sys.executable, '-m', 'pip', 'install', 'dashscope', '--no-cache-dir'],
            'desc': '标准安装(无缓存)'
        },
        {
            'cmd': [sys.executable, '-m', 'pip', 'install', 'dashscope', 
                   '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple/', '--no-cache-dir'],
            'desc': '清华源安装'
        },
        {
            'cmd': [sys.executable, '-m', 'pip', 'install', 'dashscope', 
                   '-i', 'https://mirrors.aliyun.com/pypi/simple/', '--no-cache-dir'],
            'desc': '阿里源安装'
        },
        {
            'cmd': [sys.executable, '-m', 'pip', 'install', 'dashscope', '--user', '--no-cache-dir'],
            'desc': '用户模式安装'
        }
    ]
    
    for method in install_methods:
        print(f"\n🔄 尝试{method['desc']}...")
        success, result = run_command(method['cmd'], method['desc'])
        
        if success:
            # 测试导入
            test_success, _ = run_command([sys.executable, '-c', 'import dashscope; print("导入成功")'], 
                                        "测试导入")
            if test_success:
                print(f"✅ {method['desc']}成功！")
                return True
            else:
                print(f"❌ {method['desc']}失败，继续尝试下一种方法")
        else:
            print(f"❌ {method['desc']}失败")
    
    return False

def fix_python_path():
    """修复Python路径问题"""
    print_step(7, "修复Python路径问题")
    
    # 获取dashscope安装位置
    success, result = run_command([sys.executable, '-c', 
                                 'import site; print("\\n".join(site.getsitepackages()))'], 
                                 "获取site-packages路径")
    
    if success and result.stdout:
        site_packages = result.stdout.strip().split('\n')
        print("site-packages路径:")
        for path in site_packages:
            print(f"  - {path}")
            
            # 检查dashscope是否存在
            dashscope_path = Path(path) / 'dashscope'
            if dashscope_path.exists():
                print(f"✅ 找到dashscope: {dashscope_path}")
                
                # 检查权限
                if os.access(dashscope_path, os.R_OK):
                    print("✅ dashscope目录可读")
                else:
                    print("❌ dashscope目录不可读，尝试修复权限")
                    success, _ = run_command(f"chmod -R 755 {dashscope_path}", "修复权限")
    
    # 设置PYTHONPATH环境变量
    pythonpath = os.environ.get('PYTHONPATH', '')
    for path in site_packages:
        if path not in pythonpath:
            pythonpath = f"{path}:{pythonpath}" if pythonpath else path
    
    print(f"建议设置PYTHONPATH: {pythonpath}")
    
    # 创建环境变量设置脚本
    with open('set_pythonpath.sh', 'w') as f:
        f.write(f'#!/bin/bash\n')
        f.write(f'export PYTHONPATH="{pythonpath}"\n')
        f.write(f'echo "PYTHONPATH已设置为: $PYTHONPATH"\n')
    
    os.chmod('set_pythonpath.sh', 0o755)
    print("✅ 已创建set_pythonpath.sh脚本")

def final_test():
    """最终测试"""
    print_step(8, "最终测试")
    
    # 测试基本导入
    success, _ = run_command([sys.executable, '-c', 'import dashscope; print("✅ dashscope导入成功")'], 
                           "测试dashscope导入")
    
    if not success:
        print("❌ dashscope基本导入失败")
        return False
    
    # 测试子模块导入
    success, _ = run_command([sys.executable, '-c', 
                            'from dashscope.audio.asr import Transcription; print("✅ Transcription导入成功")'], 
                           "测试Transcription导入")
    
    if not success:
        print("❌ Transcription导入失败")
        return False
    
    # 测试在项目中导入
    test_code = '''
import sys
sys.path.insert(0, ".")
try:
    from fun_asr_module import FunASRProcessor
    print("✅ FunASRProcessor导入成功")
except Exception as e:
    print(f"❌ FunASRProcessor导入失败: {e}")
'''
    
    with open('test_import.py', 'w') as f:
        f.write(test_code)
    
    success, _ = run_command([sys.executable, 'test_import.py'], "测试项目中的导入")
    
    # 清理测试文件
    if os.path.exists('test_import.py'):
        os.remove('test_import.py')
    
    return success

def main():
    """主函数"""
    print("🚀 云端服务器DashScope问题修复工具")
    print("此工具将尝试解决云端服务器上dashscope导入失败的问题")
    
    # 检查是否为Linux环境
    if sys.platform != 'linux':
        print(f"⚠️ 当前系统: {sys.platform}")
        print("此脚本主要针对Linux云端服务器，在其他系统上可能不完全适用")
    
    try:
        # 步骤1: 检查环境
        check_current_environment()
        
        # 步骤2: 清理缓存
        clean_python_cache()
        
        # 步骤3: 卸载dashscope
        uninstall_dashscope()
        
        # 步骤4: 安装系统依赖
        if os.geteuid() == 0:  # 只有root用户才能安装系统依赖
            install_system_dependencies()
        else:
            print("⚠️ 非root用户，跳过系统依赖安装")
        
        # 步骤5: 创建虚拟环境(如果需要)
        if not create_virtual_environment():
            return  # 需要激活虚拟环境后重新运行
        
        # 步骤6: 全新安装dashscope
        if not install_dashscope_fresh():
            print("❌ 所有安装方法都失败了")
            return
        
        # 步骤7: 修复Python路径
        fix_python_path()
        
        # 步骤8: 最终测试
        if final_test():
            print("\n🎉 修复完成！dashscope现在应该可以正常使用了")
            print("\n📝 后续步骤:")
            print("1. 如果创建了虚拟环境，请激活它")
            print("2. 运行: source set_pythonpath.sh (如果需要)")
            print("3. 测试你的应用: python web_interface.py")
        else:
            print("\n❌ 修复失败，请检查错误信息并手动解决")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 修复过程中发生异常: {e}")

if __name__ == "__main__":
    main()
