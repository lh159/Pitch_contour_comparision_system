# -*- coding: utf-8 -*-
"""
依赖安装脚本
自动检测和安装系统所需的依赖包
"""
import subprocess
import sys
import os
import importlib.util

class DependencyInstaller:
    """依赖安装器"""
    
    def __init__(self):
        self.required_packages = {
            # 核心依赖
            'parselmouth': 'praat-parselmouth>=0.4.2',
            'numpy': 'numpy>=1.21.0',
            'matplotlib': 'matplotlib>=3.5.0',
            'scipy': 'scipy>=1.7.0',
            'librosa': 'librosa>=0.8.1',
            'pydub': 'pydub>=0.25.1',
            'scikit-learn': 'scikit-learn>=1.0.0',
            
            # Web框架
            'flask': 'flask>=2.0.0',
            'flask_cors': 'flask-cors>=3.0.10',
            
            # 工具库
            'requests': 'requests>=2.25.0',
            'python-dotenv': 'python-dotenv>=0.19.0',
            'seaborn': 'seaborn>=0.11.0',
        }
        
        self.optional_packages = {
            # TTS选项
            'edge-tts': 'edge-tts>=6.1.0',
            'pyttsx3': 'pyttsx3>=2.90',
            
            # DTW算法（可选但推荐）
            'dtaidistance': 'dtaidistance>=2.3.4',
        }
        
        self.installed_packages = set()
        self.failed_packages = set()
    
    def check_package(self, package_name: str) -> bool:
        """检查包是否已安装"""
        try:
            importlib.import_module(package_name)
            return True
        except ImportError:
            return False
    
    def install_package(self, package_spec: str) -> bool:
        """安装单个包"""
        try:
            print(f"正在安装: {package_spec}")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package_spec, '--upgrade'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"✅ 安装成功: {package_spec}")
            return True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"❌ 安装失败: {package_spec} - {error_msg}")
            return False
    
    def install_required_packages(self):
        """安装必需的依赖包"""
        print("🔧 检查和安装必需依赖包...")
        
        for package_name, package_spec in self.required_packages.items():
            if self.check_package(package_name):
                print(f"✅ 已安装: {package_name}")
                self.installed_packages.add(package_name)
            else:
                print(f"⚠️  缺少: {package_name}")
                if self.install_package(package_spec):
                    self.installed_packages.add(package_name)
                else:
                    self.failed_packages.add(package_name)
    
    def install_optional_packages(self):
        """安装可选的依赖包"""
        print("\n🔧 检查和安装可选依赖包...")
        
        for package_name, package_spec in self.optional_packages.items():
            if self.check_package(package_name):
                print(f"✅ 已安装: {package_name}")
                self.installed_packages.add(package_name)
            else:
                print(f"⚠️  缺少: {package_name} (可选)")
                
                # 询问是否安装可选包
                if package_name in ['edge-tts', 'pyttsx3']:
                    response = input(f"是否安装 {package_name}? (y/n): ").lower().strip()
                    if response in ['y', 'yes', '是']:
                        if self.install_package(package_spec):
                            self.installed_packages.add(package_name)
                        else:
                            self.failed_packages.add(package_name)
                else:
                    # 自动安装其他可选包
                    if self.install_package(package_spec):
                        self.installed_packages.add(package_name)
                    else:
                        self.failed_packages.add(package_name)
    
    def create_environment_file(self):
        """创建环境配置文件"""
        print("\n📝 创建环境配置文件...")
        
        env_content = """# 音高曲线比对系统环境变量配置
# 请根据需要修改以下配置

# === 百度TTS配置（推荐）===
# 请在百度智能云申请TTS服务并获取密钥
BAIDU_API_KEY=your_baidu_api_key_here
BAIDU_SECRET_KEY=your_baidu_secret_key_here
BAIDU_VOICE_PER=0

# === 系统配置 ===
SECRET_KEY=your_secret_key_here_change_in_production
DEBUG=true
PORT=5000

# === 使用说明 ===
# 1. 推荐使用百度TTS，性价比高，免费额度大
# 2. 如果不配置百度TTS，系统会尝试其他TTS引擎（Edge TTS、离线TTS）
# 3. 生产环境中请将DEBUG设置为false，并更改SECRET_KEY
"""
        
        env_file = '.env'
        if not os.path.exists(env_file):
            try:
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                print(f"✅ 创建环境配置文件: {env_file}")
                print("   请根据需要修改其中的配置项")
            except Exception as e:
                print(f"❌ 创建环境文件失败: {e}")
        else:
            print(f"✅ 环境配置文件已存在: {env_file}")
    
    def check_system_requirements(self):
        """检查系统要求"""
        print("🔍 检查系统要求...")
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version >= (3, 8):
            print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
            print("   需要Python 3.8或更高版本")
            return False
        
        # 检查pip
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', '--version'], 
                                stdout=subprocess.DEVNULL)
            print("✅ pip 可用")
        except subprocess.CalledProcessError:
            print("❌ pip 不可用")
            return False
        
        return True
    
    def run_installation(self):
        """运行完整的安装流程"""
        print("🚀 开始安装音高曲线比对系统依赖...")
        print("=" * 50)
        
        # 检查系统要求
        if not self.check_system_requirements():
            print("❌ 系统要求检查失败")
            return False
        
        # 安装必需包
        self.install_required_packages()
        
        # 安装可选包
        self.install_optional_packages()
        
        # 创建环境文件
        self.create_environment_file()
        
        # 显示安装结果
        print("\n" + "=" * 50)
        print("📊 安装结果:")
        print(f"✅ 成功安装: {len(self.installed_packages)} 个包")
        print(f"❌ 安装失败: {len(self.failed_packages)} 个包")
        
        if self.failed_packages:
            print(f"\n失败的包: {', '.join(self.failed_packages)}")
            print("请手动安装失败的包，或检查网络连接")
        
        # 检查核心功能是否可用
        core_missing = set(['parselmouth', 'numpy', 'matplotlib', 'flask']) & self.failed_packages
        if core_missing:
            print(f"\n⚠️  警告: 核心包安装失败 {core_missing}")
            print("系统可能无法正常运行")
            return False
        
        print("\n🎉 依赖安装完成！")
        print("📝 下一步:")
        print("   1. 根据需要修改 .env 文件中的配置")
        print("   2. 运行 python web_interface.py 启动系统")
        print("   3. 在浏览器中访问 http://localhost:5000")
        
        return True

def main():
    """主函数"""
    installer = DependencyInstaller()
    
    print("音高曲线比对系统 - 依赖安装工具")
    print("=" * 50)
    
    # 询问是否继续
    response = input("是否开始安装依赖包? (y/n): ").lower().strip()
    if response not in ['y', 'yes', '是']:
        print("安装已取消")
        return
    
    # 运行安装
    success = installer.run_installation()
    
    if success:
        # 询问是否立即测试
        response = input("\n是否立即测试系统? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是']:
            try:
                print("\n🧪 测试系统组件...")
                from main_controller import PitchComparisonSystem
                
                system = PitchComparisonSystem()
                if system.initialize():
                    print("✅ 系统测试通过！")
                    
                    status = system.get_system_status()
                    print(f"   TTS引擎: {status['tts_engines']}")
                    print("   系统已准备就绪")
                else:
                    print("❌ 系统测试失败")
                    
            except Exception as e:
                print(f"❌ 系统测试失败: {e}")
                print("请检查依赖安装是否完整")

if __name__ == '__main__':
    main()
