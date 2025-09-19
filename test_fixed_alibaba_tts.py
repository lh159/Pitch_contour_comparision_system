#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的阿里云TTS引擎
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tts_engines.alibaba_emotion_tts import AlibabaEmotionTTS
from config import Config

def test_fixed_alibaba_tts():
    """测试修复后的阿里云TTS引擎"""
    
    print("=== 测试修复后的阿里云TTS引擎 ===")
    
    # 创建TTS实例
    api_key = Config.ALIBABA_TTS_CONFIG['api_key']
    tts = AlibabaEmotionTTS(api_key)
    
    # 初始化
    print("1. 初始化引擎...")
    if not tts.initialize():
        print("❌ 引擎初始化失败")
        return False
    print("✅ 引擎初始化成功")
    
    # 测试基本合成
    print("\n2. 测试基本语音合成...")
    success = tts.synthesize(
        text="你好，欢迎使用音高曲线比对系统！",
        output_path="test_basic_fixed.mp3",
        voice="zhimiao_emo",
        emotion="neutral"
    )
    
    if success:
        print("✅ 基本语音合成成功")
    else:
        print("❌ 基本语音合成失败")
        return False
    
    # 测试情感合成
    print("\n3. 测试情感语音合成...")
    emotions_to_test = ['happy', 'sad', 'gentle']
    
    for emotion in emotions_to_test:
        print(f"   测试情感: {emotion}")
        success = tts.synthesize(
            text=f"这是{emotion}情感的测试语音。",
            output_path=f"test_emotion_{emotion}_fixed.mp3",
            voice="zhimiao_emo",
            emotion=emotion
        )
        
        if success:
            print(f"   ✅ {emotion}情感合成成功")
        else:
            print(f"   ❌ {emotion}情感合成失败")
    
    # 测试对话功能
    print("\n4. 测试对话功能...")
    
    # 女性角色
    success_female = tts.synthesize_dialogue(
        text="我是AI助手小美，很高兴为您服务！",
        character="female",
        emotion="gentle",
        output_path="test_dialogue_female_fixed.mp3"
    )
    
    # 男性角色
    success_male = tts.synthesize_dialogue(
        text="我是AI助手小明，有什么可以帮您的吗？",
        character="male", 
        emotion="neutral",
        output_path="test_dialogue_male_fixed.mp3"
    )
    
    if success_female and success_male:
        print("✅ 对话功能测试成功")
    else:
        print("❌ 对话功能测试失败")
    
    # 显示可用功能
    print("\n5. 可用功能信息:")
    print(f"   可用角色: {tts.get_available_characters()}")
    print(f"   可用情感: {tts.get_available_emotions()}")
    
    voice_info = tts.get_voice_info()
    print(f"   可用发音人:")
    for voice_key, info in voice_info.items():
        print(f"     - {voice_key}: {info['name']} ({info['description']})")
    
    return True

if __name__ == "__main__":
    try:
        success = test_fixed_alibaba_tts()
        if success:
            print("\n🎉 阿里云TTS修复测试完成！")
        else:
            print("\n😞 阿里云TTS修复测试失败")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
