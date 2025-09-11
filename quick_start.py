#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音高曲线比对系统快速启动脚本
默认配置：完整系统，端口9999，无需用户交互
"""
import subprocess
import sys
import os

def quick_start():
    """快速启动系统"""
    print("🚀 快速启动音高曲线比对系统...")
    print("📍 模式: 完整系统")
    print("🔌 端口: 9999")
    print("=" * 50)
    
    try:
        # 直接调用主启动脚本
        result = subprocess.run([sys.executable, 'start.py'], 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n👋 已取消启动")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

if __name__ == '__main__':
    success = quick_start()
    exit(0 if success else 1)
