#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fun-ASR时间戳处理模块
使用阿里云Fun-ASR服务获取TTS音频的详细时间戳信息
"""

import os
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
from http import HTTPStatus
from dashscope.audio.asr import Transcription
import dashscope


class FunASRProcessor:
    """Fun-ASR时间戳处理器"""
    
    def __init__(self, api_key: str = None):
        """
        初始化Fun-ASR处理器
        :param api_key: 阿里云API Key，如果为None则从环境变量获取
        """
        self.api_key = api_key or os.environ.get('DASHSCOPE_API_KEY')
        if self.api_key:
            dashscope.api_key = self.api_key
        else:
            print("⚠️ 警告: 未设置DASHSCOPE_API_KEY，Fun-ASR功能将不可用")
            print("请设置环境变量或在初始化时提供API Key")
    
    def upload_audio_to_temp_server(self, audio_path: str) -> Optional[str]:
        """
        将本地音频文件上传到临时服务器获取公网URL
        这里使用一个简单的文件服务器或OSS服务
        
        注意：在实际使用中，您需要：
        1. 搭建一个简单的文件服务器
        2. 或者使用阿里云OSS等对象存储服务
        3. 或者使用其他公网可访问的存储方案
        
        :param audio_path: 本地音频文件路径
        :return: 公网可访问的URL
        """
        # 这里是一个示例实现，实际需要根据您的基础设施调整
        try:
            # 方案1：如果您有自己的文件服务器
            # 可以通过POST请求上传文件
            
            # 方案2：使用阿里云OSS（推荐）
            # from oss2 import Auth, Bucket
            # auth = Auth('access_key_id', 'access_key_secret')
            # bucket = Bucket(auth, 'endpoint', 'bucket_name')
            # bucket.put_object_from_file('audio_file.wav', audio_path)
            # return f"https://{bucket_name}.{endpoint}/audio_file.wav"
            
            # 临时方案：返回本地文件路径（仅用于测试）
            print(f"⚠️ 需要将 {audio_path} 上传到公网可访问的位置")
            print("请参考Fun-ASR文档配置文件上传服务")
            return None
            
        except Exception as e:
            print(f"上传音频文件失败: {e}")
            return None
    
    def get_timestamps_from_audio(self, audio_url: str, expected_text: str = None) -> Optional[Dict]:
        """
        使用Fun-ASR获取音频的时间戳信息
        :param audio_url: 公网可访问的音频URL
        :param expected_text: 期望的文本，用于提高识别准确度
        :return: 包含时间戳信息的结果
        """
        if not self.api_key:
            print("❌ API Key未设置，无法使用Fun-ASR服务")
            return None
        
        try:
            print(f"正在使用Fun-ASR处理音频: {audio_url}")
            
            # 构建请求参数
            params = {
                'model': 'fun-asr',
                'file_urls': [audio_url],
                'language_hints': ['zh'],  # 中文识别
                'word_timestamps': True,   # 启用词级时间戳
                'speaker_diarization': False,  # 不需要说话人分离
                'special_word_filter': False,  # 不过滤特殊词汇
                'audio_event_detection': False,  # 不需要音频事件检测
            }
            
            # 如果提供了期望文本，可以作为热词提高准确度
            if expected_text:
                params['vocabulary_id'] = expected_text  # 这个参数可能需要调整
            
            # 异步提交任务
            task_response = Transcription.async_call(**params)
            
            if task_response.status_code != HTTPStatus.OK:
                print(f"提交任务失败: {task_response.message}")
                return None
            
            print(f"任务提交成功，任务ID: {task_response.output.task_id}")
            
            # 等待任务完成
            transcription_response = Transcription.wait(task=task_response.output.task_id)
            
            if transcription_response.status_code != HTTPStatus.OK:
                print(f"获取结果失败: {transcription_response.message}")
                return None
            
            # 解析结果
            result = transcription_response.output
            print(f"任务状态: {result.task_status}")
            
            if result.task_status == "SUCCEEDED":
                return self._parse_asr_result(result)
            else:
                print(f"ASR任务失败: {result}")
                return None
                
        except Exception as e:
            print(f"Fun-ASR处理失败: {e}")
            return None
    
    def _parse_asr_result(self, result) -> Dict:
        """
        解析Fun-ASR的结果，提取时间戳信息
        :param result: Fun-ASR的识别结果
        :return: 格式化的时间戳信息
        """
        try:
            parsed_result = {
                'task_id': result.task_id,
                'task_status': result.task_status,
                'files': [],
                'total_text': '',
                'word_timestamps': [],
                'sentence_timestamps': []
            }
            
            # 处理每个文件的结果
            for file_result in result.results:
                if file_result.subtask_status == "SUCCEEDED":
                    # 下载转录结果
                    transcription_url = file_result.transcription_url
                    transcription_data = self._download_transcription(transcription_url)
                    
                    if transcription_data:
                        file_info = {
                            'file_url': file_result.file_url,
                            'transcription': transcription_data
                        }
                        parsed_result['files'].append(file_info)
                        
                        # 提取文本和时间戳
                        text, word_ts, sent_ts = self._extract_timestamps(transcription_data)
                        parsed_result['total_text'] += text
                        parsed_result['word_timestamps'].extend(word_ts)
                        parsed_result['sentence_timestamps'].extend(sent_ts)
                
            return parsed_result
            
        except Exception as e:
            print(f"解析ASR结果失败: {e}")
            return None
    
    def _download_transcription(self, url: str) -> Optional[Dict]:
        """
        下载转录结果文件
        :param url: 转录结果URL
        :return: 转录数据
        """
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"下载转录结果失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"下载转录结果异常: {e}")
            return None
    
    def _extract_timestamps(self, transcription_data: Dict) -> Tuple[str, List[Dict], List[Dict]]:
        """
        从转录数据中提取时间戳信息
        :param transcription_data: 转录数据
        :return: (完整文本, 词级时间戳, 句子级时间戳)
        """
        full_text = ""
        word_timestamps = []
        sentence_timestamps = []
        
        try:
            # Fun-ASR的结果格式可能因版本而异，需要根据实际返回格式调整
            if 'transcripts' in transcription_data:
                for transcript in transcription_data['transcripts']:
                    if 'words' in transcript:
                        for word_info in transcript['words']:
                            word_timestamps.append({
                                'word': word_info.get('word', ''),
                                'start_time': word_info.get('start_time', 0),
                                'end_time': word_info.get('end_time', 0),
                                'confidence': word_info.get('confidence', 1.0)
                            })
                            full_text += word_info.get('word', '')
                    
                    if 'sentences' in transcript:
                        for sent_info in transcript['sentences']:
                            sentence_timestamps.append({
                                'text': sent_info.get('text', ''),
                                'start_time': sent_info.get('start_time', 0),
                                'end_time': sent_info.get('end_time', 0)
                            })
            
            # 如果没有获取到时间戳，尝试其他格式
            elif 'results' in transcription_data:
                # 处理其他可能的格式
                pass
                
        except Exception as e:
            print(f"提取时间戳失败: {e}")
        
        return full_text, word_timestamps, sentence_timestamps
    
    def process_tts_audio_with_text(self, audio_path: str, original_text: str) -> Optional[Dict]:
        """
        处理TTS生成的音频，获取与原始文本对应的时间戳
        :param audio_path: TTS生成的音频文件路径
        :param original_text: 生成TTS时使用的原始文本
        :return: 时间戳对齐结果
        """
        print(f"正在处理TTS音频: {audio_path}")
        print(f"原始文本: {original_text}")
        
        # 1. 上传音频获取公网URL
        audio_url = self.upload_audio_to_temp_server(audio_path)
        if not audio_url:
            print("❌ 无法获取音频的公网URL，请配置文件上传服务")
            return None
        
        # 2. 使用Fun-ASR获取时间戳
        asr_result = self.get_timestamps_from_audio(audio_url, original_text)
        if not asr_result:
            print("❌ Fun-ASR处理失败")
            return None
        
        # 3. 对齐原始文本和识别结果
        aligned_result = self._align_text_with_timestamps(original_text, asr_result)
        
        return aligned_result
    
    def _align_text_with_timestamps(self, original_text: str, asr_result: Dict) -> Dict:
        """
        将原始文本与ASR时间戳结果对齐
        :param original_text: 原始文本
        :param asr_result: ASR识别结果
        :return: 对齐后的结果
        """
        try:
            # 简单的字符级对齐
            aligned_chars = []
            recognized_text = asr_result.get('total_text', '')
            word_timestamps = asr_result.get('word_timestamps', [])
            
            # 如果有词级时间戳，进行对齐
            if word_timestamps:
                word_index = 0
                char_index = 0
                
                for char in original_text:
                    if word_index < len(word_timestamps):
                        current_word = word_timestamps[word_index]
                        
                        # 检查当前字符是否在当前词中
                        if char_index < len(current_word['word']) and char == current_word['word'][char_index]:
                            # 线性插值计算字符的时间戳
                            word_duration = current_word['end_time'] - current_word['start_time']
                            char_progress = char_index / len(current_word['word'])
                            char_time = current_word['start_time'] + word_duration * char_progress
                            
                            aligned_chars.append({
                                'char': char,
                                'timestamp': char_time,
                                'word_info': current_word
                            })
                            
                            char_index += 1
                            if char_index >= len(current_word['word']):
                                word_index += 1
                                char_index = 0
                        else:
                            # 字符不匹配，可能是识别错误或文本差异
                            aligned_chars.append({
                                'char': char,
                                'timestamp': None,
                                'word_info': None
                            })
                    else:
                        # 超出了识别结果范围
                        aligned_chars.append({
                            'char': char,
                            'timestamp': None,
                            'word_info': None
                        })
            
            return {
                'original_text': original_text,
                'asr_result': asr_result,
                'aligned_chars': aligned_chars,
                'alignment_quality': self._calculate_alignment_quality(aligned_chars)
            }
            
        except Exception as e:
            print(f"文本时间戳对齐失败: {e}")
            return {
                'original_text': original_text,
                'asr_result': asr_result,
                'aligned_chars': [],
                'alignment_quality': 0.0
            }
    
    def _calculate_alignment_quality(self, aligned_chars: List[Dict]) -> float:
        """
        计算对齐质量
        :param aligned_chars: 对齐后的字符列表
        :return: 对齐质量分数 (0-1)
        """
        if not aligned_chars:
            return 0.0
        
        aligned_count = sum(1 for char_info in aligned_chars if char_info['timestamp'] is not None)
        return aligned_count / len(aligned_chars)


# 使用示例和测试代码
if __name__ == "__main__":
    # 测试Fun-ASR处理器
    processor = FunASRProcessor()
    
    # 测试音频文件（需要是公网可访问的URL）
    test_audio_url = "https://your-domain.com/test_audio.wav"
    test_text = "今天天气很好"
    
    print("测试Fun-ASR时间戳提取...")
    result = processor.get_timestamps_from_audio(test_audio_url, test_text)
    
    if result:
        print("✅ Fun-ASR处理成功")
        print(f"识别文本: {result.get('total_text', '')}")
        print(f"词级时间戳数量: {len(result.get('word_timestamps', []))}")
    else:
        print("❌ Fun-ASR处理失败")
