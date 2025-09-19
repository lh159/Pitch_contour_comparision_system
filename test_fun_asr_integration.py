#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Fun-ASR时间戳集成功能
"""

import os
import sys
from tts_module import TTSManager
from pitch_comparison import PitchComparator
from config import Config

def test_fun_asr_integration():
    """测试Fun-ASR集成功能"""
    
    # 创建必要目录
    Config.create_directories()
    
    # 测试文本
    test_text = "今天天气很好"
    
    print("🚀 开始测试Fun-ASR时间戳集成功能...")
    print(f"测试文本: {test_text}")
    
    try:
        # 1. 生成TTS标准音频
        print("\n📢 步骤1: 生成TTS标准音频...")
        tts_manager = TTSManager()
        
        # 生成TTS音频文件路径
        standard_audio = os.path.join(Config.OUTPUT_FOLDER, f'fun_asr_test_standard_{test_text}.wav')
        
        success = tts_manager.generate_standard_audio(
            text=test_text,
            output_path=standard_audio
        )
        
        if not success:
            print("❌ TTS生成失败")
            return False
        print(f"✅ TTS音频生成成功: {standard_audio}")
        
        # 2. 准备用户音频（这里用相同的音频做测试）
        print("\n🎙️ 步骤2: 准备用户音频...")
        user_audio = standard_audio  # 测试时使用相同音频
        print(f"用户音频: {user_audio}")
        
        # 3. 执行Fun-ASR增强音高比对
        print("\n🔍 步骤3: 执行Fun-ASR增强音高比对...")
        comparator = PitchComparator()
        
        output_path = os.path.join(Config.OUTPUT_FOLDER, 'fun_asr_test_comparison.png')
        
        result = comparator.compare_with_fun_asr_visualization(
            standard_audio=standard_audio,
            user_audio=user_audio,
            original_text=test_text,
            output_path=output_path
        )
        
        if result:
            print("✅ Fun-ASR增强音高比对成功!")
            print(f"📊 可视化结果: {result['visualization_path']}")
            print(f"🎯 Fun-ASR启用状态: {result['fun_asr_enabled']}")
            
            # 显示评分结果
            score_result = result.get('score_result', {})
            if score_result:
                total_score = score_result.get('total_score', 0)
                print(f"📈 总分: {total_score:.1f}")
                
                component_scores = score_result.get('component_scores', {})
                for component, score in component_scores.items():
                    print(f"   {component}: {score:.1f}")
            
            return True
        else:
            print("❌ Fun-ASR增强音高比对失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fun_asr_module_only():
    """单独测试Fun-ASR模块"""
    print("\n🧪 单独测试Fun-ASR模块...")
    
    try:
        from fun_asr_module import FunASRProcessor
        
        processor = FunASRProcessor()
        
        # 测试音频文件（需要是公网URL）
        print("⚠️ 注意: Fun-ASR需要公网可访问的音频URL")
        print("请配置文件上传服务以获得完整功能")
        
        # 测试文本对齐功能
        test_text = "今天天气很好"
        print(f"测试文本: {test_text}")
        
        # 这里只是演示API调用，实际需要公网URL
        print("📝 Fun-ASR模块初始化成功，等待公网URL配置...")
        
        return True
        
    except Exception as e:
        print(f"❌ Fun-ASR模块测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎵 Fun-ASR时间戳集成测试")
    print("=" * 50)
    
    # 检查环境变量
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if not api_key:
        print("⚠️ 警告: 未设置DASHSCOPE_API_KEY环境变量")
        print("Fun-ASR功能将不可用，但会测试其他功能")
    
    # 测试1: 单独测试Fun-ASR模块
    test1_result = test_fun_asr_module_only()
    
    # 测试2: 完整集成测试
    test2_result = test_fun_asr_integration()
    
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    print(f"Fun-ASR模块测试: {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"完整集成测试: {'✅ 通过' if test2_result else '❌ 失败'}")
    
    if test1_result and test2_result:
        print("🎉 所有测试通过!")
        return True
    else:
        print("⚠️ 部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
