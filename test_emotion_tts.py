#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云TTS情感测试脚本
直接测试不同情感的音频生成效果
"""

import os
import sys
from tts_engines.alibaba_emotion_tts import AlibabaEmotionTTS

def test_emotions():
    """测试不同情感的TTS效果"""
    
    # 从环境变量获取API Key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print("❌ 请设置 DASHSCOPE_API_KEY 环境变量")
        return False
    
    # 初始化TTS引擎
    print("🚀 初始化阿里云TTS引擎...")
    tts = AlibabaEmotionTTS(api_key)
    if not tts.initialize():
        print("❌ TTS引擎初始化失败")
        return False
    
    # 测试文本
    test_text = "你好，今天天气真好，我们一起去公园玩吧！"
    
    # 测试不同情感
    emotions = ['neutral', 'happy', 'sad', 'angry']
    voices = ['male', 'female']
    
    print(f"\n📝 测试文本: {test_text}")
    print("=" * 60)
    
    for voice in voices:
        print(f"\n🎤 测试 {voice} 声音:")
        for emotion in emotions:
            output_file = f"test_audio_{voice}_{emotion}.wav"
            print(f"  🎭 生成 {emotion} 情感音频...")
            
            success = tts.synthesize(
                text=test_text,
                voice=voice,
                emotion=emotion,
                output_path=output_file
            )
            
            if success and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"    ✅ 成功生成: {output_file} ({file_size} bytes)")
            else:
                print(f"    ❌ 生成失败: {output_file}")
    
    print("\n🎵 测试完成！请播放生成的音频文件对比情感差异。")
    return True

if __name__ == "__main__":
    success = test_emotions()
    sys.exit(0 if success else 1)

