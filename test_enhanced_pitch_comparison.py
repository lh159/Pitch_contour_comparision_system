#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强的音高比对功能
"""

import os
import sys
from main_controller import PitchComparisonSystem

def test_enhanced_pitch_comparison():
    """测试增强的音高比对功能"""
    print("=== 测试增强的音高比对系统 ===")
    
    # 初始化系统
    system = PitchComparisonSystem()
    if not system.initialize():
        print("❌ 系统初始化失败")
        return False
    
    print("✓ 系统初始化成功")
    print(f"  - VAD功能: {'启用' if system.comparator.use_vad else '禁用'}")
    print(f"  - Fun-ASR功能: {'启用' if system.comparator.use_fun_asr else '禁用'}")
    print(f"  - 增强对齐功能: {'启用' if system.comparator.use_enhanced_alignment else '禁用'}")
    
    # 测试文本
    test_text = "你好世界"
    
    # 生成TTS音频
    print(f"\n🎵 生成TTS音频: {test_text}")
    tts_path = "temp/test_tts_enhanced.wav"
    
    if not system.tts_manager.generate_standard_audio(test_text, tts_path):
        print("❌ TTS音频生成失败")
        return False
    
    print(f"✓ TTS音频已生成: {tts_path}")
    
    # 如果有现有的用户录音可以用于测试
    user_audio_path = "temp/test_user.wav"
    if not os.path.exists(user_audio_path):
        # 创建一个简单的测试音频（复制TTS作为模拟用户录音）
        import shutil
        try:
            shutil.copy(tts_path, user_audio_path)
            print(f"✓ 使用TTS音频模拟用户录音: {user_audio_path}")
        except Exception as e:
            print(f"❌ 无法创建测试用户录音: {e}")
            return False
    
    # 执行增强的音高比对
    print(f"\n🔍 执行增强音高比对分析...")
    result = system.process_word(test_text, user_audio_path, "temp")
    
    if 'error' in result:
        print(f"❌ 音高比对失败: {result['error']}")
        return False
    
    print("✅ 增强音高比对成功!")
    
    # 检查增强功能是否被使用
    comparison_result = result.get('comparison_result', {})
    preprocessing_info = comparison_result.get('preprocessing_info', {})
    enhanced_alignment_result = comparison_result.get('enhanced_alignment_result')
    
    print(f"  - 增强对齐已启用: {preprocessing_info.get('enhanced_alignment_enabled', False)}")
    print(f"  - 增强对齐已使用: {preprocessing_info.get('enhanced_alignment_used', False)}")
    
    if enhanced_alignment_result:
        print(f"  - TTS有效时长: {enhanced_alignment_result.get('tts_effective_duration', 0):.3f}s")
        alignment = enhanced_alignment_result.get('alignment', {})
        print(f"  - 对齐方法: {alignment.get('method', 'unknown')}")
        user_quality = enhanced_alignment_result.get('user_quality', {})
        print(f"  - 用户录音质量: {user_quality.get('reason', 'unknown')}")
    
    # 检查可视化结果
    visualization_path = result.get('visualization_path')
    if visualization_path and os.path.exists(visualization_path):
        print(f"✓ 可视化图表已生成: {visualization_path}")
    else:
        print("⚠️ 可视化图表未生成")
    
    return True

def main():
    """主函数"""
    try:
        success = test_enhanced_pitch_comparison()
        if success:
            print("\n🎉 增强音高比对功能测试完成!")
        else:
            print("\n❌ 增强音高比对功能测试失败!")
        return success
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
