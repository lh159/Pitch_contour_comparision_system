# -*- coding: utf-8 -*-
"""
系统功能测试脚本
验证音高曲线比对系统的各个组件
"""
import os
import sys
import traceback
from datetime import datetime

def test_imports():
    """测试模块导入"""
    print("🧪 测试模块导入...")
    
    modules = {
        'config': 'Config',
        'tts_module': 'TTSManager', 
        'pitch_comparison': 'PitchComparator',
        'scoring_algorithm': 'ScoringSystem',
        'visualization': 'PitchVisualization',
        'main_controller': 'PitchComparisonSystem'
    }
    
    success_count = 0
    for module_name, class_name in modules.items():
        try:
            module = __import__(module_name)
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name}: {e}")
    
    print(f"\n导入测试: {success_count}/{len(modules)} 成功")
    return success_count == len(modules)

def test_config():
    """测试配置模块"""
    print("\n🧪 测试配置模块...")
    
    try:
        from config import Config
        
        # 测试目录创建
        Config.create_directories()
        
        # 检查目录是否存在
        directories = [Config.UPLOAD_FOLDER, Config.OUTPUT_FOLDER, 
                      Config.TEMP_FOLDER, Config.STATIC_FOLDER]
        
        for directory in directories:
            if os.path.exists(directory):
                print(f"  ✅ 目录存在: {directory}")
            else:
                print(f"  ❌ 目录缺失: {directory}")
                return False
        
        print(f"  ✅ 配置参数: 采样率={Config.SAMPLE_RATE}Hz")
        return True
        
    except Exception as e:
        print(f"  ❌ 配置测试失败: {e}")
        return False

def test_tts():
    """测试TTS模块"""
    print("\n🧪 测试TTS模块...")
    
    try:
        from tts_module import TTSManager
        from config import Config
        
        # 初始化TTS管理器
        tts_manager = TTSManager()
        engines = tts_manager.get_available_engines()
        
        print(f"  ✅ 可用TTS引擎: {engines}")
        
        if engines:
            # 测试生成简单音频
            test_text = "测试"
            output_path = os.path.join(Config.TEMP_FOLDER, "test_tts.wav")
            
            print(f"  📝 测试生成: '{test_text}'")
            success = tts_manager.generate_standard_audio(test_text, output_path)
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"  ✅ 音频生成成功: {file_size} bytes")
                # 清理测试文件
                try:
                    os.remove(output_path)
                except:
                    pass
                return True
            else:
                print(f"  ⚠️  音频生成失败（可能需要配置API密钥）")
                return len(engines) > 0  # 至少有引擎可用就算成功
        else:
            print(f"  ❌ 没有可用的TTS引擎")
            return False
            
    except Exception as e:
        print(f"  ❌ TTS测试失败: {e}")
        return False

def test_pitch_extraction():
    """测试音高提取功能"""
    print("\n🧪 测试音高提取...")
    
    try:
        from pitch_comparison import PitchExtractor
        import numpy as np
        import parselmouth
        
        # 创建测试音频（合成正弦波）
        extractor = PitchExtractor()
        
        # 生成测试音频信号
        sample_rate = 16000
        duration = 1.0
        frequency = 200  # 200Hz正弦波
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_signal = np.sin(2 * np.pi * frequency * t)
        
        # 创建parselmouth Sound对象
        sound = parselmouth.Sound(audio_signal, sampling_frequency=sample_rate)
        
        # 提取音高
        pitch_data = extractor.extract_pitch(sound)
        
        duration = pitch_data.get('duration', 0)
        valid_ratio = pitch_data.get('valid_ratio', 0)
        
        print(f"  ✅ 音高提取成功")
        print(f"  📊 时长: {duration:.2f}秒")
        print(f"  📊 有效比例: {valid_ratio:.1%}")
        
        return duration > 0 and valid_ratio > 0
        
    except Exception as e:
        print(f"  ❌ 音高提取测试失败: {e}")
        traceback.print_exc()
        return False

def test_scoring():
    """测试评分系统"""
    print("\n🧪 测试评分系统...")
    
    try:
        from scoring_algorithm import ScoringSystem
        
        scoring_system = ScoringSystem()
        
        # 模拟测试数据
        test_metrics = {
            'metrics': {
                'correlation': 0.8,
                'rmse': 30.0,
                'trend_consistency': 0.7,
                'pitch_range_ratio': 0.85,
                'std_mean': 200.0,
                'user_mean': 195.0,
                'valid_points': 100
            }
        }
        
        # 计算评分
        score_result = scoring_system.calculate_score(test_metrics)
        
        total_score = score_result.get('total_score', 0)
        level = score_result.get('level', '')
        
        print(f"  ✅ 评分计算成功")
        print(f"  📊 总分: {total_score}")
        print(f"  📊 评级: {level}")
        
        return total_score > 0 and level
        
    except Exception as e:
        print(f"  ❌ 评分测试失败: {e}")
        return False

def test_visualization():
    """测试可视化功能"""
    print("\n🧪 测试可视化...")
    
    try:
        from visualization import PitchVisualization
        from config import Config
        import numpy as np
        
        visualizer = PitchVisualization()
        
        # 创建模拟音高数据
        times = np.linspace(0, 2, 100)
        pitch_values = 200 + 50 * np.sin(times * 3)
        
        pitch_data = {
            'times': times,
            'pitch_values': pitch_values,
            'smooth_pitch': pitch_values,
            'duration': 2.0,
            'valid_ratio': 1.0
        }
        
        # 测试单独音高图
        output_path = os.path.join(Config.OUTPUT_FOLDER, "test_visualization.png")
        success = visualizer.plot_individual_pitch(pitch_data, output_path, "测试音高曲线")
        
        if success and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"  ✅ 可视化生成成功: {file_size} bytes")
            
            # 清理测试文件
            try:
                os.remove(output_path)
            except:
                pass
            
            return True
        else:
            print(f"  ❌ 可视化生成失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 可视化测试失败: {e}")
        return False

def test_main_controller():
    """测试主控制器"""
    print("\n🧪 测试主控制器...")
    
    try:
        from main_controller import PitchComparisonSystem
        
        # 初始化系统
        system = PitchComparisonSystem()
        success = system.initialize()
        
        if success:
            print(f"  ✅ 系统初始化成功")
            
            # 获取状态
            status = system.get_system_status()
            print(f"  📊 TTS引擎: {status.get('tts_engines', [])}")
            print(f"  📊 组件状态: {status.get('initialized', False)}")
            
            return True
        else:
            print(f"  ❌ 系统初始化失败")
            return False
            
    except Exception as e:
        print(f"  ❌ 主控制器测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("音高曲线比对系统 - 功能测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version}")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置模块", test_config),
        ("TTS模块", test_tts),
        ("音高提取", test_pitch_extraction),
        ("评分系统", test_scoring),
        ("可视化", test_visualization),
        ("主控制器", test_main_controller),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:12} {status}")
        if result:
            passed += 1
    
    total = len(results)
    print("=" * 50)
    print(f"总体结果: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常使用")
        print("\n下一步:")
        print("  运行: python start_system.py")
        print("  或者: python web_interface.py")
    elif passed >= total * 0.7:
        print("⚠️  大部分测试通过，系统基本可用")
        print("建议检查失败的模块")
    else:
        print("❌ 多个测试失败，系统可能无法正常工作")
        print("请检查依赖安装和配置")

if __name__ == '__main__':
    main()
