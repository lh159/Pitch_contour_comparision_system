# -*- coding: utf-8 -*-
"""
测试文本对齐和汉字标注功能
"""
import os
from main_controller import PitchComparisonSystem
from config import Config

def test_text_alignment():
    """测试文本对齐功能"""
    
    print("🧪 测试音高曲线文本对齐功能")
    print("=" * 50)
    
    # 初始化系统
    system = PitchComparisonSystem()
    if not system.initialize():
        print("❌ 系统初始化失败")
        return False
    
    # 测试文本
    test_text = "你好世界"
    print(f"📝 测试文本: {test_text}")
    
    # 创建测试用户音频（这里假设存在，实际使用时需要真实的音频文件）
    user_audio_path = os.path.join(Config.TEMP_FOLDER, "test_user_audio.wav")
    
    # 检查测试音频是否存在
    if not os.path.exists(user_audio_path):
        print("⚠️  测试音频不存在，将生成一个示例音频文件")
        
        # 如果没有测试音频，我们先生成一个标准音频作为测试用
        if not system.tts_manager.generate_standard_audio(test_text, user_audio_path):
            print("❌ 无法生成测试音频文件")
            return False
        print(f"✓ 测试音频已生成: {user_audio_path}")
    
    # 执行完整处理流程
    print("\n🎯 开始处理...")
    result = system.process_word(test_text, user_audio_path, Config.OUTPUT_FOLDER)
    
    if result.get('success'):
        print("✅ 处理成功!")
        print(f"   总分: {result['score']['total_score']:.1f}分")
        print(f"   等级: {result['score']['level']}")
        
        # 检查是否有VAD和文本对齐结果
        if result.get('comparison', {}).get('vad_result'):
            vad_result = result['comparison']['vad_result']
            print(f"   VAD处理: 已启用")
            
            if vad_result.get('text_alignment_result'):
                text_alignment = vad_result['text_alignment_result']
                print(f"   文本对齐: 已启用")
                
                # 显示对齐结果
                if text_alignment.get('text_alignment'):
                    print("\n📋 文本对齐结果:")
                    for i, alignment in enumerate(text_alignment['text_alignment']):
                        expected = alignment.get('expected_word', '?')
                        recognized = alignment.get('recognized_word', '?')
                        match_type = alignment.get('match_type', 'unknown')
                        start_time = alignment.get('start_time', 0)
                        end_time = alignment.get('end_time', 0)
                        
                        status_icon = "✓" if match_type == 'exact' else "≈" if match_type == 'partial' else "✗"
                        print(f"     {i+1}. {status_icon} 期望: '{expected}' | 识别: '{recognized}' | 时间: {start_time:.2f}s-{end_time:.2f}s")
                
                # 显示ASR识别结果
                if text_alignment.get('asr_result'):
                    asr_result = text_alignment['asr_result']
                    print(f"\n🎤 语音识别结果:")
                    print(f"     识别文本: '{asr_result.get('text', '无')}'")
                    print(f"     时间戳数量: {len(asr_result.get('timestamps', []))}")
        
        if result.get('chart_path'):
            print(f"\n🎨 可视化图表已保存: {result['chart_path']}")
            print("   新功能包括:")
            print("     • 音高曲线上的汉字标注")
            print("     • 文本时域对齐图")
            print("     • 语音识别匹配度显示")
        else:
            print("⚠️  可视化图表生成失败")
    
    else:
        print(f"❌ 处理失败: {result.get('error', '未知错误')}")
        return False
    
    return True

def test_with_different_texts():
    """用不同文本测试"""
    
    test_texts = [
        "语音测试",
        "发音练习", 
        "你好朋友",
        "今天天气很好"
    ]
    
    system = PitchComparisonSystem()
    if not system.initialize():
        print("❌ 系统初始化失败")
        return
    
    print("\n🔄 批量测试不同文本...")
    
    for i, text in enumerate(test_texts):
        print(f"\n--- 测试 {i+1}: {text} ---")
        
        # 生成测试音频
        user_audio_path = os.path.join(Config.TEMP_FOLDER, f"test_batch_{i}.wav")
        if not system.tts_manager.generate_standard_audio(text, user_audio_path):
            print(f"⚠️  跳过 {text}: 无法生成音频")
            continue
        
        # 处理
        result = system.process_word(text, user_audio_path, Config.OUTPUT_FOLDER)
        
        if result.get('success'):
            print(f"✓ {text}: {result['score']['total_score']:.1f}分")
            if result.get('chart_path'):
                print(f"  图表: {os.path.basename(result['chart_path'])}")
        else:
            print(f"✗ {text}: 失败")

if __name__ == '__main__':
    print("🎯 开始测试文本对齐功能")
    
    # 创建必要目录
    Config.create_directories()
    
    # 基础测试
    success = test_text_alignment()
    
    if success:
        print("\n" + "="*50)
        print("✅ 基础测试通过！")
        
        # 批量测试
        test_with_different_texts()
        
        print("\n🎉 所有测试完成！")
        print("\n📄 功能说明:")
        print("• 现在系统支持 Paraformer + VAD 语音识别和文本对齐")
        print("• 音高曲线图上会显示对应的汉字标注")
        print("• 新增文本时域对齐图，显示识别准确度")
        print("• 支持实时的语音-文本匹配分析")
    else:
        print("\n❌ 测试失败，请检查系统配置")
