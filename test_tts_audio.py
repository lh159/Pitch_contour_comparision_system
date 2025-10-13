#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS音频生成测试脚本
用于诊断听觉反馈系统中的音频生成问题
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from tts_module import TTSManager

def test_tts_generation():
    """测试TTS音频生成"""
    print("=" * 60)
    print("TTS音频生成测试")
    print("=" * 60)
    
    # 创建必要目录
    Config.create_directories()
    
    # 初始化TTS管理器
    print("\n1. 初始化TTS管理器...")
    try:
        tts_manager = TTSManager()
        print("✓ TTS管理器初始化成功")
    except Exception as e:
        print(f"✗ TTS管理器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试文本
    test_texts = [
        "你好，欢迎来到咖啡店！",
        "今天天气真不错",
        "谢谢你的帮助"
    ]
    
    # 测试不同格式
    formats = ['mp3', 'wav']
    
    for fmt in formats:
        print(f"\n2. 测试 {fmt.upper()} 格式音频生成...")
        
        for i, text in enumerate(test_texts):
            print(f"\n   测试 {i+1}/{len(test_texts)}: '{text}'")
            
            # 生成文件路径
            filename = f"test_feedback_{i}.{fmt}"
            output_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            print(f"   输出路径: {output_path}")
            
            # 尝试生成音频
            try:
                success = tts_manager.generate_standard_audio(
                    text=text,
                    output_path=output_path,
                    voice_gender='female',
                    voice_emotion='neutral'
                )
                
                # 检查结果
                if success:
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        print(f"   ✓ 音频生成成功: {filename} ({file_size} bytes)")
                    else:
                        print(f"   ✗ 函数返回成功但文件不存在: {output_path}")
                else:
                    print(f"   ✗ 音频生成失败")
                    
            except Exception as e:
                print(f"   ✗ 音频生成异常: {e}")
                import traceback
                traceback.print_exc()
    
    # 检查uploads目录
    print(f"\n3. 检查 uploads 目录...")
    if os.path.exists(Config.UPLOAD_FOLDER):
        files = [f for f in os.listdir(Config.UPLOAD_FOLDER) if f.startswith('test_feedback_')]
        print(f"   找到 {len(files)} 个测试文件:")
        for f in files:
            filepath = os.path.join(Config.UPLOAD_FOLDER, f)
            size = os.path.getsize(filepath)
            print(f"   - {f} ({size} bytes)")
    else:
        print(f"   ✗ uploads 目录不存在")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_tts_generation()

