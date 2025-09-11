# -*- coding: utf-8 -*-
"""
实时字词同步功能测试脚本
"""
import unittest
import os
import json
import time
import tempfile
from datetime import datetime
import numpy as np

# 测试模块导入
try:
    from timestamp_generator import UniversalTimestampGenerator
    from cache_manager import TimestampCache, PerformanceOptimizer
except ImportError as e:
    print(f"警告：某些模块导入失败: {e}")

class TestTimestampGenerator(unittest.TestCase):
    """时间戳生成器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.generator = UniversalTimestampGenerator(enable_cache=False)  # 测试时禁用缓存
        self.test_text = "你好世界"
        self.test_audio_duration = 3.0
        
    def test_uniform_estimation(self):
        """测试均匀分布估算"""
        print("\n=== 测试均匀分布时间戳估算 ===")
        
        # 创建临时音频文件路径（不需要真实文件，只用于测试）
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            audio_path = f.name
        
        try:
            # 模拟音频时长
            original_get_duration = self.generator._get_audio_duration
            self.generator._get_audio_duration = lambda path: self.test_audio_duration
            
            result = self.generator._uniform_estimation(self.test_text, audio_path)
            
            # 验证结果
            self.assertTrue(result['success'])
            self.assertEqual(result['method'], 'uniform_estimation')
            self.assertEqual(len(result['char_timestamps']), len(self.test_text))
            
            # 验证时间戳逻辑
            timestamps = result['char_timestamps']
            expected_duration = self.test_audio_duration / len(self.test_text)
            
            for i, ts in enumerate(timestamps):
                self.assertEqual(ts['char'], self.test_text[i])
                self.assertEqual(ts['index'], i)
                self.assertAlmostEqual(ts['start_time'], i * expected_duration, places=3)
                self.assertAlmostEqual(ts['end_time'], (i + 1) * expected_duration, places=3)
                self.assertEqual(ts['confidence'], 0.5)
            
            print(f"✓ 均匀分布估算测试通过，生成 {len(timestamps)} 个时间戳")
            
        finally:
            # 恢复原方法
            self.generator._get_audio_duration = original_get_duration
            # 清理临时文件
            try:
                os.unlink(audio_path)
            except:
                pass
    
    def test_timestamp_validation(self):
        """测试时间戳验证"""
        print("\n=== 测试时间戳验证 ===")
        
        # 有效的时间戳
        valid_timestamps = [
            {'char': '你', 'start_time': 0.0, 'end_time': 0.5, 'index': 0},
            {'char': '好', 'start_time': 0.5, 'end_time': 1.0, 'index': 1}
        ]
        
        # 无效的时间戳（时间逻辑错误）
        invalid_timestamps = [
            {'char': '你', 'start_time': 0.5, 'end_time': 0.0, 'index': 0},  # 开始时间 > 结束时间
            {'char': '好', 'start_time': 1.0, 'end_time': 1.5, 'index': 1}
        ]
        
        # 缺少字段的时间戳
        incomplete_timestamps = [
            {'char': '你', 'start_time': 0.0},  # 缺少 end_time 和 index
        ]
        
        self.assertTrue(self.generator.validate_timestamps(valid_timestamps))
        self.assertFalse(self.generator.validate_timestamps(invalid_timestamps))
        self.assertFalse(self.generator.validate_timestamps(incomplete_timestamps))
        
        print("✓ 时间戳验证测试通过")
    
    def test_generation_methods(self):
        """测试不同的时间戳生成方法"""
        print("\n=== 测试不同时间戳生成方法 ===")
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            audio_path = f.name
        
        try:
            # 模拟音频时长
            self.generator._get_audio_duration = lambda path: self.test_audio_duration
            
            methods = ['auto', 'uniform', 'vad_estimation']
            
            for method in methods:
                print(f"测试方法: {method}")
                result = self.generator.generate_timestamps(self.test_text, audio_path, method)
                
                self.assertTrue(result['success'], f"方法 {method} 应该成功")
                self.assertIn('char_timestamps', result)
                self.assertIn('method', result)
                
                # 验证时间戳基本属性
                timestamps = result['char_timestamps']
                if timestamps:  # 有些方法可能返回空列表
                    self.assertLessEqual(len(timestamps), len(self.test_text))
                    for ts in timestamps:
                        self.assertIn('char', ts)
                        self.assertIn('start_time', ts)
                        self.assertIn('end_time', ts)
                        self.assertGreaterEqual(ts['start_time'], 0)
                        self.assertGreater(ts['end_time'], ts['start_time'])
                
                print(f"  ✓ 方法 {method} 测试通过")
        
        finally:
            try:
                os.unlink(audio_path)
            except:
                pass

class TestCacheManager(unittest.TestCase):
    """缓存管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时缓存目录
        self.temp_dir = tempfile.mkdtemp()
        self.cache = TimestampCache(cache_dir=os.path.join(self.temp_dir, 'test_cache'))
        
    def tearDown(self):
        """测试后清理"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_cache_operations(self):
        """测试缓存基本操作"""
        print("\n=== 测试缓存基本操作 ===")
        
        # 测试数据
        text = "测试文本"
        timestamps = {
            'success': True,
            'char_timestamps': [
                {'char': '测', 'start_time': 0.0, 'end_time': 0.5},
                {'char': '试', 'start_time': 0.5, 'end_time': 1.0},
                {'char': '文', 'start_time': 1.0, 'end_time': 1.5},
                {'char': '本', 'start_time': 1.5, 'end_time': 2.0}
            ],
            'method': 'test'
        }
        
        # 保存到缓存
        success = self.cache.set_timestamps(text, timestamps, 'test_engine', 'test_method')
        self.assertTrue(success)
        
        # 从缓存获取
        result = self.cache.get_timestamps(text, 'test_engine', 'test_method')
        self.assertIsNotNone(result)
        self.assertEqual(result['timestamps']['method'], 'test')
        self.assertEqual(len(result['timestamps']['char_timestamps']), 4)
        
        print("✓ 缓存基本操作测试通过")
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        print("\n=== 测试缓存键生成 ===")
        
        # 相同参数应该生成相同的键
        key1 = self.cache._generate_cache_key("文本", "engine", "method")
        key2 = self.cache._generate_cache_key("文本", "engine", "method")
        self.assertEqual(key1, key2)
        
        # 不同参数应该生成不同的键
        key3 = self.cache._generate_cache_key("文本", "engine2", "method")
        self.assertNotEqual(key1, key3)
        
        print("✓ 缓存键生成测试通过")
    
    def test_cache_stats(self):
        """测试缓存统计"""
        print("\n=== 测试缓存统计 ===")
        
        # 添加一些测试数据
        test_data = {
            'success': True,
            'char_timestamps': [],
            'method': 'test'
        }
        
        self.cache.set_timestamps("测试1", test_data, "engine1", "method1")
        self.cache.set_timestamps("测试2", test_data, "engine2", "method2")
        
        # 获取统计信息
        stats = self.cache.get_cache_stats()
        
        self.assertIn('memory_cache', stats)
        self.assertIn('file_cache', stats)
        self.assertIn('total_size_mb', stats)
        
        # 验证内存缓存统计
        memory_stats = stats['memory_cache']
        self.assertGreaterEqual(memory_stats['total_items'], 2)
        
        print("✓ 缓存统计测试通过")

class TestPerformanceOptimizer(unittest.TestCase):
    """性能优化器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.optimizer = PerformanceOptimizer()
    
    def test_timing_operations(self):
        """测试计时操作"""
        print("\n=== 测试性能计时 ===")
        
        # 开始计时
        timing_id = self.optimizer.start_timing('test_operation')
        self.assertIsNotNone(timing_id)
        
        # 模拟操作
        time.sleep(0.1)
        
        # 结束计时
        duration = self.optimizer.end_timing(timing_id, 'test_operation')
        self.assertGreater(duration, 0.05)  # 至少50ms
        self.assertLess(duration, 0.5)      # 不超过500ms
        
        # 验证统计数据
        stats = self.optimizer.get_performance_stats()
        self.assertIn('test_operation', stats)
        
        op_stats = stats['test_operation']
        self.assertEqual(op_stats['count'], 1)
        self.assertGreater(op_stats['avg_time'], 0)
        
        print("✓ 性能计时测试通过")
    
    def test_timing_decorator(self):
        """测试计时装饰器"""
        print("\n=== 测试计时装饰器 ===")
        
        from cache_manager import timing_decorator
        
        @timing_decorator('decorated_operation')
        def test_function():
            time.sleep(0.05)
            return "完成"
        
        # 执行被装饰的函数
        result = test_function()
        self.assertEqual(result, "完成")
        
        # 验证统计记录
        stats = self.optimizer.get_performance_stats()
        self.assertIn('decorated_operation', stats)
        
        print("✓ 计时装饰器测试通过")

class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        print("\n=== 测试完整工作流程 ===")
        
        # 1. 创建时间戳生成器（启用缓存）
        generator = UniversalTimestampGenerator(enable_cache=True)
        test_text = "完整测试流程"
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            audio_path = f.name
        
        try:
            # 模拟音频时长
            generator._get_audio_duration = lambda path: 4.0
            
            # 2. 第一次生成（应该计算并缓存）
            print("第一次生成时间戳...")
            start_time = time.time()
            result1 = generator.generate_timestamps(test_text, audio_path, 'uniform', 'test_engine')
            first_duration = time.time() - start_time
            
            self.assertTrue(result1['success'])
            self.assertIn('char_timestamps', result1)
            
            # 3. 第二次生成（应该从缓存获取）
            print("第二次生成时间戳（缓存）...")
            start_time = time.time()
            result2 = generator.generate_timestamps(test_text, audio_path, 'uniform', 'test_engine')
            second_duration = time.time() - start_time
            
            self.assertTrue(result2['success'])
            
            # 缓存应该更快
            self.assertLess(second_duration, first_duration)
            
            # 结果应该相同
            self.assertEqual(len(result1['char_timestamps']), len(result2['char_timestamps']))
            
            print(f"✓ 完整工作流程测试通过")
            print(f"  第一次耗时: {first_duration:.3f}秒")
            print(f"  第二次耗时: {second_duration:.3f}秒")
            print(f"  缓存提速: {(first_duration/second_duration):.1f}倍")
            
        finally:
            try:
                os.unlink(audio_path)
            except:
                pass

def run_web_api_tests():
    """运行Web API测试"""
    print("\n=== Web API 功能测试 ===")
    
    try:
        import requests
        
        # 假设服务器运行在 localhost:5000
        base_url = "http://localhost:5000"
        
        # 测试系统状态
        print("测试系统状态API...")
        try:
            response = requests.get(f"{base_url}/api/system/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 系统状态API正常: {data.get('status', {})}")
            else:
                print(f"⚠️ 系统状态API响应异常: {response.status_code}")
        except requests.exceptions.RequestException:
            print("⚠️ 无法连接到服务器，跳过Web API测试")
            return
        
        # 测试时间戳生成API
        print("测试时间戳生成API...")
        try:
            test_data = {
                "text": "API测试文本",
                "method": "uniform"
            }
            response = requests.post(f"{base_url}/api/tts/generate_with_timestamps", 
                                   json=test_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✓ 时间戳生成API正常: {len(data.get('char_timestamps', []))} 个时间戳")
                else:
                    print(f"⚠️ 时间戳生成API失败: {data.get('error')}")
            else:
                print(f"⚠️ 时间戳生成API响应异常: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 时间戳生成API请求失败: {e}")
        
        # 测试缓存统计API
        print("测试缓存统计API...")
        try:
            response = requests.get(f"{base_url}/api/cache/stats", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('cache_enabled'):
                    print("✓ 缓存统计API正常")
                else:
                    print("⚠️ 缓存系统未启用")
            else:
                print(f"⚠️ 缓存统计API响应异常: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 缓存统计API请求失败: {e}")
    
    except ImportError:
        print("⚠️ requests模块未安装，跳过Web API测试")

def main():
    """主测试函数"""
    print("🚀 开始实时字词同步功能测试")
    print("=" * 60)
    
    # 运行单元测试
    test_classes = [
        TestTimestampGenerator,
        TestCacheManager,
        TestPerformanceOptimizer,
        TestIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{'='*20} {test_class.__name__} {'='*20}")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        total_tests += result.testsRun
        passed_tests += result.testsRun - len(result.failures) - len(result.errors)
        failed_tests += len(result.failures) + len(result.errors)
        
        if result.failures:
            print("失败的测试:")
            for test, error in result.failures:
                print(f"  ✗ {test}: {error}")
        
        if result.errors:
            print("错误的测试:")
            for test, error in result.errors:
                print(f"  ✗ {test}: {error}")
    
    # 运行Web API测试
    run_web_api_tests()
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print(f"🏁 测试完成!")
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    
    if failed_tests == 0:
        print("🎉 所有测试都通过了！")
        return True
    else:
        print(f"❌ 有 {failed_tests} 个测试失败")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
