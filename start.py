# -*- coding: utf-8 -*-
"""
音高曲线比对系统统一启动脚本
合并了原有的系统启动脚本和实时字词同步功能启动脚本
"""
import os
import sys
import time
import subprocess
import webbrowser
import socket
from pathlib import Path

def check_dependencies():
    """检查依赖模块"""
    print("🔍 检查依赖模块...")
    
    # 合并两个脚本的依赖检查
    required_modules = [
        'parselmouth', 'numpy', 'matplotlib', 'flask', 'scipy',
        'flask_socketio', 'librosa'
    ]
    
    optional_modules = [
        'redis', 'requests'
    ]
    
    missing_required = []
    missing_optional = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            missing_required.append(module)
            print(f"✗ {module} (必需)")
    
    for module in optional_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            missing_optional.append(module)
            print(f"? {module} (可选)")
    
    if missing_required:
        print(f"\n❌ 缺少必需模块: {', '.join(missing_required)}")
        print("请运行: pip install -r requirements.txt")
        return False, missing_required
    
    if missing_optional:
        print(f"\n⚠️ 缺少可选模块: {', '.join(missing_optional)}")
        print("这些模块不是必需的，但可能影响某些功能")
    
    return True, []

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

def check_system_files(mode='full'):
    """检查系统文件"""
    print(f"\n🔍 检查系统文件 ({mode})...")
    
    # 基础文件
    base_files = [
        'web_interface.py',
        'config.py',
        'tts_module.py',
        'pitch_comparison.py',
        'scoring_algorithm.py',
        'visualization.py'
    ]
    
    # 实时同步功能文件
    realtime_files = [
        'timestamp_generator.py',
        'cache_manager.py',
        'realtime_sync.py',
        'static/js/realtime-sync.js',
        'static/js/recording-guide.js',
        'static/css/realtime-sync.css',
        'templates/index.html'
    ]
    
    # 根据模式选择检查的文件
    if mode == 'full':
        required_files = base_files + realtime_files
    elif mode == 'realtime':
        required_files = ['web_interface.py'] + realtime_files
    else:
        required_files = base_files
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"✗ {file_path}")
    
    if missing_files:
        print(f"\n❌ 缺少文件: {', '.join(missing_files)}")
        return False
    
    return True

def create_directories():
    """创建必要的目录"""
    print("\n📁 创建必要的目录...")
    directories = [
        'uploads', 'outputs', 'temp', 'static', 'templates',
        'data/cache/timestamps', 'src/uploads', 'src/temp', 'src/outputs'
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✓ {directory}")
        except Exception as e:
            print(f"⚠️ 创建目录 {directory} 失败: {e}")

def run_tests():
    """运行功能测试"""
    print("\n🧪 运行功能测试...")
    
    try:
        result = subprocess.run([
            sys.executable, 'test_realtime_sync.py'
        ], capture_output=True, text=True, timeout=60)
        
        print("测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("测试错误:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 功能测试通过")
            return True
        else:
            print("❌ 功能测试失败")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
        return False
    except FileNotFoundError:
        print("⚠️ 测试文件不存在，跳过测试")
        return True
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False

def check_port_available(port):
    """检查端口是否可用"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0

def start_server(mode='full', port=None):
    """启动服务器"""
    if mode == 'realtime':
        default_port = 5000
        print("\n🚀 启动实时字词同步系统...")
    else:
        default_port = 9999
        print("\n🚀 启动音高曲线比对系统...")
    
    if port is None:
        port = default_port
    
    try:
        # 检查端口是否可用
        if not check_port_available(port):
            print(f"⚠️ 端口 {port} 已被占用")
            # 尝试其他端口
            for alt_port in [5000, 9999, 8000, 8080]:
                if alt_port != port and check_port_available(alt_port):
                    print(f"尝试使用端口 {alt_port}")
                    port = alt_port
                    break
            else:
                print("❌ 找不到可用端口")
                return False
        
        print(f"启动Web服务器在端口 {port}...")
        print(f"访问地址: http://localhost:{port}")
        print("按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        # 设置环境变量指定端口
        os.environ['PORT'] = str(port)
        
        # 启动服务器
        process = subprocess.Popen([sys.executable, 'web_interface.py'])
        
        # 等待服务器启动
        time.sleep(3)
        
        # 自动打开浏览器
        try:
            webbrowser.open(f"http://localhost:{port}")
            print("✅ 已自动打开浏览器")
        except:
            print("请手动在浏览器中访问上述地址")
        
        # 显示使用说明
        show_usage_guide(mode)
        
        # 等待用户中断
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n👋 正在关闭系统...")
            process.terminate()
            print("✅ 系统已关闭")
        
        return True
        
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        return False

def show_usage_guide(mode='full'):
    """显示使用指南"""
    print("\n" + "="*60)
    
    if mode == 'realtime':
        print("📖 实时字词同步功能使用指南:")
        print("-" * 50)
        print("1. 基本使用流程:")
        print("   - 在文本框中输入要练习的文本")
        print("   - 点击'生成标准发音'按钮")
        print("   - 点击'启用同步显示'查看实时字词高亮")
        print("   - 选择'实时指导录音'模式进行录音")
        print("")
        print("2. 实时同步功能:")
        print("   - 播放标准发音时，文字会实时高亮")
        print("   - 当前朗读的字符会有特殊标识")
        print("   - 支持进度条和时间显示")
        print("")
        print("3. 录音指导功能:")
        print("   - 实时显示应该朗读的字符")
        print("   - 提供节奏提示和时机指导")
        print("   - 统计准确率和错过的字符")
        print("")
        print("4. 缓存优化:")
        print("   - 相同文本的时间戳会被缓存")
        print("   - 提升重复使用的性能")
        print("   - 支持缓存统计和清理")
    else:
        print("音高曲线比对系统使用指南:")
        print("-" * 50)
        print("📝 基本功能:")
        print("  1. 在网页中输入要练习的中文词汇")
        print("  2. 点击'生成标准发音'获取标准音频")
        print("  3. 点击'开始录音'录制您的发音")
        print("  4. 点击'开始比对分析'查看结果")
        print("")
        print("💡 使用提示:")
        print("  - 支持的词汇: 你好、早上好、欢迎光临等")
        print("  - 建议在安静环境中录音")
        print("  - 支持实时字词同步功能")
        
    print("=" * 60)

# 移除交互式菜单，改为自动启动模式

def main():
    """主函数"""
    # 检查工作目录
    if not os.path.exists('web_interface.py'):
        print("❌ 请在项目根目录下运行此脚本")
        return False
    
    # 默认配置：完整系统，不进行功能测试，端口9999
    mode = 'full'
    port = 9999
    
    print("=" * 60)
    print("🎵 音高曲线比对系统 - 自动启动")
    print("=" * 60)
    print("🎯 启动模式: 完整系统 (音高比对 + 实时同步)")
    print(f"🔌 端口号: {port}")
    print("🚫 跳过功能测试")
    print("-" * 60)
    
    try:
        # 检查依赖
        deps_ok, missing = check_dependencies()
        if not deps_ok:
            print(f"\n❌ 缺少必需依赖: {', '.join(missing)}")
            print("正在自动安装依赖...")
            if not install_dependencies():
                print("❌ 依赖安装失败，请手动运行 python install_dependencies.py")
                return False
            # 重新检查
            deps_ok, _ = check_dependencies()
            if not deps_ok:
                print("❌ 安装后仍有依赖缺失")
                return False
        
        # 检查文件
        if not check_system_files(mode):
            print("❌ 系统文件检查失败")
            return False
        
        # 创建目录
        create_directories()
        
        print("\n✅ 系统检查完成，正在启动服务器...")
        
        # 启动服务器
        return start_server(mode, port)
            
    except KeyboardInterrupt:
        print("\n👋 已取消")
        return True
    except Exception as e:
        print(f"❌ 执行出错: {e}")
        return False

if __name__ == '__main__':
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 已取消")
        exit(0)
    except Exception as e:
        print(f"\n❌ 启动脚本异常: {e}")
        exit(1)
