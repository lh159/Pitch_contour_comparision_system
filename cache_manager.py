# -*- coding: utf-8 -*-
"""
缓存管理器
提供时间戳数据缓存和性能优化功能
"""
import os
import json
import time
import hashlib
import pickle
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import threading

class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl  # 生存时间（秒）
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                return None
            
            # 检查过期
            if time.time() - self.cache[key]['timestamp'] > self.ttl:
                self.delete(key)
                return None
            
            # 更新访问时间
            self.access_times[key] = time.time()
            return self.cache[key]['data']
    
    def set(self, key: str, value: Any) -> bool:
        """设置缓存值"""
        with self.lock:
            # 检查容量
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # 存储数据
            self.cache[key] = {
                'data': value,
                'timestamp': time.time()
            }
            self.access_times[key] = time.time()
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def _evict_lru(self) -> None:
        """淘汰最近最少使用的项目"""
        if not self.access_times:
            return
        
        # 找到最少访问的键
        lru_key = min(self.access_times, key=self.access_times.get)
        self.delete(lru_key)
    
    def stats(self) -> Dict:
        """获取缓存统计信息"""
        with self.lock:
            now = time.time()
            valid_count = sum(1 for item in self.cache.values() 
                            if now - item['timestamp'] <= self.ttl)
            
            return {
                'total_items': len(self.cache),
                'valid_items': valid_count,
                'expired_items': len(self.cache) - valid_count,
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1),
                'size_mb': self._calculate_size() / 1024 / 1024
            }
    
    def _calculate_size(self) -> int:
        """计算缓存占用的内存大小（字节）"""
        try:
            return sum(len(pickle.dumps(item)) for item in self.cache.values())
        except:
            return 0

class FileCacheManager:
    """文件缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache", max_age_days: int = 7):
        self.cache_dir = cache_dir
        self.max_age_days = max_age_days
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def get(self, key: str) -> Optional[Any]:
        """从文件获取缓存"""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            # 检查文件年龄
            file_age = time.time() - os.path.getmtime(cache_path)
            if file_age > self.max_age_days * 24 * 3600:
                os.remove(cache_path)
                return None
            
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                return data
                
        except Exception as e:
            print(f"读取缓存文件失败: {e}")
            # 删除损坏的缓存文件
            try:
                os.remove(cache_path)
            except:
                pass
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """保存到文件缓存"""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            return True
        except Exception as e:
            print(f"写入缓存文件失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除文件缓存"""
        cache_path = self._get_cache_path(key)
        
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                return True
        except Exception as e:
            print(f"删除缓存文件失败: {e}")
        
        return False
    
    def cleanup_expired(self) -> int:
        """清理过期的缓存文件"""
        if not os.path.exists(self.cache_dir):
            return 0
        
        expired_count = 0
        cutoff_time = time.time() - self.max_age_days * 24 * 3600
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.cache_dir, filename)
                    
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            expired_count += 1
                    except OSError:
                        pass
        except Exception as e:
            print(f"清理缓存时出错: {e}")
        
        return expired_count
    
    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        if not os.path.exists(self.cache_dir):
            return {'file_count': 0, 'total_size': 0}
        
        file_count = 0
        total_size = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.cache_dir, filename)
                    file_count += 1
                    total_size += os.path.getsize(file_path)
        except Exception as e:
            print(f"获取缓存信息时出错: {e}")
        
        return {
            'file_count': file_count,
            'total_size': total_size,
            'total_size_mb': total_size / 1024 / 1024
        }

class TimestampCache:
    """时间戳专用缓存"""
    
    def __init__(self, cache_dir: str = "data/cache/timestamps"):
        self.memory_cache = MemoryCache(max_size=500, ttl=1800)  # 30分钟
        self.file_cache = FileCacheManager(cache_dir, max_age_days=30)  # 30天
    
    def _generate_cache_key(self, text: str, tts_engine: str, method: str = 'auto') -> str:
        """生成缓存键"""
        content = f"{text}:{tts_engine}:{method}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_timestamps(self, text: str, tts_engine: str = 'default', 
                      method: str = 'auto') -> Optional[Dict]:
        """获取时间戳缓存"""
        cache_key = self._generate_cache_key(text, tts_engine, method)
        
        # 先尝试内存缓存
        result = self.memory_cache.get(cache_key)
        if result is not None:
            print(f"✓ 从内存缓存获取时间戳: {text[:20]}...")
            return result
        
        # 再尝试文件缓存
        result = self.file_cache.get(cache_key)
        if result is not None:
            print(f"✓ 从文件缓存获取时间戳: {text[:20]}...")
            # 加载到内存缓存
            self.memory_cache.set(cache_key, result)
            return result
        
        return None
    
    def set_timestamps(self, text: str, timestamps: Dict, tts_engine: str = 'default', 
                      method: str = 'auto') -> bool:
        """保存时间戳到缓存"""
        cache_key = self._generate_cache_key(text, tts_engine, method)
        
        # 添加元数据
        cache_data = {
            'text': text,
            'timestamps': timestamps,
            'tts_engine': tts_engine,
            'method': method,
            'created_at': datetime.now().isoformat(),
            'cache_key': cache_key
        }
        
        # 保存到内存和文件缓存
        memory_success = self.memory_cache.set(cache_key, cache_data)
        file_success = self.file_cache.set(cache_key, cache_data)
        
        print(f"✓ 保存时间戳到缓存: {text[:20]}... (内存: {memory_success}, 文件: {file_success})")
        
        return memory_success or file_success
    
    def clear_expired(self) -> Dict:
        """清理过期缓存"""
        # 清理文件缓存
        expired_files = self.file_cache.cleanup_expired()
        
        # 内存缓存会自动过期，但可以手动清理
        memory_stats = self.memory_cache.stats()
        
        return {
            'expired_files': expired_files,
            'memory_stats': memory_stats
        }
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        memory_stats = self.memory_cache.stats()
        file_info = self.file_cache.get_cache_info()
        
        return {
            'memory_cache': memory_stats,
            'file_cache': file_info,
            'total_size_mb': memory_stats.get('size_mb', 0) + file_info.get('total_size_mb', 0)
        }

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.timing_stats = {}
        self.operation_counts = {}
        self.start_times = {}
    
    def start_timing(self, operation_name: str) -> str:
        """开始计时"""
        timing_id = f"{operation_name}_{int(time.time() * 1000000)}"
        self.start_times[timing_id] = time.time()
        return timing_id
    
    def end_timing(self, timing_id: str, operation_name: str = None) -> float:
        """结束计时并记录"""
        if timing_id not in self.start_times:
            return 0.0
        
        duration = time.time() - self.start_times[timing_id]
        del self.start_times[timing_id]
        
        # 提取操作名称
        if operation_name is None:
            operation_name = timing_id.split('_')[0]
        
        # 记录统计
        if operation_name not in self.timing_stats:
            self.timing_stats[operation_name] = []
        
        self.timing_stats[operation_name].append(duration)
        
        # 限制记录数量
        if len(self.timing_stats[operation_name]) > 100:
            self.timing_stats[operation_name] = self.timing_stats[operation_name][-50:]
        
        # 增加操作计数
        self.operation_counts[operation_name] = self.operation_counts.get(operation_name, 0) + 1
        
        return duration
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        stats = {}
        
        for operation, durations in self.timing_stats.items():
            if durations:
                stats[operation] = {
                    'count': len(durations),
                    'total_time': sum(durations),
                    'avg_time': sum(durations) / len(durations),
                    'min_time': min(durations),
                    'max_time': max(durations),
                    'recent_avg': sum(durations[-10:]) / min(len(durations), 10)
                }
        
        return stats
    
    def clear_stats(self):
        """清空统计数据"""
        self.timing_stats.clear()
        self.operation_counts.clear()
        self.start_times.clear()

# 全局缓存实例
timestamp_cache = TimestampCache()
performance_optimizer = PerformanceOptimizer()

def timing_decorator(operation_name: str):
    """性能计时装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            timing_id = performance_optimizer.start_timing(operation_name)
            try:
                result = func(*args, **kwargs)
                duration = performance_optimizer.end_timing(timing_id, operation_name)
                print(f"⏱️ {operation_name} 耗时: {duration:.3f}秒")
                return result
            except Exception as e:
                performance_optimizer.end_timing(timing_id, operation_name)
                raise e
        return wrapper
    return decorator

# 使用示例
if __name__ == '__main__':
    # 测试时间戳缓存
    cache = TimestampCache()
    
    # 模拟时间戳数据
    test_timestamps = {
        'success': True,
        'char_timestamps': [
            {'char': '你', 'start_time': 0.0, 'end_time': 0.5},
            {'char': '好', 'start_time': 0.5, 'end_time': 1.0}
        ],
        'method': 'test'
    }
    
    # 保存和获取测试
    print("=== 时间戳缓存测试 ===")
    cache.set_timestamps("你好", test_timestamps, "test_engine", "auto")
    
    result = cache.get_timestamps("你好", "test_engine", "auto")
    if result:
        print("✓ 缓存功能正常")
        print(f"缓存的时间戳数量: {len(result['timestamps']['char_timestamps'])}")
    else:
        print("✗ 缓存功能异常")
    
    # 性能统计测试
    print("\n=== 性能优化器测试 ===")
    
    @timing_decorator("test_operation")
    def test_function():
        time.sleep(0.1)
        return "测试完成"
    
    # 执行几次测试
    for i in range(3):
        test_function()
    
    stats = performance_optimizer.get_performance_stats()
    print("性能统计:", stats)
    
    # 缓存统计
    print("\n=== 缓存统计 ===")
    cache_stats = cache.get_cache_stats()
    print(json.dumps(cache_stats, indent=2, ensure_ascii=False))
