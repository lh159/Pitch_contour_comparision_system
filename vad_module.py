# -*- coding: utf-8 -*-
"""
语音活动检测(VAD)模块
集成阿里达摩院paraformer-v2进行精确的语音活动区域检测
用于改进音高曲线比对的时域对齐精度
"""
import os
import numpy as np
import librosa
import soundfile as sf
from typing import List, Tuple, Dict, Optional
import tempfile
import traceback

from config import Config

try:
    import dashscope
    from funasr import AutoModel
    DASHSCOPE_AVAILABLE = True
    FUNASR_AVAILABLE = True
except ImportError as e:
    print(f"警告: 阿里语音服务导入失败: {e}")
    DASHSCOPE_AVAILABLE = False
    FUNASR_AVAILABLE = False

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("警告: jieba分词工具未安装，文本对齐功能将受限")

class VADProcessor:
    """语音活动检测处理器 (单例模式)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if self._initialized:
            return
            
        self.api_key = Config.ALIBABA_PARAFORMER_API_KEY
        self.vad_model_name = Config.ALIBABA_VAD_MODEL
        self.asr_model_name = Config.ALIBABA_ASR_MODEL
        
        # 本地VAD模型
        self.local_vad_model = None
        self.vad_available = False
        
        # 本地ASR模型
        self.local_asr_model = None
        self.asr_available = False
        
        # 初始化服务
        self._initialize_services()
        self._initialized = True
    
    def _initialize_services(self):
        """初始化语音服务"""
        try:
            # 初始化DashScope (用于paraformer-v2)
            if DASHSCOPE_AVAILABLE and self.api_key:
                dashscope.api_key = self.api_key
                print("✓ DashScope API已配置")
            else:
                print("⚠️ DashScope API未配置或不可用")
            
            # 初始化本地VAD模型 (FunASR)
            if FUNASR_AVAILABLE:
                try:
                    print("正在加载本地VAD模型...")
                    self.local_vad_model = AutoModel(
                        model=self.vad_model_name,
                        model_revision="v2.0.4"
                    )
                    self.vad_available = True
                    print("✓ 本地VAD模型加载成功")
                except Exception as e:
                    print(f"⚠️ 本地VAD模型加载失败: {e}")
                    print("将使用基础能量检测方法")
                
                # 初始化本地ASR模型
                try:
                    print(f"正在加载本地ASR模型: {self.asr_model_name}")
                    self.local_asr_model = AutoModel(
                        model=self.asr_model_name,
                        model_revision="v2.0.4",
                        # 启用时间戳输出
                        disable_pbar=True,
                        disable_update=True
                    )
                    self.asr_available = True
                    print("✓ 本地ASR模型加载成功")
                except Exception as e:
                    print(f"⚠️ 本地ASR模型加载失败: {e}")
                    print("将使用VAD+uniform估算方法作为降级方案")
                    # 不设置为完全不可用，而是使用降级方案
            
        except Exception as e:
            print(f"VAD服务初始化失败: {e}")
            traceback.print_exc()
    
    def detect_speech_segments(self, audio_path: str, method: str = 'auto') -> List[Tuple[float, float]]:
        """
        检测音频中的语音活动段
        :param audio_path: 音频文件路径
        :param method: 检测方法 ('funasr', 'energy', 'auto')
        :return: 语音段列表 [(开始时间, 结束时间), ...]
        """
        if method == 'auto':
            # 自动选择最佳方法
            if self.vad_available:
                method = 'funasr'
            else:
                method = 'energy'
        
        print(f"使用 {method} 方法进行VAD检测...")
        
        if method == 'funasr' and self.vad_available:
            return self._detect_with_funasr(audio_path)
        else:
            return self._detect_with_energy(audio_path)
    
    def _detect_with_funasr(self, audio_path: str) -> List[Tuple[float, float]]:
        """使用FunASR VAD模型检测语音段"""
        try:
            # 使用本地VAD模型
            result = self.local_vad_model.generate(input=audio_path)
            
            # 解析结果
            speech_segments = []
            if isinstance(result, list) and len(result) > 0:
                # result格式: [{'value': [[beg1, end1], [beg2, end2], ...]}]
                if 'value' in result[0]:
                    segments = result[0]['value']
                    for segment in segments:
                        if len(segment) >= 2:
                            # 转换为秒 (FunASR返回毫秒)
                            start_time = segment[0] / 1000.0
                            end_time = segment[1] / 1000.0
                            speech_segments.append((start_time, end_time))
            
            print(f"FunASR VAD检测到 {len(speech_segments)} 个语音段")
            return speech_segments
            
        except Exception as e:
            print(f"FunASR VAD检测失败: {e}")
            # 降级到能量检测
            return self._detect_with_energy(audio_path)
    
    def _detect_with_energy(self, audio_path: str) -> List[Tuple[float, float]]:
        """使用能量阈值方法检测语音段"""
        try:
            # 加载音频
            y, sr = librosa.load(audio_path, sr=None)
            
            # 计算短时能量
            frame_length = int(0.025 * sr)  # 25ms帧
            hop_length = int(0.010 * sr)    # 10ms跳跃
            
            # 计算RMS能量
            rms = librosa.feature.rms(
                y=y, 
                frame_length=frame_length, 
                hop_length=hop_length
            )[0]
            
            # 动态阈值
            energy_mean = np.mean(rms)
            energy_std = np.std(rms)
            threshold = max(Config.VAD_ENERGY_THRESHOLD, 
                          energy_mean - 0.5 * energy_std)
            
            # 检测语音帧
            speech_frames = rms > threshold
            
            # 转换为时间段
            times = librosa.frames_to_time(
                np.arange(len(speech_frames)), 
                sr=sr, 
                hop_length=hop_length
            )
            
            # 合并连续的语音段
            speech_segments = self._merge_segments(
                times, speech_frames, 
                min_duration=Config.VAD_MIN_SPEECH_DURATION,
                max_gap=Config.VAD_MAX_SILENCE_DURATION
            )
            
            print(f"能量VAD检测到 {len(speech_segments)} 个语音段")
            return speech_segments
            
        except Exception as e:
            print(f"能量VAD检测失败: {e}")
            # 返回整个音频作为一个语音段
            try:
                duration = librosa.get_duration(filename=audio_path)
                return [(0.0, duration)]
            except:
                return [(0.0, 10.0)]  # 默认10秒
    
    def _merge_segments(self, times: np.ndarray, speech_frames: np.ndarray, 
                       min_duration: float = 0.1, max_gap: float = 0.5) -> List[Tuple[float, float]]:
        """合并连续的语音段"""
        segments = []
        in_speech = False
        start_time = None
        
        for i, (time, is_speech) in enumerate(zip(times, speech_frames)):
            if is_speech and not in_speech:
                # 语音开始
                start_time = time
                in_speech = True
            elif not is_speech and in_speech:
                # 语音结束
                if start_time is not None:
                    duration = time - start_time
                    if duration >= min_duration:
                        segments.append((start_time, time))
                in_speech = False
        
        # 处理最后一个段
        if in_speech and start_time is not None:
            duration = times[-1] - start_time
            if duration >= min_duration:
                segments.append((start_time, times[-1]))
        
        # 合并间隔过小的段
        merged_segments = []
        for start, end in segments:
            if not merged_segments:
                merged_segments.append((start, end))
            else:
                last_start, last_end = merged_segments[-1]
                gap = start - last_end
                if gap <= max_gap:
                    # 合并段
                    merged_segments[-1] = (last_start, end)
                else:
                    merged_segments.append((start, end))
        
        return merged_segments
    
    def get_speech_regions_timestamps(self, audio_path: str) -> Dict:
        """
        获取语音区域的详细时间戳信息
        :param audio_path: 音频文件路径
        :return: 包含各种时间戳信息的字典
        """
        try:
            # 检测语音段
            speech_segments = self.detect_speech_segments(audio_path)
            
            # 加载音频获取总时长
            duration = librosa.get_duration(filename=audio_path)
            
            # 计算统计信息
            total_speech_duration = sum(end - start for start, end in speech_segments)
            speech_ratio = total_speech_duration / duration if duration > 0 else 0
            
            # 如果使用paraformer-v2还可以获取更详细的时间戳信息
            detailed_timestamps = None
            if DASHSCOPE_AVAILABLE and self.api_key:
                detailed_timestamps = self._get_detailed_timestamps(audio_path)
            
            return {
                'speech_segments': speech_segments,
                'total_duration': duration,
                'speech_duration': total_speech_duration,
                'silence_duration': duration - total_speech_duration,
                'speech_ratio': speech_ratio,
                'detailed_timestamps': detailed_timestamps,
                'segment_count': len(speech_segments)
            }
            
        except Exception as e:
            print(f"获取语音时间戳失败: {e}")
            return {
                'speech_segments': [(0.0, 0.0)],
                'total_duration': 0.0,
                'speech_duration': 0.0,
                'silence_duration': 0.0,
                'speech_ratio': 0.0,
                'detailed_timestamps': None,
                'segment_count': 0
            }
    
    def _get_detailed_timestamps(self, audio_path: str) -> Optional[Dict]:
        """使用paraformer-v2获取详细的词级时间戳(需要上传到云端)"""
        try:
            # 注意: paraformer-v2需要音频文件可通过公网访问
            # 这里仅作为示例，实际使用时需要先上传音频文件到OSS等服务
            print("获取详细时间戳需要将音频上传到云端，当前跳过此功能")
            return None
            
        except Exception as e:
            print(f"获取详细时间戳失败: {e}")
            return None
    
    def recognize_speech_with_timestamps(self, audio_path: str, text: str = None) -> Optional[Dict]:
        """
        使用ASR模型识别语音并获取时间戳
        :param audio_path: 音频文件路径
        :param text: 可选的文本，用于强制对齐获取更精确的时间戳
        :return: 识别结果和时间戳信息
        """
        if not self.asr_available:
            print("ASR模型不可用，无法获取语音识别结果")
            return None
        
        try:
            print("正在进行语音识别...")
            
            # 读取音频文件数据
            import soundfile as sf
            if isinstance(audio_path, str) and os.path.exists(audio_path):
                print(f"从文件读取音频: {audio_path}")
                try:
                    # 尝试使用soundfile读取
                    audio_data, sample_rate = sf.read(audio_path)
                    print(f"音频数据形状: {audio_data.shape}, 采样率: {sample_rate}")
                    audio_input = audio_data
                except Exception as e:
                    print(f"soundfile读取失败，尝试直接使用文件路径: {e}")
                    audio_input = audio_path
            else:
                audio_input = audio_path
                
            # 准备ASR参数
            asr_params = {
                "input": audio_input,
                "cache": {},
                "language": "auto",  # 自动检测语言
                "use_itn": True,  # 启用反向文本规范化
                "batch_size_s": 300,  # 批处理大小
                "merge_vad": True,  # 合并VAD结果 
                "merge_length_s": 15,  # 合并段落长度
                "word_timestamp": True,  # 启用词级时间戳
                "return_raw_text": False,  # 返回结构化结果
                "is_final": True,  # 最终结果
                "output_dir": None  # 不输出到文件
            }
            
            # 如果提供了文本，添加强制对齐参数
            if text:
                print(f"使用强制对齐模式，目标文本: {text}")
                asr_params["text"] = text
                asr_params["hotword"] = text  # 添加热词提高准确度
            
            # funasr的generate方法调用
            result = self.local_asr_model.generate(**asr_params)
            
            if isinstance(result, list) and len(result) > 0:
                # 处理识别结果
                recognition_result = result[0]
                
                # 调试输出：打印完整结果结构
                print("🔍 ASR识别结果结构:")
                print(f"结果类型: {type(recognition_result)}")
                print(f"结果键: {list(recognition_result.keys()) if isinstance(recognition_result, dict) else '非字典类型'}")
                if isinstance(recognition_result, dict):
                    for key, value in recognition_result.items():
                        print(f"  {key}: {type(value)} - {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
                        # 如果值是字典或列表，进一步探索
                        if isinstance(value, dict):
                            print(f"    字典键: {list(value.keys())}")
                            for sub_key, sub_value in value.items():
                                print(f"      {sub_key}: {type(sub_value)} - {str(sub_value)[:50]}{'...' if len(str(sub_value)) > 50 else ''}")
                        elif isinstance(value, list) and len(value) > 0:
                            print(f"    列表长度: {len(value)}")
                            if len(value) > 0:
                                print(f"    第一个元素: {type(value[0])} - {str(value[0])[:50]}{'...' if len(str(value[0])) > 50 else ''}")
                
                # 同时打印整个result的结构
                print("\n🔍 完整result结构:")
                print(f"result类型: {type(result)}")
                print(f"result长度: {len(result) if isinstance(result, list) else 'N/A'}")
                
                # 提取文本
                recognized_text = recognition_result.get('text', '')
                
                # 提取时间戳 (如果可用)
                timestamps = []
                
                # 尝试多种时间戳格式
                timestamp_fields = ['timestamp', 'timestamps', 'word_info', 'word_timestamp']
                timestamp_data = None
                
                for field in timestamp_fields:
                    if field in recognition_result:
                        timestamp_data = recognition_result[field]
                        print(f"找到时间戳字段: {field}")
                        break
                
                if timestamp_data:
                    print(f"时间戳数据类型: {type(timestamp_data)}")
                    print(f"时间戳数据内容: {timestamp_data}")
                    
                    if isinstance(timestamp_data, list):
                        for i, ts_item in enumerate(timestamp_data):
                            try:
                                if isinstance(ts_item, list) and len(ts_item) >= 3:
                                    # 格式1: [word, start_time, end_time]
                                    word = str(ts_item[0])
                                    start_time = float(ts_item[1]) / 1000.0  # 转换为秒
                                    end_time = float(ts_item[2]) / 1000.0
                                    timestamps.append({
                                        'word': word,
                                        'start': start_time,
                                        'end': end_time
                                    })
                                elif isinstance(ts_item, dict):
                                    # 格式2: {'word': 'xxx', 'start': xxx, 'end': xxx}
                                    word = str(ts_item.get('word', ts_item.get('text', '')))
                                    start_time = float(ts_item.get('start', ts_item.get('start_time', 0))) / 1000.0
                                    end_time = float(ts_item.get('end', ts_item.get('end_time', 0))) / 1000.0
                                    timestamps.append({
                                        'word': word,
                                        'start': start_time,
                                        'end': end_time
                                    })
                            except (ValueError, KeyError, IndexError) as e:
                                print(f"解析时间戳项 {i} 失败: {e}, 内容: {ts_item}")
                                continue
                
                print(f"识别文本: {recognized_text}")
                print(f"时间戳数量: {len(timestamps)}")
                
                return {
                    'text': recognized_text,
                    'timestamps': timestamps,
                    'confidence': recognition_result.get('confidence', 0.0),
                    'raw_result': recognition_result
                }
            
            return None
            
        except Exception as e:
            print(f"语音识别失败: {e}")
            traceback.print_exc()
            return None
    
    def align_text_with_vad(self, expected_text: str, audio_path: str) -> Dict:
        """
        将期望文本与语音活动区域和识别结果进行对齐
        :param expected_text: 期望的文本（如TTS的原文）
        :param audio_path: 音频文件路径
        :return: 对齐结果
        """
        try:
            print(f"正在对齐文本: {expected_text}")
            
            # 1. 获取VAD结果
            vad_segments = self.detect_speech_segments(audio_path)
            
            # 2. 获取ASR识别结果（使用期望文本进行强制对齐）
            asr_result = self.recognize_speech_with_timestamps(audio_path, expected_text)
            
            # 3. 准备文本对齐
            aligned_result = {
                'expected_text': expected_text,
                'vad_segments': vad_segments,
                'asr_result': asr_result,
                'text_alignment': []
            }
            
            if asr_result:
                if asr_result['timestamps'] and len(asr_result['timestamps']) > 0:
                    # 4a. 有详细时间戳时的精确对齐
                    alignment = self._align_expected_with_recognized(
                        expected_text, 
                        asr_result['text'],
                        asr_result['timestamps']
                    )
                else:
                    # 4b. 无详细时间戳时的基础对齐
                    alignment = self._create_basic_text_alignment(
                        expected_text,
                        asr_result['text'],
                        vad_segments
                    )
                
                aligned_result['text_alignment'] = alignment
                
                # 5. 将对齐结果映射到VAD段
                aligned_result['vad_text_mapping'] = self._map_text_to_vad_segments(
                    alignment, vad_segments
                )
            
            return aligned_result
            
        except Exception as e:
            print(f"文本对齐失败: {e}")
            traceback.print_exc()
            return {
                'expected_text': expected_text,
                'vad_segments': vad_segments if 'vad_segments' in locals() else [],
                'asr_result': None,
                'text_alignment': [],
                'error': str(e)
            }
    
    def _align_expected_with_recognized(self, expected: str, recognized: str, timestamps: List[Dict]) -> List[Dict]:
        """
        对齐期望文本和识别文本
        :param expected: 期望文本
        :param recognized: 识别文本  
        :param timestamps: 识别结果的时间戳
        :return: 对齐结果
        """
        try:
            # 清理和分词
            if JIEBA_AVAILABLE:
                expected_words = list(jieba.cut(expected.strip()))
                recognized_words = list(jieba.cut(recognized.strip()))
            else:
                # 简单按字符分割
                expected_words = list(expected.strip())
                recognized_words = list(recognized.strip())
            
            # 简单的对齐算法（可以改进为更复杂的算法）
            alignment = []
            expected_idx = 0
            timestamp_idx = 0
            
            while expected_idx < len(expected_words) and timestamp_idx < len(timestamps):
                expected_word = expected_words[expected_idx]
                timestamp_item = timestamps[timestamp_idx]
                recognized_word = timestamp_item['word']
                
                # 字符匹配
                if expected_word == recognized_word or expected_word in recognized_word:
                    # 完全匹配
                    alignment.append({
                        'expected_word': expected_word,
                        'recognized_word': recognized_word,
                        'start_time': timestamp_item['start'],
                        'end_time': timestamp_item['end'],
                        'match_type': 'exact'
                    })
                    expected_idx += 1
                    timestamp_idx += 1
                
                elif recognized_word in expected_word:
                    # 部分匹配
                    alignment.append({
                        'expected_word': expected_word,
                        'recognized_word': recognized_word,
                        'start_time': timestamp_item['start'],
                        'end_time': timestamp_item['end'],
                        'match_type': 'partial'
                    })
                    expected_idx += 1
                    timestamp_idx += 1
                
                else:
                    # 不匹配，可能是插入或删除
                    if len(recognized_word) > len(expected_word):
                        # 识别结果更长，可能是插入
                        alignment.append({
                            'expected_word': '',
                            'recognized_word': recognized_word,
                            'start_time': timestamp_item['start'],
                            'end_time': timestamp_item['end'],
                            'match_type': 'insertion'
                        })
                        timestamp_idx += 1
                    else:
                        # 期望文本更长，可能是删除
                        alignment.append({
                            'expected_word': expected_word,
                            'recognized_word': '',
                            'start_time': None,
                            'end_time': None,
                            'match_type': 'deletion'
                        })
                        expected_idx += 1
            
            # 处理剩余的期望词汇（删除）
            while expected_idx < len(expected_words):
                alignment.append({
                    'expected_word': expected_words[expected_idx],
                    'recognized_word': '',
                    'start_time': None,
                    'end_time': None,
                    'match_type': 'deletion'
                })
                expected_idx += 1
            
            # 处理剩余的识别词汇（插入）
            while timestamp_idx < len(timestamps):
                timestamp_item = timestamps[timestamp_idx]
                alignment.append({
                    'expected_word': '',
                    'recognized_word': timestamp_item['word'],
                    'start_time': timestamp_item['start'],
                    'end_time': timestamp_item['end'],
                    'match_type': 'insertion'
                })
                timestamp_idx += 1
            
            return alignment
            
        except Exception as e:
            print(f"文本对齐处理失败: {e}")
            return []
    
    def _create_basic_text_alignment(self, expected: str, recognized: str, vad_segments: List[Tuple]) -> List[Dict]:
        """
        创建基础文本对齐（无详细时间戳时使用）
        :param expected: 期望文本
        :param recognized: 识别文本
        :param vad_segments: VAD语音段
        :return: 基础对齐结果
        """
        try:
            print("🔤 使用基础文本对齐（无详细时间戳）")
            
            # 清理和分词
            if JIEBA_AVAILABLE:
                expected_words = list(jieba.cut(expected.strip()))
                recognized_words = list(jieba.cut(recognized.strip()))
            else:
                # 简单按字符分割
                expected_words = list(expected.strip())
                recognized_words = list(recognized.strip())
            
            alignment = []
            
            # 如果有VAD段，将文本均匀分布到语音段中
            if vad_segments and len(vad_segments) > 0:
                # 计算总的语音时长
                total_speech_duration = sum(end - start for start, end in vad_segments)
                
                # 按字符数量分配时间
                total_chars = len(expected.replace(' ', ''))
                if total_chars > 0:
                    char_duration = total_speech_duration / total_chars
                    
                    current_time = vad_segments[0][0]  # 从第一个语音段开始
                    segment_idx = 0
                    segment_time_left = vad_segments[0][1] - vad_segments[0][0]
                    
                    for word in expected_words:
                        word_duration = len(word) * char_duration
                        
                        # 检查当前语音段是否有足够时间
                        while segment_time_left < word_duration and segment_idx < len(vad_segments) - 1:
                            # 移动到下一个语音段
                            segment_idx += 1
                            current_time = vad_segments[segment_idx][0]
                            segment_time_left = vad_segments[segment_idx][1] - vad_segments[segment_idx][0]
                        
                        start_time = current_time
                        end_time = min(current_time + word_duration, vad_segments[segment_idx][1])
                        
                        # 确定匹配类型
                        if word in recognized:
                            match_type = 'exact'
                        elif any(char in recognized for char in word):
                            match_type = 'partial'
                        else:
                            match_type = 'mismatch'
                        
                        alignment.append({
                            'expected_word': word,
                            'recognized_word': word if match_type == 'exact' else '?',
                            'start_time': start_time,
                            'end_time': end_time,
                            'match_type': match_type
                        })
                        
                        current_time = end_time
                        segment_time_left -= word_duration
            
            else:
                # 如果没有VAD段，创建简单的匹配记录
                for word in expected_words:
                    match_type = 'exact' if word in recognized else 'mismatch'
                    alignment.append({
                        'expected_word': word,
                        'recognized_word': word if match_type == 'exact' else '?',
                        'start_time': 0,
                        'end_time': 1,
                        'match_type': match_type
                    })
            
            print(f"✓ 基础文本对齐完成，生成 {len(alignment)} 个对齐项")
            return alignment
            
        except Exception as e:
            print(f"基础文本对齐失败: {e}")
            return []
    
    def _map_text_to_vad_segments(self, alignment: List[Dict], vad_segments: List[Tuple[float, float]]) -> List[Dict]:
        """
        将文本对齐结果映射到VAD段
        :param alignment: 文本对齐结果
        :param vad_segments: VAD语音段
        :return: 映射结果
        """
        try:
            vad_mapping = []
            
            for vad_start, vad_end in vad_segments:
                # 找到该VAD段内的所有文本
                segment_words = []
                
                for align_item in alignment:
                    if (align_item['start_time'] is not None and 
                        align_item['end_time'] is not None):
                        word_start = align_item['start_time']
                        word_end = align_item['end_time']
                        
                        # 检查词汇是否在当前VAD段内
                        if (word_start >= vad_start and word_start <= vad_end) or \
                           (word_end >= vad_start and word_end <= vad_end) or \
                           (word_start <= vad_start and word_end >= vad_end):
                            segment_words.append(align_item)
                
                # 构建该段的文本
                expected_text = ''.join([w['expected_word'] for w in segment_words if w['expected_word']])
                recognized_text = ''.join([w['recognized_word'] for w in segment_words if w['recognized_word']])
                
                vad_mapping.append({
                    'vad_start': vad_start,
                    'vad_end': vad_end,
                    'expected_text': expected_text,
                    'recognized_text': recognized_text,
                    'words': segment_words,
                    'word_count': len(segment_words),
                    'match_quality': self._calculate_segment_match_quality(segment_words)
                })
            
            return vad_mapping
            
        except Exception as e:
            print(f"VAD文本映射失败: {e}")
            return []
    
    def _calculate_segment_match_quality(self, words: List[Dict]) -> float:
        """计算段落匹配质量"""
        if not words:
            return 0.0
        
        exact_matches = sum(1 for w in words if w['match_type'] == 'exact')
        partial_matches = sum(1 for w in words if w['match_type'] == 'partial')
        total_words = len(words)
        
        # 计算匹配质量分数
        quality = (exact_matches + 0.5 * partial_matches) / total_words
        return quality
    
    def extract_speech_audio(self, audio_path: str, output_path: str = None) -> str:
        """
        提取纯语音音频（去除静音段）
        :param audio_path: 输入音频路径
        :param output_path: 输出音频路径
        :return: 输出文件路径
        """
        try:
            # 检测语音段
            speech_segments = self.detect_speech_segments(audio_path)
            
            if not speech_segments:
                print("未检测到语音段，返回原音频")
                return audio_path
            
            # 加载音频
            y, sr = librosa.load(audio_path, sr=None)
            
            # 提取语音段
            speech_audio = []
            for start_time, end_time in speech_segments:
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                segment = y[start_sample:end_sample]
                speech_audio.append(segment)
            
            # 合并所有语音段
            if speech_audio:
                combined_audio = np.concatenate(speech_audio)
            else:
                combined_audio = y  # 如果没有检测到，使用原音频
            
            # 保存结果
            if output_path is None:
                output_path = audio_path.replace('.wav', '_speech_only.wav')
            
            sf.write(output_path, combined_audio, sr)
            print(f"提取的纯语音音频已保存到: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"提取语音音频失败: {e}")
            return audio_path  # 返回原文件

class VADComparator:
    """基于VAD的音高比对增强器"""
    
    def __init__(self):
        self.vad_processor = VADProcessor()
    
    def align_speech_regions(self, standard_audio: str, user_audio: str) -> Dict:
        """
        基于VAD检测结果对齐两个音频的语音区域
        :param standard_audio: 标准音频路径
        :param user_audio: 用户音频路径
        :return: 对齐结果
        """
        try:
            print("🎯 开始VAD增强的音频对齐...")
            
            # 检测两个音频的语音区域
            std_info = self.vad_processor.get_speech_regions_timestamps(standard_audio)
            user_info = self.vad_processor.get_speech_regions_timestamps(user_audio)
            
            print(f"标准音频: {len(std_info['speech_segments'])} 个语音段, "
                  f"语音比例: {std_info['speech_ratio']:.2%}")
            print(f"用户音频: {len(user_info['speech_segments'])} 个语音段, "
                  f"语音比例: {user_info['speech_ratio']:.2%}")
            
            # 提取纯语音音频用于更精确的音高比对
            std_speech_path = self.vad_processor.extract_speech_audio(
                standard_audio, 
                standard_audio.replace('.wav', '_vad_speech.wav')
            )
            user_speech_path = self.vad_processor.extract_speech_audio(
                user_audio,
                user_audio.replace('.wav', '_vad_speech.wav')
            )
            
            return {
                'success': True,
                'standard_info': std_info,
                'user_info': user_info,
                'standard_speech_audio': std_speech_path,
                'user_speech_audio': user_speech_path,
                'alignment_quality': self._calculate_alignment_quality(std_info, user_info)
            }
            
        except Exception as e:
            print(f"VAD对齐失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'standard_speech_audio': standard_audio,
                'user_speech_audio': user_audio
            }
    
    def _calculate_alignment_quality(self, std_info: Dict, user_info: Dict) -> Dict:
        """计算对齐质量指标"""
        try:
            # 语音比例差异
            ratio_diff = abs(std_info['speech_ratio'] - user_info['speech_ratio'])
            
            # 段数差异
            segment_diff = abs(std_info['segment_count'] - user_info['segment_count'])
            
            # 时长差异
            duration_diff = abs(std_info['speech_duration'] - user_info['speech_duration'])
            
            # 计算质量评分 (0-1，越高越好)
            ratio_score = max(0, 1 - ratio_diff * 2)  # 比例差异权重
            segment_score = max(0, 1 - segment_diff * 0.1)  # 段数差异权重
            duration_score = max(0, 1 - duration_diff * 0.1)  # 时长差异权重
            
            overall_score = (ratio_score + segment_score + duration_score) / 3
            
            return {
                'overall_score': overall_score,
                'ratio_difference': ratio_diff,
                'segment_difference': segment_diff,
                'duration_difference': duration_diff,
                'quality_level': 'high' if overall_score > 0.8 else 
                               'medium' if overall_score > 0.6 else 'low'
            }
            
        except Exception as e:
            return {
                'overall_score': 0.5,
                'quality_level': 'unknown',
                'error': str(e)
            }

# 使用示例和测试
if __name__ == '__main__':
    import sys
    
    # 创建VAD处理器
    vad = VADProcessor()
    
    print("=== VAD模块状态 ===")
    print(f"DashScope可用: {DASHSCOPE_AVAILABLE}")
    print(f"FunASR可用: {FUNASR_AVAILABLE}")
    print(f"本地VAD模型: {'可用' if vad.vad_available else '不可用'}")
    
    # 如果提供了测试音频，进行测试
    if len(sys.argv) > 1:
        test_audio = sys.argv[1]
        if os.path.exists(test_audio):
            print(f"\n=== 测试VAD: {test_audio} ===")
            
            # 检测语音段
            segments = vad.detect_speech_segments(test_audio)
            print(f"检测到语音段: {segments}")
            
            # 获取详细信息
            info = vad.get_speech_regions_timestamps(test_audio)
            print(f"总时长: {info['total_duration']:.2f}s")
            print(f"语音时长: {info['speech_duration']:.2f}s")
            print(f"语音比例: {info['speech_ratio']:.2%}")
            
            # 提取纯语音
            speech_path = vad.extract_speech_audio(test_audio)
            print(f"纯语音文件: {speech_path}")
        else:
            print(f"测试音频文件不存在: {test_audio}")
    else:
        print("\n提示: 可以使用以下命令进行测试:")
        print("python vad_module.py test_audio.wav")
