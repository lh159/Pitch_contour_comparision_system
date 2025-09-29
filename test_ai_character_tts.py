# -*- coding: utf-8 -*-
"""
测试AI角色情感TTS功能
"""
import os
import sys
import json
from config import Config
from tts_module import get_tts_manager

def test_ai_character_tts():
    """测试AI角色情感TTS功能"""
    print("🎭 开始测试AI角色情感TTS功能...")
    
    # 获取TTS管理器
    tts_manager = get_tts_manager()
    
    if not tts_manager.is_emotion_supported():
        print("❌ 情感TTS不可用，请检查阿里云TTS配置")
        return False
    
    # 测试用例
    test_cases = [
        {
            'text': '你好！我很高兴见到你！',
            'character_type': 'adult_female',
            'emotion': 'happy',
            'scenario_context': '友好聚会场景',
            'expected_voice': 'zhimiao_emo'
        },
        {
            'text': '请注意，这个问题很重要。',
            'character_type': 'adult_male',
            'emotion': 'serious',
            'scenario_context': '商务会议场景',
            'expected_voice': 'zhibing_emo'
        },
        {
            'text': '对不起，让您久等了。',
            'character_type': 'young_female',
            'emotion': 'gentle',
            'scenario_context': '客服场景',
            'expected_voice': 'zhimiao_emo'
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 测试用例 {i}: {test_case['text']}")
        print(f"   角色类型: {test_case['character_type']}")
        print(f"   情感: {test_case['emotion']}")
        print(f"   场景: {test_case['scenario_context']}")
        
        # 生成输出文件路径
        output_filename = f"test_ai_character_{i}_{test_case['character_type']}_{test_case['emotion']}.wav"
        output_path = os.path.join(Config.TEMP_FOLDER, output_filename)
        
        # 确保临时目录存在
        os.makedirs(Config.TEMP_FOLDER, exist_ok=True)
        
        try:
            # 生成AI角色音频
            success = tts_manager.generate_ai_character_audio(
                text=test_case['text'],
                output_path=output_path,
                character_type=test_case['character_type'],
                emotion=test_case['emotion'],
                scenario_context=test_case['scenario_context']
            )
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"   ✅ 生成成功: {output_filename} ({file_size} bytes)")
                success_count += 1
            else:
                print(f"   ❌ 生成失败: 文件不存在或为空")
                
        except Exception as e:
            print(f"   ❌ 生成异常: {e}")
    
    print(f"\n📊 测试结果: {success_count}/{len(test_cases)} 成功")
    
    if success_count == len(test_cases):
        print("🎉 所有测试用例通过！AI角色情感TTS功能正常")
        return True
    else:
        print("⚠️ 部分测试用例失败，请检查TTS配置")
        return False

def test_emotion_detection():
    """测试情感检测功能"""
    print("\n🎭 测试情感检测功能...")
    
    # 导入情感检测函数
    sys.path.append(os.path.dirname(__file__))
    from web_interface import detect_dialogue_emotion
    
    test_texts = [
        ('你好！我很开心！', 'happy'),
        ('太好了！真棒！', 'happy'),
        ('谢谢您的帮助', 'gentle'),
        ('对不起，让您久等了', 'gentle'),
        ('这个问题很重要，请注意', 'serious'),
        ('我很生气！', 'angry'),
        ('我感到很难过', 'sad'),
        ('你在哪里？', 'neutral'),
        ('今天天气不错', 'neutral')
    ]
    
    correct_count = 0
    
    for text, expected_emotion in test_texts:
        detected_emotion = detect_dialogue_emotion(text)
        is_correct = detected_emotion == expected_emotion
        
        print(f"   文本: '{text}' -> 检测: {detected_emotion}, 期望: {expected_emotion} {'✅' if is_correct else '❌'}")
        
        if is_correct:
            correct_count += 1
    
    print(f"\n📊 情感检测准确率: {correct_count}/{len(test_texts)} ({correct_count/len(test_texts)*100:.1f}%)")
    
    return correct_count >= len(test_texts) * 0.7  # 70%准确率算通过

def main():
    """主测试函数"""
    print("🚀 开始AI角色情感TTS系统测试")
    print("=" * 50)
    
    # 检查配置
    if not hasattr(Config, 'ALIBABA_TTS_CONFIG') or not Config.ALIBABA_TTS_CONFIG.get('enabled'):
        print("❌ 阿里云TTS未配置或未启用")
        print("请在config.py中配置ALIBABA_TTS_CONFIG")
        return
    
    # 测试TTS功能
    tts_success = test_ai_character_tts()
    
    # 测试情感检测
    emotion_success = test_emotion_detection()
    
    print("\n" + "=" * 50)
    print("📋 测试总结:")
    print(f"   AI角色TTS: {'✅ 通过' if tts_success else '❌ 失败'}")
    print(f"   情感检测: {'✅ 通过' if emotion_success else '❌ 失败'}")
    
    if tts_success and emotion_success:
        print("\n🎉 所有测试通过！AI角色情感TTS系统运行正常")
    else:
        print("\n⚠️ 部分测试失败，请检查系统配置")

if __name__ == '__main__':
    main()
