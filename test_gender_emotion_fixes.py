#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试性别和情感修复
"""

import os
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tts_module import TTSManager
from config import Config

def test_gender_emotion_fixes():
    """测试性别和情感修复"""
    print("=== 测试性别和情感修复 ===")
    
    # 初始化TTS管理器
    print("1. 初始化TTS管理器...")
    tts_manager = TTSManager()
    
    if not tts_manager.emotion_engine:
        print("❌ 阿里云情感TTS引擎未初始化")
        return False
    
    print("✅ TTS管理器初始化成功")
    
    # 测试文本
    test_text = "这是一个测试语音合成的句子。"
    
    # 测试用例
    test_cases = [
        {
            'name': '女声-中性',
            'gender': 'female',
            'emotion': 'neutral',
            'filename': 'test_female_neutral.mp3'
        },
        {
            'name': '男声-中性', 
            'gender': 'male',
            'emotion': 'neutral',
            'filename': 'test_male_neutral.mp3'
        },
        {
            'name': '女声-开心',
            'gender': 'female', 
            'emotion': 'happy',
            'filename': 'test_female_happy.mp3'
        },
        {
            'name': '男声-开心',
            'gender': 'male',
            'emotion': 'happy', 
            'filename': 'test_male_happy.mp3'
        },
        {
            'name': '女声-悲伤',
            'gender': 'female',
            'emotion': 'sad',
            'filename': 'test_female_sad.mp3'
        }
    ]
    
    print("\n2. 开始测试各种组合...")
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   测试 {i}/{len(test_cases)}: {test_case['name']}")
        print(f"   参数: gender={test_case['gender']}, emotion={test_case['emotion']}")
        
        output_path = test_case['filename']
        
        try:
            # 使用修复后的generate_standard_audio方法
            success = tts_manager.generate_standard_audio(
                text=test_text,
                output_path=output_path,
                voice_gender=test_case['gender'],
                voice_emotion=test_case['emotion']
            )
            
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                file_size = os.path.getsize(output_path)
                print(f"   ✅ 成功生成音频文件: {output_path} ({file_size} bytes)")
                success_count += 1
            else:
                print(f"   ❌ 音频生成失败")
                
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
        
        # 短暂延迟避免API限制
        time.sleep(0.5)
    
    print(f"\n3. 测试结果:")
    print(f"   成功: {success_count}/{len(test_cases)}")
    print(f"   成功率: {success_count/len(test_cases)*100:.1f}%")
    
    if success_count > 0:
        print(f"\n4. 生成的音频文件:")
        for test_case in test_cases:
            filename = test_case['filename']
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"   - {filename}: {file_size} bytes ({test_case['name']})")
    
    return success_count == len(test_cases)

def test_direct_engine():
    """直接测试阿里云TTS引擎"""
    print("\n=== 直接测试阿里云TTS引擎 ===")
    
    from tts_engines.alibaba_emotion_tts import AlibabaEmotionTTS
    
    # 创建引擎实例
    engine = AlibabaEmotionTTS(Config.DASHSCOPE_API_KEY)
    if not engine.initialize():
        print("❌ 引擎初始化失败")
        return False
    
    print("✅ 引擎初始化成功")
    
    # 测试不同声音
    voice_tests = [
        {
            'name': '女声情感(zhimiao_emo)',
            'voice': 'zhimiao_emo',
            'emotion': 'happy',
            'filename': 'test_direct_female.mp3'
        },
        {
            'name': '男声标准(zhishuo)', 
            'voice': 'zhishuo',
            'emotion': 'neutral',
            'filename': 'test_direct_male.mp3'
        }
    ]
    
    test_text = "修复后的语音合成测试，不应该读出情感提示词。"
    
    for test in voice_tests:
        print(f"\n测试: {test['name']}")
        print(f"参数: voice={test['voice']}, emotion={test['emotion']}")
        
        try:
            success = engine.synthesize(
                text=test_text,
                output_path=test['filename'],
                voice=test['voice'],
                emotion=test['emotion']
            )
            
            if success and os.path.exists(test['filename']):
                file_size = os.path.getsize(test['filename'])
                print(f"✅ 成功: {test['filename']} ({file_size} bytes)")
            else:
                print(f"❌ 失败")
                
        except Exception as e:
            print(f"❌ 异常: {e}")
    
    return True

if __name__ == "__main__":
    try:
        print("开始测试性别和情感修复...")
        
        # 测试1: 通过TTS管理器
        result1 = test_gender_emotion_fixes()
        
        # 测试2: 直接测试引擎
        result2 = test_direct_engine()
        
        if result1 and result2:
            print("\n🎉 所有测试通过！性别和情感问题已修复")
        else:
            print("\n⚠️  部分测试失败，请检查日志")
            
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
