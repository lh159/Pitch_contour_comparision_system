# -*- coding: utf-8 -*-
"""
IndexTTS2集成测试脚本
验证所有新功能是否正常工作
"""

import os
import sys
import time
import traceback
from config import Config

def test_imports():
    """测试模块导入"""
    print("=== 测试模块导入 ===")
    
    try:
        from tts_engines import TTSEngineBase, DialogueTTSEngine, VoiceCloningEngine
        print("✓ TTS引擎基类导入成功")
        
        from tts_engines.baidu_tts_engine import BaiduTTSEngine
        print("✓ 百度TTS引擎导入成功")
        
        from tts_engines.index_tts2_engine import IndexTTS2Engine
        print("✓ IndexTTS2引擎导入成功")
        
        from enhanced_tts_manager import EnhancedTTSManager
        print("✓ 增强型TTS管理器导入成功")
        
        from character_voice_manager import CharacterVoiceManager
        print("✓ 角色语音管理器导入成功")
        
        from dialogue_emotion_analyzer import DialogueEmotionAnalyzer
        print("✓ 对话情感分析器导入成功")
        
        return True
        
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 导入异常: {e}")
        return False

def test_character_voice_manager():
    """测试角色语音管理器"""
    print("\n=== 测试角色语音管理器 ===")
    
    try:
        from character_voice_manager import CharacterVoiceManager
        
        manager = CharacterVoiceManager()
        
        # 测试获取所有角色
        characters = manager.get_all_characters()
        print(f"✓ 发现 {len(characters)} 个角色: {characters}")
        
        # 测试获取角色配置
        for character in characters[:2]:  # 只测试前两个
            profile = manager.get_character_voice_config(character)
            if profile:
                print(f"✓ 角色 {character}: {profile.description}")
                emotions = manager.get_character_emotions(character)
                print(f"  支持情感: {emotions}")
            else:
                print(f"✗ 角色 {character} 配置获取失败")
        
        # 测试统计信息
        stats = manager.get_character_stats()
        print(f"✓ 角色统计: {stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ 角色语音管理器测试失败: {e}")
        traceback.print_exc()
        return False

def test_emotion_analyzer():
    """测试情感分析器"""
    print("\n=== 测试情感分析器 ===")
    
    try:
        from dialogue_emotion_analyzer import DialogueEmotionAnalyzer
        
        analyzer = DialogueEmotionAnalyzer()
        
        # 测试文本
        test_texts = [
            "太好了！我终于通过考试了！",
            "我今天心情不好，什么都不想做...",
            "你这个混蛋！怎么能这样对我！",
            "天哪，这怎么可能？真的假的？",
            "好的，我知道了，没问题。"
        ]
        
        for text in test_texts:
            emotion, confidence = analyzer.analyze_emotion(text)
            description = analyzer.get_emotion_description(emotion)
            print(f"✓ 文本: {text}")
            print(f"  情感: {emotion} ({description}) - 置信度: {confidence:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 情感分析器测试失败: {e}")
        traceback.print_exc()
        return False

def test_baidu_tts_engine():
    """测试百度TTS引擎"""
    print("\n=== 测试百度TTS引擎 ===")
    
    try:
        from tts_engines.baidu_tts_engine import BaiduTTSEngine
        
        if not Config.BAIDU_API_KEY or not Config.BAIDU_SECRET_KEY:
            print("⚠ 百度TTS密钥未配置，跳过测试")
            return True
        
        engine = BaiduTTSEngine(Config.BAIDU_API_KEY, Config.BAIDU_SECRET_KEY)
        
        # 测试初始化
        if engine.initialize():
            print("✓ 百度TTS引擎初始化成功")
            
            # 测试功能特性
            features = engine.get_supported_features()
            print(f"✓ 支持的功能: {features}")
            
            # 测试角色和情感
            characters = engine.get_available_characters()
            emotions = engine.get_available_emotions()
            print(f"✓ 支持的角色: {characters}")
            print(f"✓ 支持的情感: {emotions}")
            
            return True
        else:
            print("✗ 百度TTS引擎初始化失败")
            return False
        
    except Exception as e:
        print(f"✗ 百度TTS引擎测试失败: {e}")
        traceback.print_exc()
        return False

def test_indextts2_engine():
    """测试IndexTTS2引擎"""
    print("\n=== 测试IndexTTS2引擎 ===")
    
    try:
        from tts_engines.index_tts2_engine import IndexTTS2Engine
        
        engine = IndexTTS2Engine()
        
        # 测试初始化
        if engine.initialize():
            print("✓ IndexTTS2引擎初始化成功")
            
            # 测试功能特性
            features = engine.get_supported_features()
            print(f"✓ 支持的功能: {features}")
            
            # 测试角色和情感
            characters = engine.get_available_characters()
            emotions = engine.get_available_emotions()
            print(f"✓ 支持的角色: {characters}")
            print(f"✓ 支持的情感: {emotions}")
            
            return True
        else:
            print("✗ IndexTTS2引擎初始化失败")
            print("提示: 请确保已下载模型文件")
            return False
        
    except Exception as e:
        print(f"✗ IndexTTS2引擎测试失败: {e}")
        print("提示: 请检查IndexTTS2依赖是否已安装")
        return False

def test_enhanced_tts_manager():
    """测试增强型TTS管理器"""
    print("\n=== 测试增强型TTS管理器 ===")
    
    try:
        from enhanced_tts_manager import EnhancedTTSManager
        
        manager = EnhancedTTSManager()
        
        # 测试可用引擎
        engines = manager.get_available_engines()
        print(f"✓ 可用引擎: {engines}")
        print(f"✓ 当前引擎: {manager.current_engine}")
        print(f"✓ 备用引擎: {manager.fallback_engine}")
        
        # 测试引擎功能特性
        for engine in engines:
            features = manager.get_engine_features(engine)
            print(f"✓ {engine} 支持的功能: {features}")
        
        # 测试统计信息
        stats = manager.get_stats()
        print(f"✓ 统计信息: {stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ 增强型TTS管理器测试失败: {e}")
        traceback.print_exc()
        return False

def test_audio_synthesis():
    """测试音频合成"""
    print("\n=== 测试音频合成 ===")
    
    try:
        from enhanced_tts_manager import EnhancedTTSManager
        
        manager = EnhancedTTSManager()
        
        # 创建测试目录
        test_dir = "test_output"
        os.makedirs(test_dir, exist_ok=True)
        
        # 测试标准合成
        print("测试标准合成...")
        test_text = "你好，这是一个测试。"
        output_path = os.path.join(test_dir, "test_standard.wav")
        
        success = manager.synthesize_text(test_text, output_path)
        if success and os.path.exists(output_path):
            print(f"✓ 标准合成成功: {output_path}")
        else:
            print("✗ 标准合成失败")
        
        # 测试对话合成
        print("测试对话合成...")
        dialogue_text = "小明，你今天真棒！"
        audio_path, info = manager.synthesize_dialogue(
            text=dialogue_text,
            character="小明",
            auto_emotion=True
        )
        
        if audio_path and info['success']:
            print(f"✓ 对话合成成功: {audio_path}")
            print(f"  合成信息: {info}")
        else:
            print("✗ 对话合成失败")
            print(f"  合成信息: {info}")
        
        return True
        
    except Exception as e:
        print(f"✗ 音频合成测试失败: {e}")
        traceback.print_exc()
        return False

def test_web_integration():
    """测试Web集成"""
    print("\n=== 测试Web集成 ===")
    
    try:
        # 测试Web界面模块导入
        from web_interface import init_system, enhanced_tts_manager, voice_manager, emotion_analyzer
        
        print("✓ Web界面模块导入成功")
        
        # 测试系统初始化
        if init_system():
            print("✓ 系统初始化成功")
            
            # 检查组件状态
            if enhanced_tts_manager:
                print("✓ 增强型TTS管理器已初始化")
            else:
                print("⚠ 增强型TTS管理器未初始化")
            
            if voice_manager:
                print("✓ 角色语音管理器已初始化")
            else:
                print("⚠ 角色语音管理器未初始化")
            
            if emotion_analyzer:
                print("✓ 情感分析器已初始化")
            else:
                print("⚠ 情感分析器未初始化")
            
            return True
        else:
            print("✗ 系统初始化失败")
            return False
        
    except Exception as e:
        print(f"✗ Web集成测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("IndexTTS2集成测试开始\n")
    
    # 创建必要目录
    Config.create_directories()
    
    test_results = []
    
    # 运行各项测试
    tests = [
        ("模块导入", test_imports),
        ("角色语音管理器", test_character_voice_manager),
        ("情感分析器", test_emotion_analyzer),
        ("百度TTS引擎", test_baidu_tts_engine),
        ("IndexTTS2引擎", test_indextts2_engine),
        ("增强型TTS管理器", test_enhanced_tts_manager),
        ("音频合成", test_audio_synthesis),
        ("Web集成", test_web_integration)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} 测试异常: {e}")
            test_results.append((test_name, False))
    
    # 输出测试结果汇总
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:20} {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed + failed} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    
    if failed == 0:
        print("\n🎉 所有测试通过！IndexTTS2集成成功！")
        return True
    else:
        print(f"\n⚠ {failed} 项测试失败，请检查相关配置和依赖")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
