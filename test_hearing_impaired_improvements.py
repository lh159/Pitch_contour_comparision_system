# -*- coding: utf-8 -*-
"""
听障人士音调比对系统改进测试
验证新的评分算法和声调分析功能
"""

import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pitch_comparison import PitchComparator
from scoring_algorithm import ScoringSystem
from chinese_tone_analyzer import ChineseToneAnalyzer
from config import Config

def generate_test_pitch_data():
    """生成测试音高数据"""
    
    # 模拟不同声调的音高曲线
    test_cases = {
        "阴平_妈": {
            "pitch": np.array([220, 225, 222, 223, 221, 224, 222]),  # 平调
            "text": "妈"
        },
        "阳平_麻": {
            "pitch": np.array([200, 210, 220, 235, 245, 250, 255]),  # 升调
            "text": "麻"
        },
        "上声_马": {
            "pitch": np.array([230, 220, 210, 205, 215, 230, 240]),  # 降升调
            "text": "马"
        },
        "去声_骂": {
            "pitch": np.array([250, 240, 230, 220, 210, 200, 190]),  # 降调
            "text": "骂"
        },
        "双字_你好": {
            "pitch": np.array([210, 205, 200, 195, 200, 215, 230, 235, 232, 228]),  # 上声+上声
            "text": "你好"
        }
    }
    
    # 为每个测试用例添加时间轴
    for case_name, case_data in test_cases.items():
        pitch_len = len(case_data["pitch"])
        case_data["times"] = np.linspace(0, 1.0, pitch_len)
    
    return test_cases

def test_tone_analyzer():
    """测试声调分析器"""
    print("🎵 测试声调分析器...")
    
    analyzer = ChineseToneAnalyzer()
    test_cases = generate_test_pitch_data()
    
    for case_name, case_data in test_cases.items():
        print(f"\n📊 测试用例: {case_name}")
        
        # 直接分析音高声调，不需要预设的期望声调
        # 对于音高曲线对比分析，我们只从音频中检测声调
        result = analyzer.analyze_pitch_tones(
            case_data["pitch"], 
            case_data["times"], 
            expected_tones=None
        )
        
        if result and 'tone_analysis' in result:
            print(f"  检测结果: {result['overall_tone_accuracy']:.2f}")
            
            # 生成反馈
            feedback = analyzer.get_tone_feedback(result['tone_analysis'])
            print(f"  反馈建议: {feedback[:100]}...")
        else:
            print(f"  分析失败: {result}")

def test_improved_scoring():
    """测试改进的评分系统"""
    print("\n🎯 测试改进的评分系统...")
    
    scoring_system = ScoringSystem()
    test_cases = generate_test_pitch_data()
    
    # 创建模拟的比较结果
    for case_name, case_data in test_cases.items():
        print(f"\n📈 测试用例: {case_name}")
        
        # 模拟比较结果
        mock_comparison_result = {
            'metrics': {
                'correlation': 0.8,
                'rmse': 25.0,
                'trend_consistency': 0.85,  # 高趋势一致性
                'pitch_range_ratio': 0.9
            },
            'standard_pitch': {
                'pitch_values': case_data["pitch"],
                'times': case_data["times"]
            },
            'user_pitch': {
                'pitch_values': case_data["pitch"] + np.random.normal(0, 5, len(case_data["pitch"])),
                'times': case_data["times"]
            }
        }
        
        # 计算评分（带声调分析）
        score_result = scoring_system.calculate_score(
            mock_comparison_result, 
            case_data["text"]
        )
        
        print(f"  总分: {score_result['total_score']}")
        print(f"  趋势分: {score_result['component_scores']['trend']}")
        print(f"  声调增强: {score_result.get('tone_enhancement', 0)}")
        print(f"  评级: {score_result['level']}")
        
        if score_result.get('tone_feedback'):
            print(f"  声调反馈: {score_result['tone_feedback'][:80]}...")

def test_baseline_alignment():
    """测试改进的音高基线对齐"""
    print("\n🎵 测试改进的音高基线对齐...")
    
    from pitch_comparison import PitchAligner
    
    aligner = PitchAligner()
    
    # 模拟不同性别的音高差异
    male_pitch = np.array([120, 125, 130, 128, 125])  # 男声（低音）
    female_pitch = np.array([220, 225, 230, 228, 225])  # 女声（高音）
    times = np.linspace(0, 1, 5)
    
    print(f"原始男声音高: {male_pitch}")
    print(f"原始女声音高: {female_pitch}")
    
    # 测试对齐
    aligned_male, aligned_female = aligner._align_pitch_baseline(male_pitch, female_pitch)
    
    print(f"对齐后男声: {aligned_male}")
    print(f"对齐后女声: {aligned_female}")
    print(f"对齐后差异: {np.mean(aligned_female) - np.mean(aligned_male):.1f}Hz")

def test_trend_consistency():
    """测试趋势一致性算法"""
    print("\n📊 测试趋势一致性算法...")
    
    comparator = PitchComparator()
    
    # 测试不同的音调模式
    patterns = {
        "完全匹配": (
            np.array([200, 210, 220, 230, 240]),
            np.array([200, 212, 222, 228, 238])
        ),
        "方向相反": (
            np.array([200, 210, 220, 230, 240]),
            np.array([240, 230, 220, 210, 200])
        ),
        "部分匹配": (
            np.array([200, 210, 220, 215, 210]),
            np.array([200, 208, 218, 220, 215])
        )
    }
    
    for pattern_name, (standard, user) in patterns.items():
        consistency = comparator._calculate_trend_consistency(standard, user)
        print(f"  {pattern_name}: {consistency:.3f}")

def demonstrate_improvement():
    """展示改进前后的对比"""
    print("\n🚀 改进效果展示...")
    
    print("📊 权重调整效果:")
    print("  旧权重: 相关性40%, 趋势30%, 稳定性20%, 音域10%")
    print("  新权重: 相关性25%, 趋势50%, 稳定性15%, 音域10%")
    print("  ✅ 突出了音调变化的重要性，更适合听障人士训练")
    
    print("\n🎵 新增功能:")
    print("  ✅ 智能音高基线对齐 - 处理性别差异")
    print("  ✅ 中文声调识别 - 专门的声调分析")
    print("  ✅ 多维度趋势分析 - 方向、幅度、模式")
    print("  ✅ 听障人士专用反馈 - 针对性建议")
    
    print("\n🎯 核心改进:")
    print("  ✅ 趋势一致性算法从简单方向匹配升级为多维度分析")
    print("  ✅ 音高对齐从固定参数升级为自适应智能对齐")
    print("  ✅ 评分系统从通用评分升级为听障人士专用评分")

if __name__ == '__main__':
    print("🎯 听障人士音调比对系统改进测试")
    print("=" * 50)
    
    try:
        # 运行各项测试
        test_tone_analyzer()
        test_improved_scoring()
        test_baseline_alignment()
        test_trend_consistency()
        demonstrate_improvement()
        
        print("\n✅ 所有测试完成！")
        print("\n🎵 系统已针对听障人士音调训练进行了全面优化:")
        print("   - 音调变化权重提升到50%")
        print("   - 智能音高基线对齐")
        print("   - 中文声调特征识别")
        print("   - 多维度趋势一致性分析")
        print("   - 专门的听障人士反馈系统")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
