# -*- coding: utf-8 -*-
"""
IndexTTS2安装和配置脚本
自动安装依赖、下载模型文件并配置系统
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

def run_command(command, description, check=True):
    """运行命令并处理结果"""
    print(f"正在执行: {description}")
    print(f"命令: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ {description} 成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ {description} 失败")
            if result.stderr.strip():
                print(f"错误: {result.stderr.strip()}")
            if check:
                return False
            return True
            
    except Exception as e:
        print(f"✗ {description} 异常: {e}")
        if check:
            return False
        return True

def check_python_version():
    """检查Python版本"""
    print("=== 检查Python版本 ===")
    
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 10:
        print("✓ Python版本符合要求 (>= 3.10)")
        return True
    else:
        print("✗ Python版本不符合要求，需要Python 3.10或更高版本")
        return False

def check_gpu_support():
    """检查GPU支持"""
    print("\n=== 检查GPU支持 ===")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✓ 检测到 {gpu_count} 个GPU: {gpu_name}")
            print(f"CUDA版本: {torch.version.cuda}")
            return True
        else:
            print("⚠ 未检测到可用GPU，将使用CPU模式")
            return False
    except ImportError:
        print("⚠ PyTorch未安装，无法检测GPU支持")
        return False

def install_base_dependencies():
    """安装基础依赖"""
    print("\n=== 安装基础依赖 ===")
    
    dependencies = [
        "torch",
        "torchaudio", 
        "transformers",
        "librosa",
        "soundfile",
        "numpy",
        "scipy",
        "jieba",
        "requests"
    ]
    
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"安装 {dep}", check=False):
            print(f"⚠ {dep} 安装可能失败，请手动检查")
    
    return True

def setup_indextts2():
    """设置IndexTTS2"""
    print("\n=== 设置IndexTTS2 ===")
    
    indextts_path = "third_party/index-tts"
    
    if not os.path.exists(indextts_path):
        print(f"✗ IndexTTS2目录不存在: {indextts_path}")
        return False
    
    # 检查pyproject.toml
    pyproject_path = os.path.join(indextts_path, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        print(f"✗ pyproject.toml不存在: {pyproject_path}")
        return False
    
    # 安装IndexTTS2
    original_dir = os.getcwd()
    try:
        os.chdir(indextts_path)
        
        # 尝试使用uv安装（如果可用）
        if run_command("which uv", "检查uv可用性", check=False):
            print("使用uv安装IndexTTS2依赖...")
            success = run_command("uv sync --all-extras", "uv安装IndexTTS2", check=False)
        else:
            print("uv不可用，使用pip安装...")
            success = run_command("pip install -e .", "pip安装IndexTTS2", check=False)
        
        if not success:
            print("⚠ IndexTTS2安装可能失败")
        
    finally:
        os.chdir(original_dir)
    
    return True

def download_models():
    """下载模型文件"""
    print("\n=== 下载模型文件 ===")
    
    checkpoints_dir = "third_party/index-tts/checkpoints"
    
    # 检查是否已有模型文件
    config_path = os.path.join(checkpoints_dir, "config.yaml")
    if os.path.exists(config_path):
        # 检查模型文件是否完整
        model_files = ["pytorch_model.bin", "model.safetensors", "config.json"]
        existing_files = []
        for model_file in model_files:
            if os.path.exists(os.path.join(checkpoints_dir, model_file)):
                existing_files.append(model_file)
        
        if existing_files:
            print(f"✓ 发现已存在的模型文件: {existing_files}")
            user_input = input("是否重新下载模型文件？(y/N): ").lower()
            if user_input != 'y':
                print("跳过模型下载")
                return True
    
    # 尝试使用huggingface-cli下载
    hf_commands = [
        "pip install huggingface_hub",
        f"huggingface-cli download IndexTeam/IndexTTS-2 --local-dir {checkpoints_dir}"
    ]
    
    for cmd in hf_commands:
        if not run_command(cmd, f"执行: {cmd}", check=False):
            print(f"⚠ 命令执行可能失败: {cmd}")
    
    # 验证下载结果
    if os.path.exists(config_path):
        print("✓ 模型文件下载成功")
        return True
    else:
        print("✗ 模型文件下载失败")
        print("请手动下载模型文件:")
        print("1. 安装huggingface_hub: pip install huggingface_hub")
        print("2. 下载模型: huggingface-cli download IndexTeam/IndexTTS-2 --local-dir=third_party/index-tts/checkpoints")
        return False

def create_directories():
    """创建必要目录"""
    print("\n=== 创建目录 ===")
    
    directories = [
        "config",
        "cache/tts",
        "cache/indextts2",
        "tts_engines",
        "test_output"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ 创建目录: {directory}")
    
    return True

def test_installation():
    """测试安装结果"""
    print("\n=== 测试安装 ===")
    
    try:
        # 测试基本导入
        print("测试模块导入...")
        from tts_engines.index_tts2_engine import IndexTTS2Engine
        print("✓ IndexTTS2引擎导入成功")
        
        # 测试引擎初始化
        print("测试引擎初始化...")
        engine = IndexTTS2Engine()
        if engine.initialize():
            print("✓ IndexTTS2引擎初始化成功")
            
            # 测试功能
            features = engine.get_supported_features()
            characters = engine.get_available_characters()
            emotions = engine.get_available_emotions()
            
            print(f"✓ 支持的功能: {features}")
            print(f"✓ 可用角色: {characters}")
            print(f"✓ 可用情感: {emotions}")
            
            return True
        else:
            print("✗ IndexTTS2引擎初始化失败")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def main():
    """主安装函数"""
    print("IndexTTS2自动安装脚本")
    print("=" * 50)
    
    # 安装步骤
    steps = [
        ("检查Python版本", check_python_version),
        ("检查GPU支持", check_gpu_support),
        ("安装基础依赖", install_base_dependencies),
        ("设置IndexTTS2", setup_indextts2),
        ("下载模型文件", download_models),
        ("创建目录", create_directories),
        ("测试安装", test_installation)
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            if not step_func():
                failed_steps.append(step_name)
        except Exception as e:
            print(f"✗ {step_name} 异常: {e}")
            failed_steps.append(step_name)
    
    # 输出安装结果
    print("\n" + "=" * 50)
    print("安装结果汇总")
    print("=" * 50)
    
    if failed_steps:
        print(f"⚠ 以下步骤失败或有警告: {', '.join(failed_steps)}")
        print("\n建议手动检查这些步骤:")
        
        if "下载模型文件" in failed_steps:
            print("- 模型文件下载失败，请手动下载")
            print("  命令: huggingface-cli download IndexTeam/IndexTTS-2 --local-dir=third_party/index-tts/checkpoints")
        
        if "设置IndexTTS2" in failed_steps:
            print("- IndexTTS2安装失败，请检查依赖")
            print("  尝试: cd third_party/index-tts && pip install -e .")
        
        if "测试安装" in failed_steps:
            print("- 安装测试失败，请运行: python test_indextts2_integration.py")
    else:
        print("🎉 IndexTTS2安装完成！")
        print("\n接下来您可以:")
        print("1. 运行测试: python test_indextts2_integration.py")
        print("2. 启动Web服务: python web_interface.py")
        print("3. 查看使用文档: docs/IndexTTS2场景对话集成方案.md")
    
    return len(failed_steps) == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
