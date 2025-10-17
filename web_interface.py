# -*- coding: utf-8 -*-
"""
Web界面模块 - Flask后端API
提供音高曲线比对系统的Web服务
"""
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_cors import CORS
import os
import uuid
import time
from datetime import datetime
import json
import traceback

# 导入系统模块
from config import Config
from tts_module import TTSManager
from enhanced_tts_manager import EnhancedTTSManager
from pitch_comparison import PitchComparator
from scoring_algorithm import ScoringSystem, DetailedAnalyzer
from visualization import PitchVisualization
from character_voice_manager import CharacterVoiceManager
from dialogue_emotion_analyzer import DialogueEmotionAnalyzer

# 导入数值处理
import numpy as np
import io
import wave
import threading
import queue

# 导入场景对话模块
from deepseek_integration import get_deepseek_generator

# 导入文字比对模块
from text_comparator import TextComparator

# 导入频谱分析模块
from spectrogram_analyzer import get_analyzer

def detect_dialogue_emotion(text: str) -> str:
    """
    改进的对话情感检测
    
    Args:
        text: 对话文本
    
    Returns:
        str: 检测到的情感类型
    """
    text_lower = text.lower()
    
    # 情感权重系统，避免单一关键词误判
    emotion_scores = {
        'happy': 0,
        'angry': 0,
        'sad': 0,
        'gentle': 0,
        'serious': 0,
        'neutral': 0
    }
    
    # 开心/兴奋的关键词（权重不同）
    happy_keywords = {
        '哈哈': 3, '太好了': 3, '真棒': 2, '很棒': 2, '开心': 3, '高兴': 3, 
        '兴奋': 3, '不错': 1, '很好': 1, '太棒了': 3, '棒': 1
    }
    for keyword, weight in happy_keywords.items():
        if keyword in text_lower:
            emotion_scores['happy'] += weight
    
    # 感叹号增加开心权重
    if '!' in text or '！' in text:
        emotion_scores['happy'] += 1
    
    # 生气/愤怒的关键词
    angry_keywords = {
        '生气': 3, '愤怒': 3, '气死了': 3, '讨厌': 2, '烦人': 2, 
        '可恶': 3, '混蛋': 3, '该死': 3, '恼火': 2
    }
    for keyword, weight in angry_keywords.items():
        if keyword in text_lower:
            emotion_scores['angry'] += weight
    
    # 悲伤的关键词
    sad_keywords = {
        '难过': 3, '伤心': 3, '哭': 3, '痛苦': 3, '失望': 2, 
        '沮丧': 2, '郁闷': 2, '悲伤': 3, '心痛': 3
    }
    for keyword, weight in sad_keywords.items():
        if keyword in text_lower:
            emotion_scores['sad'] += weight
    
    # 温柔的关键词
    gentle_keywords = {
        '谢谢': 2, '请': 1, '麻烦': 1, '不好意思': 2, '对不起': 2, 
        '抱歉': 2, '温柔': 3, '轻声': 2, '劳烦': 1, '辛苦': 1
    }
    for keyword, weight in gentle_keywords.items():
        if keyword in text_lower:
            emotion_scores['gentle'] += weight
    
    # 严肃的关键词
    serious_keywords = {
        '重要': 2, '注意': 2, '必须': 2, '严肃': 3, '认真': 2, 
        '警告': 3, '小心': 2, '紧急': 3, '关键': 2, '务必': 2
    }
    for keyword, weight in serious_keywords.items():
        if keyword in text_lower:
            emotion_scores['serious'] += weight
    
    # 疑问增加中性权重
    if '?' in text or '？' in text:
        emotion_scores['neutral'] += 2
    
    # 疑问词
    question_words = ['什么', '为什么', '怎么', '哪里', '谁', '哪个', '多少']
    for word in question_words:
        if word in text_lower:
            emotion_scores['neutral'] += 1
    
    # 特殊情况处理
    # "我很生气" 这种直接表达情感的句子
    if any(phrase in text_lower for phrase in ['我生气', '我愤怒', '我很生气']):
        emotion_scores['angry'] += 3
    
    if any(phrase in text_lower for phrase in ['我难过', '我伤心', '我很难过']):
        emotion_scores['sad'] += 3
    
    # 找到得分最高的情感
    max_emotion = max(emotion_scores.items(), key=lambda x: x[1])
    
    # 如果最高分数为0或太低，返回neutral
    if max_emotion[1] == 0 or max_emotion[1] < 2:
        return 'neutral'
    
    return max_emotion[0]

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 启用跨域支持
CORS(app)

# 添加缓存控制
@app.after_request
def after_request(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# 初始化WebSocket实时同步
try:
    from realtime_sync import init_socketio
    socketio = init_socketio(app)
    WEBSOCKET_AVAILABLE = True
    print("✓ WebSocket实时同步已启用")
except ImportError as e:
    print(f"✗ WebSocket模块导入失败: {e}")
    socketio = None
    WEBSOCKET_AVAILABLE = False
except Exception as e:
    print(f"✗ WebSocket初始化失败: {e}")
    socketio = None
    WEBSOCKET_AVAILABLE = False

def safe_json_serialize(obj):
    """安全的JSON序列化，处理NaN和inf值"""
    if isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return safe_json_serialize(obj.tolist())
    else:
        return obj

# 初始化系统组件
tts_manager = None
enhanced_tts_manager = None
comparator = None
scoring_system = None
analyzer = None
visualizer = None
voice_manager = None
emotion_analyzer = None
text_comparator = None

# 场景对话会话存储
dialogue_sessions = {}

# 听觉反馈会话存储
feedback_sessions = {}

# 录音会话管理
recording_sessions = {}
recording_lock = threading.Lock()

class RecordingSession:
    """录音会话类"""
    def __init__(self, session_id):
        self.session_id = session_id
        self.is_recording = False
        self.audio_data = queue.Queue()
        self.start_time = None
        self.audio_format = {
            'channels': 1,
            'sample_width': 2,
            'frame_rate': 44100
        }
        
    def start_recording(self):
        """开始录音"""
        self.is_recording = True
        self.start_time = time.time()
        # 清空之前的音频数据
        while not self.audio_data.empty():
            try:
                self.audio_data.get_nowait()
            except queue.Empty:
                break
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False
        
    def add_audio_chunk(self, chunk_data):
        """添加音频数据块"""
        if self.is_recording:
            self.audio_data.put(chunk_data)
    
    def get_audio_data(self):
        """获取完整的音频数据"""
        chunks = []
        while not self.audio_data.empty():
            try:
                chunks.append(self.audio_data.get_nowait())
            except queue.Empty:
                break
        return b''.join(chunks) if chunks else b''

def init_system():
    """初始化系统组件"""
    global tts_manager, enhanced_tts_manager, comparator, scoring_system, analyzer, visualizer, voice_manager, emotion_analyzer, text_comparator
    
    try:
        print("正在初始化系统组件...")
        
        # 创建必要目录
        Config.create_directories()
        
        # 初始化各个模块
        tts_manager = TTSManager()  # 保留原有TTS管理器用于兼容
        
        # 初始化增强型TTS管理器
        try:
            enhanced_tts_manager = EnhancedTTSManager()
            print("✓ 增强型TTS管理器初始化成功")
        except Exception as e:
            print(f"⚠ 增强型TTS管理器初始化失败，使用标准TTS管理器: {e}")
            enhanced_tts_manager = None
        
        # 初始化其他组件
        comparator = PitchComparator()
        scoring_system = ScoringSystem()
        analyzer = DetailedAnalyzer()
        visualizer = PitchVisualization()
        
        # 初始化场景对话相关组件
        try:
            voice_manager = CharacterVoiceManager()
            emotion_analyzer = DialogueEmotionAnalyzer()
            print("✓ 场景对话组件初始化成功")
        except Exception as e:
            print(f"⚠ 场景对话组件初始化失败: {e}")
            voice_manager = None
            emotion_analyzer = None
        
        # 初始化文字比对器
        try:
            text_comparator = TextComparator()
            print("✓ 文字比对器初始化成功")
        except Exception as e:
            print(f"⚠ 文字比对器初始化失败: {e}")
            text_comparator = None
        
        print("✓ 系统初始化完成")
        return True
        
    except Exception as e:
        print(f"✗ 系统初始化失败: {e}")
        traceback.print_exc()
        return False

def generate_tts_audio(text: str, output_path: str) -> bool:
    """
    生成TTS音频的辅助函数
    
    Args:
        text: 要转换的文本
        output_path: 输出音频文件路径
        
    Returns:
        bool: 是否成功生成音频
    """
    try:
        if not tts_manager:
            print("⚠ TTS管理器未初始化")
            return False
        
        # 使用标准发音生成音频
        success = tts_manager.generate_standard_audio(
            text=text,
            output_path=output_path,
            voice_gender='female',
            voice_emotion='neutral'
        )
        
        return success
        
    except Exception as e:
        print(f"✗ TTS音频生成失败: {e}")
        traceback.print_exc()
        return False

# 路由定义

@app.route('/')
def index():
    """重定向到首页"""
    return render_template('home.html')

@app.route('/home')
def home():
    """首页 - 选择练习模式"""
    return render_template('home.html')

@app.route('/standard-audio')
def standard_audio():
    """标准发音播放页面"""
    return render_template('standard_audio.html')

@app.route('/recording')
def recording():
    """录音界面页面"""
    return render_template('recording.html')

@app.route('/results')
def results():
    """结果分析页面"""
    return render_template('results.html')

@app.route('/legacy')
def legacy():
    """原有的单页面应用（保留作为备用）"""
    return render_template('index.html')

@app.route('/hearing-feedback')
def hearing_feedback():
    """听觉反馈训练页面"""
    return render_template('hearing_feedback.html')

@app.route('/api/tts/engines', methods=['GET'])
def get_tts_engines():
    """获取可用的TTS引擎列表"""
    try:
        # 优先使用增强型TTS管理器
        if enhanced_tts_manager:
            engines = enhanced_tts_manager.get_available_engines()
            current_engine = enhanced_tts_manager.current_engine
            features = {}
            for engine in engines:
                features[engine] = enhanced_tts_manager.get_engine_features(engine)
        else:
            engines = tts_manager.get_available_engines() if tts_manager else []
            current_engine = 'baidu'  # 默认引擎
            features = {}
        
        return jsonify({
            'success': True,
            'engines': engines,
            'current_engine': current_engine,
            'features': features
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tts/generate', methods=['POST'])
def generate_standard_audio():
    """生成标准发音音频"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        voice_gender = data.get('voice_gender', 'female')  # 默认女声
        voice_emotion = data.get('voice_emotion', 'neutral')  # 默认中性情感
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要合成的文本'
            }), 400
        
        print(f"TTS请求参数: text='{text}', gender={voice_gender}, emotion={voice_emotion}")
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"standard_{file_id}.wav"
        output_path = os.path.join(Config.TEMP_FOLDER, filename)
        
        # 调用TTS生成音频，传递性别和情感参数
        success = tts_manager.generate_standard_audio(text, output_path, voice_gender, voice_emotion)
        
        if success:
            # 提取音高信息
            pitch_data = comparator.extractor.extract_pitch(output_path)
            
            # 安全计算音高统计
            pitch_values = pitch_data.get('pitch_values', [0])
            if len(pitch_values) > 0 and not all(np.isnan(pitch_values)):
                mean_pitch = float(np.nanmean(pitch_values))
            else:
                mean_pitch = 0.0
            
            pitch_info = {
                'duration': pitch_data.get('duration', 0),
                'valid_ratio': pitch_data.get('valid_ratio', 0),
                'mean_pitch': mean_pitch
            }
            
            return jsonify({
                'success': True,
                'audio_url': url_for('serve_temp_file', filename=filename),
                'file_id': file_id,
                'pitch_info': safe_json_serialize(pitch_info)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'TTS生成失败，请检查网络连接或TTS配置'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """开始录音会话"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        with recording_lock:
            # 如果已存在会话，先清理
            if session_id in recording_sessions:
                recording_sessions[session_id].stop_recording()
            
            # 创建新的录音会话
            recording_sessions[session_id] = RecordingSession(session_id)
            recording_sessions[session_id].start_recording()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': '录音会话已开始'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'启动录音失败: {str(e)}'
        }), 500

@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """停止录音会话并保存音频"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': '缺少session_id参数'
            }), 400
        
        with recording_lock:
            if session_id not in recording_sessions:
                return jsonify({
                    'success': False,
                    'error': '录音会话不存在'
                }), 404
            
            session = recording_sessions[session_id]
            session.stop_recording()
            
            # 获取录音数据
            audio_data = session.get_audio_data()
            
            if not audio_data:
                return jsonify({
                    'success': False,
                    'error': '没有录音数据'
                }), 400
            
        # 保存音频文件
        file_id = str(uuid.uuid4())
        wav_filename = f"user_{file_id}.wav"  # 使用与upload_audio一致的命名格式
        wav_filepath = os.path.join(Config.UPLOAD_FOLDER, wav_filename)
        
        # 🎯 保存 PCM 文件用于百度语音识别（推荐格式）
        pcm_filename = f"user_{file_id}.pcm"
        pcm_filepath = os.path.join(Config.UPLOAD_FOLDER, pcm_filename)
        with open(pcm_filepath, 'wb') as pcm_file:
            pcm_file.write(audio_data)
        
        # 将音频数据保存为WAV文件（用于播放和音高分析）
        with wave.open(wav_filepath, 'wb') as wav_file:
            wav_file.setnchannels(session.audio_format['channels'])
            wav_file.setsampwidth(session.audio_format['sample_width'])
            wav_file.setframerate(session.audio_format['frame_rate'])
            wav_file.writeframes(audio_data)
            
            # 清理录音会话
            del recording_sessions[session_id]
        
        # 获取音频信息
        duration = len(audio_data) / (session.audio_format['frame_rate'] * 
                                     session.audio_format['sample_width'] * 
                                     session.audio_format['channels'])
        
        # 生成可访问的音频URL
        audio_url = f"/uploads/{wav_filename}"
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': wav_filename,
            'audioUrl': audio_url,  # 添加音频URL供前端播放
            'duration': duration,
            'message': '录音已保存'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'停止录音失败: {str(e)}'
        }), 500

@app.route('/api/recording/data', methods=['POST'])
def upload_recording_data():
    """接收录音数据块"""
    try:
        session_id = request.form.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': '缺少session_id参数'
            }), 400
        
        if 'audio_chunk' not in request.files:
            return jsonify({
                'success': False,
                'error': '缺少音频数据'
            }), 400
        
        audio_chunk = request.files['audio_chunk']
        chunk_data = audio_chunk.read()
        
        with recording_lock:
            if session_id in recording_sessions:
                recording_sessions[session_id].add_audio_chunk(chunk_data)
                return jsonify({
                    'success': True,
                    'message': '音频数据已接收'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '录音会话不存在'
                }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'上传录音数据失败: {str(e)}'
        }), 500

@app.route('/api/recording/status/<session_id>', methods=['GET'])
def get_recording_status(session_id):
    """获取录音会话状态"""
    try:
        with recording_lock:
            if session_id in recording_sessions:
                session = recording_sessions[session_id]
                return jsonify({
                    'success': True,
                    'is_recording': session.is_recording,
                    'duration': time.time() - session.start_time if session.start_time else 0
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '录音会话不存在'
                }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取录音状态失败: {str(e)}'
        }), 500

@app.route('/api/audio/upload', methods=['POST'])
def upload_user_audio():
    """上传用户录音"""
    try:
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': '请上传音频文件'
            }), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"user_{file_id}_temp{file_extension}"
        temp_filepath = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
        
        # 先保存临时文件
        file.save(temp_filepath)
        
        # 目标WAV文件路径
        wav_filename = f"user_{file_id}.wav"
        wav_filepath = os.path.join(Config.UPLOAD_FOLDER, wav_filename)
        
        # 获取实际MIME类型
        mime_type = request.form.get('mime_type', 'audio/wav')
        
        # 🔧 通过文件头检测实际格式，解决WebM伪装成WAV的问题
        actual_format = None
        try:
            with open(temp_filepath, 'rb') as f:
                header = f.read(16)
                if header[:4] == b'\x1a\x45\xdf\xa3':  # WebM/Matroska文件头
                    actual_format = 'webm'
                    print("⚠️ 检测到WebM格式文件，但扩展名为.wav")
                elif header[:4] == b'RIFF' and header[8:12] == b'WAVE':  # WAV文件头
                    actual_format = 'wav'
                elif header[:4] == b'ftyp':  # MP4文件头
                    actual_format = 'mp4'
                elif header[:2] == b'\xff\xfb' or header[:2] == b'\xff\xf3':  # MP3文件头
                    actual_format = 'mp3'
        except Exception as e:
            print(f"文件头检测失败: {e}")
        
        print(f"收到音频文件: {temp_filename}, 声明MIME: {mime_type}, 实际格式: {actual_format}, 大小: {os.path.getsize(temp_filepath)} bytes")
        
        # 使用ffmpeg转换为WAV格式，优化手机录音处理
        try:
            import subprocess
            
            # 检查ffmpeg是否可用
            try:
                ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
                ffmpeg_available = ffmpeg_check.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                ffmpeg_available = False
            
            if not ffmpeg_available:
                print("警告: ffmpeg未安装或不可用，尝试直接处理音频文件")
                import shutil
                shutil.move(temp_filepath, wav_filepath)
            else:
                # 🔧 根据实际检测的格式优化转换参数
                if actual_format == 'webm' or 'webm' in mime_type.lower():
                    print("🔧 使用WebM格式转换参数")
                    ffmpeg_cmd = [
                        'ffmpeg', '-f', 'webm', '-i', temp_filepath, 
                        '-acodec', 'pcm_s16le',     # 16位PCM编码
                        '-ar', '16000',             # 16kHz采样率，适合语音识别
                        '-ac', '1',                 # 单声道
                        '-af', 'highpass=f=80,lowpass=f=8000,volume=1.5',  # 音频滤波和适度增益
                        '-y',                       # 覆盖输出文件
                        wav_filepath
                    ]
                elif actual_format == 'mp4':
                    print("🔧 使用MP4格式转换参数")
                    ffmpeg_cmd = [
                        'ffmpeg', '-f', 'mp4', '-i', temp_filepath, 
                        '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                        '-af', 'highpass=f=80,lowpass=f=8000,volume=1.5',
                        '-y', wav_filepath
                    ]
                elif actual_format == 'mp3':
                    print("🔧 使用MP3格式转换参数")
                    ffmpeg_cmd = [
                        'ffmpeg', '-f', 'mp3', '-i', temp_filepath, 
                        '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                        '-af', 'highpass=f=80,lowpass=f=8000,volume=1.5',
                        '-y', wav_filepath
                    ]
                elif actual_format == 'wav':
                    print("🔧 使用WAV格式转换参数")
                    ffmpeg_cmd = [
                        'ffmpeg', '-i', temp_filepath, 
                        '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                        '-af', 'highpass=f=80,lowpass=f=8000,volume=1.5',
                        '-y', wav_filepath
                    ]
                else:
                    print("🔧 使用通用格式转换参数")
                    ffmpeg_cmd = [
                        'ffmpeg', '-i', temp_filepath, 
                        '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                        '-af', 'highpass=f=80,lowpass=f=8000,volume=1.5',
                        '-y', wav_filepath
                    ]
                
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    print(f"ffmpeg转换失败: {result.stderr}")
                    print(f"尝试的命令: {' '.join(ffmpeg_cmd)}")
                    
                    # 🔧 对于WebM格式，尝试更宽松的转换参数
                    if actual_format == 'webm':
                        print("🔧 尝试WebM宽松转换参数...")
                        fallback_cmd = [
                            'ffmpeg', '-i', temp_filepath, 
                            '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                            '-vn',  # 忽略视频流
                            '-y', wav_filepath
                        ]
                        fallback_result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=30)
                        
                        if fallback_result.returncode == 0:
                            print("✓ WebM宽松转换成功")
                            if os.path.exists(temp_filepath):
                                os.remove(temp_filepath)
                        else:
                            print(f"WebM宽松转换也失败: {fallback_result.stderr}")
                            # 返回错误而不是使用原始WebM文件
                            if os.path.exists(temp_filepath):
                                os.remove(temp_filepath)
                            return jsonify({
                                'success': False,
                                'error': f'音频格式转换失败，无法处理该音频文件。检测到格式: {actual_format}'
                            }), 400
                    else:
                        # 对于其他格式，如果转换失败则返回错误
                        if os.path.exists(temp_filepath):
                            os.remove(temp_filepath)
                        return jsonify({
                            'success': False,
                            'error': f'音频格式转换失败: {result.stderr}'
                        }), 400
                else:
                    print(f"音频格式转换成功: {temp_filename} -> {wav_filename}")
                    print(f"转换后文件大小: {os.path.getsize(wav_filepath)} bytes")
                    # 删除临时文件
                    if os.path.exists(temp_filepath):
                        os.remove(temp_filepath)
                    
        except Exception as e:
            print(f"音频转换过程出错: {e}")
            # 🔧 对于WebM等需要转换的格式，转换异常时返回错误
            if actual_format in ['webm', 'mp4', 'mp3']:
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                return jsonify({
                    'success': False,
                    'error': f'音频转换异常: {str(e)}。检测到格式: {actual_format}'
                }), 400
            else:
                # 对于WAV或其他格式，尝试使用原文件
                import shutil
                if os.path.exists(temp_filepath):
                    shutil.move(temp_filepath, wav_filepath)
                    print("转换异常，使用原文件")
        
        # 使用转换后的WAV文件路径
        filepath = wav_filepath
        filename = wav_filename
        
        # 提取音高信息
        pitch_data = comparator.extractor.extract_pitch(filepath)
        
        # 安全计算平均音高
        pitch_values = pitch_data.get('pitch_values', [])
        valid_pitches = [p for p in pitch_values if p > 0]
        mean_pitch = np.mean(valid_pitches) if valid_pitches else 0.0
        
        # 🔧 添加录音质量诊断信息
        audio_diagnostics = {
            'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            'duration': pitch_data.get('duration', 0),
            'valid_ratio': pitch_data.get('valid_ratio', 0),
            'total_pitch_points': len(pitch_values),
            'valid_pitch_points': len(valid_pitches),
            'conversion_success': result.returncode == 0 if 'result' in locals() else True
        }
        
        print(f"📊 录音质量诊断: {audio_diagnostics}")
        
        # 生成可访问的音频URL
        audio_url = f"/uploads/{filename}"
        
        return safe_json_serialize({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'audioUrl': audio_url,  # 添加音频URL供前端播放
            'pitch_info': {
                'duration': pitch_data.get('duration', 0),
                'valid_ratio': pitch_data.get('valid_ratio', 0),
                'mean_pitch': mean_pitch
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'文件上传失败: {str(e)}'
        }), 500

@app.route('/api/compare', methods=['POST'])
def compare_audio():
    """比较音频并生成评分"""
    try:
        data = request.get_json()
        print(f"收到比较请求数据: {data}")
        
        if not data:
            print("错误: 请求体为空")
            return jsonify({
                'success': False,
                'error': '请求体为空'
            }), 400
            
        standard_file_id = data.get('standard_file_id')
        user_file_id = data.get('user_file_id')
        text = data.get('text', '')
        
        print(f"standard_file_id: {standard_file_id}, user_file_id: {user_file_id}")
        
        if not standard_file_id or not user_file_id:
            return jsonify({
                'success': False,
                'error': f'缺少音频文件ID (standard: {standard_file_id}, user: {user_file_id})'
            }), 400
        
        # 构建文件路径
        standard_path = os.path.join(Config.TEMP_FOLDER, f"standard_{standard_file_id}.wav")
        user_path = os.path.join(Config.UPLOAD_FOLDER, f"user_{user_file_id}.wav")
        
        if not os.path.exists(standard_path):
            return jsonify({
                'success': False,
                'error': '标准音频文件不存在'
            }), 404
        
        if not os.path.exists(user_path):
            return jsonify({
                'success': False,
                'error': '用户音频文件不存在'
            }), 404
        
        # 进行音高比较
        print(f"开始比较音频: {standard_path} vs {user_path}")
        comparison_result = comparator.compare_pitch_curves(standard_path, user_path)
        
        if 'error' in comparison_result:
            return jsonify({
                'success': False,
                'error': comparison_result['error']
            }), 400
        
        # 计算评分 (传入文本用于声调分析)
        score_result = scoring_system.calculate_score(comparison_result, text)
        
        # 详细分析
        detailed_analysis = analyzer.analyze_pitch_details(comparison_result)
        
        # 🎯 生成两个可视化图表
        timestamp = int(time.time())
        
        # 1. 音高曲线对比图
        pitch_chart_filename = f"pitch_comparison_{user_file_id}_{timestamp}.png"
        pitch_chart_path = os.path.join(Config.OUTPUT_FOLDER, pitch_chart_filename)
        
        # 强制使用桌面端完整布局尺寸，传递TTS音频路径
        standard_audio_path = comparison_result.get('processed_audio_paths', {}).get('standard')
        pitch_chart_success = visualizer.plot_pitch_comparison(
            comparison_result, score_result, pitch_chart_path, 
            fig_size=(18, 12), dpi=150, input_text=text,
            standard_audio_path=standard_audio_path  # 🎯 传递TTS音频路径
        )
        
        # 2. 波形与音高分析图
        waveform_chart_filename = f"waveform_analysis_{user_file_id}_{timestamp}.png"
        waveform_chart_path = os.path.join(Config.OUTPUT_FOLDER, waveform_chart_filename)
        waveform_chart_success = False
        
        try:
            from audio_plot import plot_waveform_and_pitch
            plot_waveform_and_pitch(user_path, waveform_chart_path, fig_size=(16, 8), dpi=150)
            waveform_chart_success = True
            print(f"✓ 波形分析图生成成功: {waveform_chart_path}")
        except Exception as e:
            print(f"⚠️ 波形分析图生成失败: {e}")
        
        # 准备返回数据，使用安全序列化
        result = {
            'success': True,
            'score': safe_json_serialize(score_result),
            'analysis': safe_json_serialize(detailed_analysis),
            'text': text,
            'timestamp': datetime.now().isoformat(),
            'chart_url': url_for('serve_output_file', filename=pitch_chart_filename) if pitch_chart_success else None,
            'waveform_chart_url': url_for('serve_output_file', filename=waveform_chart_filename) if waveform_chart_success else None
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"比较失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'比较失败: {str(e)}'
        }), 500

@app.route('/api/pitch/extract', methods=['POST'])
def extract_pitch():
    """提取单个音频的音高信息"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        file_type = data.get('type', 'user')  # 'user' or 'standard'
        text = data.get('text', '')  # 添加文本参数
        
        if not file_id:
            return jsonify({
                'success': False,
                'error': '缺少文件ID'
            }), 400
        
        # 构建文件路径
        if file_type == 'standard':
            file_path = os.path.join(Config.TEMP_FOLDER, f"standard_{file_id}.wav")
        else:
            user_files = [f for f in os.listdir(Config.UPLOAD_FOLDER) if f.startswith(f"user_{file_id}")]
            if not user_files:
                return jsonify({
                    'success': False,
                    'error': '文件不存在'
                }), 404
            file_path = os.path.join(Config.UPLOAD_FOLDER, user_files[0])
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 提取音高
        pitch_data = comparator.extractor.extract_pitch(file_path)
        
        # 生成单独的音高图
        chart_filename = f"pitch_{file_type}_{file_id}_{int(time.time())}.png"
        chart_path = os.path.join(Config.OUTPUT_FOLDER, chart_filename)
        
        title = "标准发音音高曲线" if file_type == 'standard' else "用户发音音高曲线"
        
        # 🔍 调试输出
        print(f"🔍 DEBUG: file_type={file_type}, text='{text}', len(text)={len(text)}")
        print(f"🔍 DEBUG: text.strip()='{text.strip()}', len(text.strip())={len(text.strip())}")
        print(f"🚨 WEB: About to call visualizer.plot_individual_pitch")
        print(f"🚨 WEB: visualizer type = {type(visualizer)}")
        
        chart_success = visualizer.plot_individual_pitch(pitch_data, chart_path, title, text)
        
        print(f"🚨 WEB: plot_individual_pitch returned {chart_success}")
        
        # 安全计算音高统计
        pitch_values = pitch_data.get('pitch_values', [0])
        if len(pitch_values) > 0 and not all(np.isnan(pitch_values)):
            mean_pitch = float(np.nanmean(pitch_values))
            pitch_range = float(np.nanmax(pitch_values) - np.nanmin(pitch_values))
        else:
            mean_pitch = 0.0
            pitch_range = 0.0
        
        pitch_data_safe = {
            'duration': pitch_data.get('duration', 0),
            'valid_ratio': pitch_data.get('valid_ratio', 0),
            'mean_pitch': mean_pitch,
            'pitch_range': pitch_range
        }
        
        return jsonify({
            'success': True,
            'pitch_data': safe_json_serialize(pitch_data_safe),
            'chart_url': url_for('serve_output_file', filename=chart_filename) if chart_success else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'音高提取失败: {str(e)}'
        }), 500

@app.route('/temp/<filename>')
def serve_temp_file(filename):
    """提供临时文件访问"""
    try:
        response = send_file(os.path.join(Config.TEMP_FOLDER, filename))
        # 添加缓存控制头，防止浏览器缓存图片
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception:
        return "File not found", 404

@app.route('/uploads/<filename>')
def serve_upload_file(filename):
    """提供上传文件访问"""
    try:
        response = send_file(os.path.join(Config.UPLOAD_FOLDER, filename))
        # 添加缓存控制头，防止浏览器缓存音频
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception:
        return "File not found", 404

@app.route('/output/<filename>')
def serve_output_file(filename):
    """提供输出文件访问"""
    try:
        response = send_file(os.path.join(Config.OUTPUT_FOLDER, filename))
        # 添加缓存控制头，防止浏览器缓存图片
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception:
        return "File not found", 404


@app.route('/api/tts/generate_with_timestamps', methods=['POST'])
def generate_standard_audio_with_timestamps():
    """生成标准发音音频并获取字级时间戳"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        method = data.get('method', 'auto')  # auto, vad_estimation, uniform
        voice_gender = data.get('voice_gender', 'female')  # 默认女声
        voice_emotion = data.get('voice_emotion', 'neutral')  # 默认中性情感
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要合成的文本'
            }), 400
        
        print(f"TTS时间戳请求参数: text='{text}', method={method}, gender={voice_gender}, emotion={voice_emotion}")
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        filename = f"standard_{file_id}.wav"
        output_path = os.path.join(Config.TEMP_FOLDER, filename)
        
        # 1. 先生成TTS音频，传递性别和情感参数
        success = tts_manager.generate_standard_audio(text, output_path, voice_gender, voice_emotion)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'TTS生成失败'
            }), 500
        
        # 2. 生成时间戳
        try:
            from timestamp_generator import UniversalTimestampGenerator
            
            timestamp_generator = UniversalTimestampGenerator()
            timestamp_result = timestamp_generator.generate_timestamps(text, output_path, method)
            
            # 如果没有生成时间戳，强制使用uniform方法
            if (timestamp_result.get('success') and 
                not timestamp_result.get('char_timestamps')):
                print(f"方法 {method} 未生成时间戳，强制降级到uniform方法")
                timestamp_result = timestamp_generator.generate_timestamps(text, output_path, 'uniform')
            
            if timestamp_result['success'] and timestamp_result.get('char_timestamps'):
                # 提取音频基本信息
                pitch_data = comparator.extractor.extract_pitch(output_path)
                duration = pitch_data.get('duration', 0)
                
                return jsonify({
                    'success': True,
                    'audio_url': url_for('serve_temp_file', filename=filename),
                    'file_id': file_id,
                    'char_timestamps': safe_json_serialize(timestamp_result['char_timestamps']),
                    'timestamp_method': timestamp_result['method'],
                    'duration': duration,
                    'pitch_info': safe_json_serialize({
                        'duration': duration,
                        'valid_ratio': pitch_data.get('valid_ratio', 0),
                        'mean_pitch': float(np.nanmean(pitch_data.get('pitch_values', [0]))) if len(pitch_data.get('pitch_values', [])) > 0 else 0.0
                    })
                })
            else:
                # 即使时间戳生成失败，也返回音频文件
                pitch_data = comparator.extractor.extract_pitch(output_path)
                duration = pitch_data.get('duration', 0)
                
                return jsonify({
                    'success': True,
                    'audio_url': url_for('serve_temp_file', filename=filename),
                    'file_id': file_id,
                    'char_timestamps': [],
                    'timestamp_method': 'failed',
                    'duration': duration,
                    'warning': '时间戳生成失败，将使用均匀分布估算',
                    'pitch_info': safe_json_serialize({
                        'duration': duration,
                        'valid_ratio': pitch_data.get('valid_ratio', 0),
                        'mean_pitch': float(np.nanmean(pitch_data.get('pitch_values', [0]))) if len(pitch_data.get('pitch_values', [])) > 0 else 0.0
                    })
                })
                
        except Exception as e:
            print(f"时间戳生成异常: {e}")
            # 返回基本音频信息
            pitch_data = comparator.extractor.extract_pitch(output_path)
            duration = pitch_data.get('duration', 0)
            
            return jsonify({
                'success': True,
                'audio_url': url_for('serve_temp_file', filename=filename),
                'file_id': file_id,
                'char_timestamps': [],
                'timestamp_method': 'error',
                'duration': duration,
                'error': f'时间戳生成异常: {str(e)}',
                'pitch_info': safe_json_serialize({
                    'duration': duration,
                    'valid_ratio': pitch_data.get('valid_ratio', 0),
                    'mean_pitch': float(np.nanmean(pitch_data.get('pitch_values', [0]))) if len(pitch_data.get('pitch_values', [])) > 0 else 0.0
                })
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/sync/status', methods=['POST'])
def sync_status():
    """实时同步状态更新API"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        current_time = data.get('current_time', 0)
        action = data.get('action', 'update')  # update, start, stop
        char_index = data.get('char_index', -1)
        
        # 这里可以记录用户的同步状态，用于分析
        # 例如记录到数据库或Redis
        
        # 记录同步事件
        sync_event = {
            'file_id': file_id,
            'action': action,
            'current_time': current_time,
            'char_index': char_index,
            'timestamp': datetime.now().isoformat(),
            'user_ip': request.remote_addr
        }
        
        print(f"同步状态更新: {sync_event}")
        
        return jsonify({
            'success': True,
            'timestamp': current_time,
            'action': action,
            'char_index': char_index
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/timestamps/validate', methods=['POST'])
def validate_timestamps():
    """验证时间戳数据的有效性"""
    try:
        data = request.get_json()
        timestamps = data.get('timestamps', [])
        text = data.get('text', '')
        
        # 验证时间戳
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if len(timestamps) != len(text):
            validation_result['valid'] = False
            validation_result['errors'].append(f'时间戳数量({len(timestamps)})与文本长度({len(text)})不匹配')
        
        for i, ts in enumerate(timestamps):
            # 检查必要字段
            required_fields = ['char', 'start_time', 'end_time', 'index']
            missing_fields = [field for field in required_fields if field not in ts]
            if missing_fields:
                validation_result['valid'] = False
                validation_result['errors'].append(f'时间戳{i}缺少字段: {missing_fields}')
                continue
            
            # 检查时间逻辑
            if ts['start_time'] >= ts['end_time']:
                validation_result['valid'] = False
                validation_result['errors'].append(f'时间戳{i}时间逻辑错误: start_time >= end_time')
            
            # 检查字符匹配
            if i < len(text) and ts['char'] != text[i]:
                validation_result['warnings'].append(f'时间戳{i}字符不匹配: 期望"{text[i]}", 实际"{ts["char"]}"')
            
            # 检查时间顺序
            if i > 0 and ts['start_time'] < timestamps[i-1]['start_time']:
                validation_result['warnings'].append(f'时间戳{i}时间顺序可能有问题')
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/recording_guide', methods=['POST'])
def recording_guide_status():
    """录音指导状态API"""
    try:
        data = request.get_json()
        action = data.get('action', 'status')  # status, start, stop, progress
        
        if action == 'start':
            # 开始录音指导
            session_id = str(uuid.uuid4())
            text = data.get('text', '')
            char_timestamps = data.get('char_timestamps', [])
            
            # 这里可以创建录音指导会话
            guide_session = {
                'session_id': session_id,
                'text': text,
                'char_timestamps': char_timestamps,
                'start_time': datetime.now().isoformat(),
                'status': 'active'
            }
            
            print(f"录音指导会话开始: {session_id}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'action': 'started'
            })
            
        elif action == 'progress':
            # 更新录音指导进度
            session_id = data.get('session_id')
            progress = data.get('progress', [])
            current_char = data.get('current_char', -1)
            
            print(f"录音指导进度更新: {session_id}, 当前字符: {current_char}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'current_char': current_char
            })
            
        elif action == 'stop':
            # 停止录音指导
            session_id = data.get('session_id')
            final_progress = data.get('progress', [])
            stats = data.get('stats', {})
            
            print(f"录音指导会话结束: {session_id}")
            print(f"最终统计: {stats}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'action': 'stopped',
                'final_stats': stats
            })
        
        else:
            return jsonify({
                'success': True,
                'status': 'ready'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/system/status')
def system_status():
    """获取系统状态"""
    try:
        # 检查时间戳生成器可用性
        timestamp_available = False
        cache_available = False
        try:
            from timestamp_generator import UniversalTimestampGenerator
            generator = UniversalTimestampGenerator()
            generator.initialize()
            timestamp_available = True
            
            # 检查缓存系统
            if hasattr(generator, 'cache') and generator.cache:
                cache_available = True
            
        except Exception as e:
            print(f"时间戳生成器不可用: {e}")
        
        return jsonify({
            'success': True,
            'status': {
                'tts_available': tts_manager is not None,
                'tts_engines': tts_manager.get_available_engines() if tts_manager else [],
                'timestamp_generator_available': timestamp_available,
                'cache_available': cache_available,
                'websocket_available': WEBSOCKET_AVAILABLE,
                'realtime_sync_ready': timestamp_available and tts_manager is not None and WEBSOCKET_AVAILABLE,
                'system_ready': all([tts_manager, comparator, scoring_system, visualizer])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取系统状态失败: {str(e)}'
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """获取缓存统计信息"""
    try:
        from cache_manager import timestamp_cache, performance_optimizer
        
        # 获取缓存统计
        cache_stats = timestamp_cache.get_cache_stats()
        
        # 获取性能统计
        perf_stats = performance_optimizer.get_performance_stats()
        
        return jsonify({
            'success': True,
            'cache_stats': cache_stats,
            'performance_stats': perf_stats,
            'cache_enabled': True
        })
        
    except ImportError:
        return jsonify({
            'success': True,
            'cache_enabled': False,
            'message': '缓存系统未启用'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """清理缓存"""
    try:
        from cache_manager import timestamp_cache, performance_optimizer
        
        data = request.get_json() or {}
        cache_type = data.get('type', 'all')  # all, memory, file, performance
        
        results = {}
        
        if cache_type in ['all', 'memory']:
            # 清理内存缓存
            timestamp_cache.memory_cache.clear()
            results['memory_cleared'] = True
        
        if cache_type in ['all', 'file']:
            # 清理过期文件缓存
            cleanup_result = timestamp_cache.clear_expired()
            results['file_cleanup'] = cleanup_result
        
        if cache_type in ['all', 'performance']:
            # 清理性能统计
            performance_optimizer.clear_stats()
            results['performance_cleared'] = True
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': '缓存系统未启用'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# === 增强TTS API端点 ===

@app.route('/api/tts/switch_engine', methods=['POST'])
def switch_tts_engine():
    """切换TTS引擎"""
    try:
        data = request.get_json()
        engine_name = data.get('engine')
        
        if not engine_name:
            return jsonify({
                'success': False,
                'error': '请指定引擎名称'
            }), 400
        
        if enhanced_tts_manager:
            success = enhanced_tts_manager.switch_engine(engine_name)
            if success:
                return jsonify({
                    'success': True,
                    'current_engine': enhanced_tts_manager.current_engine
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'引擎切换失败: {engine_name}'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': '增强型TTS管理器未初始化'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tts/dialogue/generate', methods=['POST'])
def generate_dialogue_audio():
    """生成场景对话音频"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        character = data.get('character')
        emotion = data.get('emotion')
        auto_emotion = data.get('auto_emotion', True)
        engine = data.get('engine')
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要合成的文本'
            }), 400
        
        if enhanced_tts_manager:
            # 使用增强型TTS管理器生成对话音频
            audio_path, synthesis_info = enhanced_tts_manager.synthesize_dialogue(
                text=text,
                character=character,
                emotion=emotion,
                auto_emotion=auto_emotion,
                engine=engine
            )
            
            if audio_path and synthesis_info['success']:
                # 生成文件ID和URL
                import uuid
                file_id = str(uuid.uuid4())
                filename = os.path.basename(audio_path)
                
                return jsonify({
                    'success': True,
                    'audio_url': url_for('serve_cache_file', filename=filename),
                    'file_id': file_id,
                    'synthesis_info': safe_json_serialize(synthesis_info)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '对话音频生成失败',
                    'synthesis_info': safe_json_serialize(synthesis_info)
                }), 500
        else:
            # 回退到标准TTS
            file_id = str(uuid.uuid4())
            filename = f"dialogue_{file_id}.wav"
            output_path = os.path.join(Config.TEMP_FOLDER, filename)
            
            success = tts_manager.generate_standard_audio(text, output_path)
            
            if success:
                return jsonify({
                    'success': True,
                    'audio_url': url_for('serve_temp_file', filename=filename),
                    'file_id': file_id,
                    'synthesis_info': {
                        'character': character,
                        'emotion': emotion,
                        'engine_used': 'baidu',
                        'success': True
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'TTS生成失败'
                }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/tts/voice_clone', methods=['POST'])
def clone_voice():
    """语音克隆"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        reference_audio = data.get('reference_audio')
        engine = data.get('engine')
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要合成的文本'
            }), 400
        
        if not reference_audio:
            return jsonify({
                'success': False,
                'error': '请提供参考音频文件'
            }), 400
        
        if enhanced_tts_manager:
            # 生成输出路径
            import uuid
            file_id = str(uuid.uuid4())
            filename = f"cloned_{file_id}.wav"
            output_path = os.path.join('cache/tts', filename)
            
            success = enhanced_tts_manager.clone_voice(
                text=text,
                reference_audio=reference_audio,
                output_path=output_path,
                engine=engine
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'audio_url': url_for('serve_cache_file', filename=filename),
                    'file_id': file_id
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '语音克隆失败'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': '语音克隆功能需要增强型TTS管理器'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/characters', methods=['GET'])
def get_characters():
    """获取所有角色"""
    try:
        if voice_manager:
            characters = []
            for name in voice_manager.get_all_characters():
                profile = voice_manager.get_character_voice_config(name)
                characters.append({
                    'name': name,
                    'type': profile.type,
                    'description': profile.description,
                    'default_emotion': profile.default_emotion,
                    'available_emotions': voice_manager.get_character_emotions(name)
                })
            
            return jsonify({
                'success': True,
                'characters': characters
            })
        else:
            return jsonify({
                'success': True,
                'characters': []
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/emotions/analyze', methods=['POST'])
def analyze_text_emotion():
    """分析文本情感"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        context = data.get('context', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': '请输入要分析的文本'
            }), 400
        
        if emotion_analyzer:
            emotion, confidence = emotion_analyzer.analyze_emotion(text, context)
            description = emotion_analyzer.get_emotion_description(emotion)
            
            return jsonify({
                'success': True,
                'emotion': emotion,
                'confidence': confidence,
                'description': description,
                'available_emotions': emotion_analyzer.get_available_emotions()
            })
        else:
            return jsonify({
                'success': False,
                'error': '情感分析器未初始化'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tts/stats', methods=['GET'])
def get_tts_stats():
    """获取TTS统计信息"""
    try:
        if enhanced_tts_manager:
            stats = enhanced_tts_manager.get_stats()
            return jsonify({
                'success': True,
                'stats': safe_json_serialize(stats)
            })
        else:
            return jsonify({
                'success': True,
                'stats': {
                    'message': '增强型TTS管理器未启用',
                    'available_engines': tts_manager.get_available_engines() if tts_manager else []
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/cache/tts/<filename>')
def serve_cache_file(filename):
    """提供TTS缓存文件访问"""
    try:
        return send_file(os.path.join('cache/tts', filename))
    except Exception:
        return "File not found", 404

# === 场景对话API端点 ===

@app.route('/api/scenario/generate', methods=['POST'])
def generate_scenario_dialogue():
    """生成场景对话"""
    try:
        data = request.get_json()
        scenario = data.get('scenario', '').strip()
        
        if not scenario:
            return jsonify({
                'success': False,
                'error': '请输入场景描述'
            }), 400
        
        if len(scenario) > Config.MAX_SCENARIO_LENGTH:
            return jsonify({
                'success': False,
                'error': f'场景描述不能超过{Config.MAX_SCENARIO_LENGTH}个字符'
            }), 400
        
        # 调用DeepSeek生成对话
        generator = get_deepseek_generator()
        result = generator.generate_scenario_dialogue(scenario, Config.DEFAULT_DIALOGUE_ROUNDS)
        
        if result.get('success'):
            # 保存对话会话
            session_id = str(uuid.uuid4())
            dialogue_sessions[session_id] = {
                'dialogue_data': result['data'],
                'scenario_description': scenario,
                'created_at': time.time(),
                'last_accessed': time.time()
            }
            
            print(f"✓ 场景对话生成成功，会话ID: {session_id}")
            print(f"场景: {result['data'].get('scenario_title', 'N/A')}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'dialogue_data': result['data']
            })
        else:
            print(f"✗ 对话生成失败: {result.get('error', '未知错误')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '对话生成失败')
            }), 500
            
    except Exception as e:
        print(f"✗ 场景对话生成异常: {e}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/scenario/next', methods=['POST'])
def get_next_dialogue():
    """获取下一句对话"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        current_order = data.get('current_order', 0)
        
        if not session_id or session_id not in dialogue_sessions:
            return jsonify({
                'success': False,
                'error': '对话会话不存在或已过期'
            }), 404
        
        # 更新访问时间
        dialogue_sessions[session_id]['last_accessed'] = time.time()
        
        session_data = dialogue_sessions[session_id]
        dialogue_data = session_data['dialogue_data']
        
        # 查找下一句对话
        next_dialogue = None
        for dialogue in dialogue_data['dialogues']:
            if dialogue['order'] == current_order + 1:
                next_dialogue = dialogue
                break
        
        if next_dialogue:
            # 调试：打印下一句对话的完整信息
            print(f"🔍 获取到下一句对话: {next_dialogue}")
            print(f"🔍 Speaker字段值: '{next_dialogue.get('speaker', 'MISSING')}'")
            print(f"🔍 Speaker字段类型: {type(next_dialogue.get('speaker', 'MISSING'))}")
            
            # 如果是AI角色台词，生成带角色语音的TTS音频
            if next_dialogue['speaker'] == 'ai':
                print(f"🎭 检测到AI角色台词: {next_dialogue['text']}")
                try:
                    # 导入必要的模块
                    from dialogue_voice_mapper import DialogueVoiceMapper
                    
                    # 初始化语音映射器
                    voice_mapper = DialogueVoiceMapper()
                    print(f"✓ 语音映射器初始化成功")
                    
                    # 分析角色并分配语音类型
                    scenario_description = dialogue_data.get('scenario', '')
                    role_data = {
                        'ai_role': dialogue_data.get('ai_role', ''),
                        'user_role': dialogue_data.get('user_role', '')
                    }
                    print(f"🎯 场景描述: {scenario_description}")
                    print(f"🎯 角色数据: {role_data}")
                    
                    # 获取角色语音映射
                    voice_mapping = voice_mapper.analyze_scenario_roles(scenario_description, role_data)
                    ai_role = dialogue_data.get('ai_role', '')
                    voice_type = voice_mapping.get(ai_role, 'adult_female')
                    print(f"🎵 语音映射结果: {voice_mapping}")
                    print(f"🎵 AI角色 '{ai_role}' 分配语音类型: {voice_type}")
                    
                    # 生成角色语音
                    import uuid
                    file_id = str(uuid.uuid4())
                    filename = f"ai_dialogue_{file_id}.wav"
                    output_path = os.path.join(Config.TEMP_FOLDER, filename)
                    print(f"📁 音频输出路径: {output_path}")
                    
                    # 使用增强的TTS管理器生成AI角色情感语音
                    if tts_manager:
                        print(f"🔊 开始生成AI角色情感语音...")
                        
                        # 分析台词情感（简单的情感识别）
                        dialogue_text = next_dialogue['text']
                        detected_emotion = detect_dialogue_emotion(dialogue_text)
                        
                        success = tts_manager.generate_ai_character_audio(
                            text=dialogue_text,
                            output_path=output_path,
                            character_type=voice_type,
                            emotion=detected_emotion,
                            scenario_context=scenario_description
                        )
                        print(f"🔊 AI角色情感语音生成结果: {success}")
                        
                        if success and os.path.exists(output_path):
                            # 添加音频信息到对话数据
                            next_dialogue['audio_url'] = url_for('serve_temp_file', filename=filename)
                            next_dialogue['voice_type'] = voice_type
                            next_dialogue['emotion'] = detected_emotion
                            next_dialogue['voice_description'] = f"{voice_mapper.get_voice_description(voice_type)} ({detected_emotion})"
                            print(f"✅ 为AI角色 '{ai_role}' 生成情感语音成功: {voice_type} ({detected_emotion})")
                            print(f"✅ 音频URL: {next_dialogue['audio_url']}")
                        else:
                            print(f"❌ AI角色语音生成失败: TTS生成返回{success}, 文件存在: {os.path.exists(output_path)}")
                    else:
                        print(f"❌ AI角色语音生成失败: tts_manager未初始化")
                        
                except Exception as e:
                    print(f"❌ 生成AI角色语音时出错: {e}")
                    import traceback
                    print(f"详细错误信息: {traceback.format_exc()}")
            
            # 检查是否是对话结束
            is_complete = current_order + 1 >= len(dialogue_data['dialogues'])
            
            return jsonify({
                'success': True,
                'dialogue': next_dialogue,
                'is_complete': is_complete,
                'total_dialogues': len(dialogue_data['dialogues'])
            })
        else:
            return jsonify({
                'success': True,
                'dialogue': None,
                'is_complete': True,
                'total_dialogues': len(dialogue_data['dialogues'])
            })
            
    except Exception as e:
        print(f"✗ 获取下一句对话失败: {e}")
        return jsonify({
            'success': False,
            'error': f'获取对话失败: {str(e)}'
        }), 500

@app.route('/api/scenario/session/<session_id>', methods=['GET'])
def get_dialogue_session(session_id):
    """获取对话会话信息"""
    try:
        if session_id not in dialogue_sessions:
            return jsonify({
                'success': False,
                'error': '对话会话不存在'
            }), 404
        
        session_data = dialogue_sessions[session_id]
        
        # 更新访问时间
        session_data['last_accessed'] = time.time()
        
        return jsonify({
            'success': True,
            'session_data': {
                'session_id': session_id,
                'dialogue_data': session_data['dialogue_data'],
                'scenario_description': session_data['scenario_description'],
                'created_at': session_data['created_at']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scenario/ai-tts', methods=['POST'])
def generate_ai_character_tts():
    """为AI角色台词生成情感TTS音频"""
    try:
        data = request.get_json()
        
        # 获取参数
        text = data.get('text', '').strip()
        character_type = data.get('character_type', 'default')
        emotion = data.get('emotion', 'neutral')
        scenario_context = data.get('scenario_context', '')
        ai_role = data.get('ai_role', '')
        
        # 参数验证
        if not text:
            return jsonify({
                'success': False,
                'error': '文本内容不能为空'
            }), 400
        
        print(f"🎭 收到AI角色TTS请求:")
        print(f"   文本: {text}")
        print(f"   角色类型: {character_type}")
        print(f"   情感: {emotion}")
        print(f"   场景: {scenario_context}")
        print(f"   AI角色: {ai_role}")
        
        # 生成唯一文件名
        import uuid
        file_id = str(uuid.uuid4())
        filename = f"ai_character_{file_id}.wav"
        output_path = os.path.join(Config.TEMP_FOLDER, filename)
        
        # 确保临时文件夹存在
        os.makedirs(Config.TEMP_FOLDER, exist_ok=True)
        
        # 使用增强的TTS管理器生成AI角色音频
        if tts_manager:
            print(f"🔊 开始生成AI角色情感语音...")
            
            success = tts_manager.generate_ai_character_audio(
                text=text,
                output_path=output_path,
                character_type=character_type,
                emotion=emotion,
                scenario_context=scenario_context
            )
            
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # 生成音频URL
                audio_url = url_for('serve_temp_file', filename=filename)
                
                # 获取语音描述信息
                voice_description = f"{character_type}({emotion})"
                if scenario_context:
                    voice_description += f" - {scenario_context[:30]}..."
                
                print(f"✅ AI角色TTS生成成功:")
                print(f"   文件路径: {output_path}")
                print(f"   音频URL: {audio_url}")
                print(f"   文件大小: {os.path.getsize(output_path)} bytes")
                
                return jsonify({
                    'success': True,
                    'audio_url': audio_url,
                    'file_id': file_id,
                    'voice_description': voice_description,
                    'character_type': character_type,
                    'emotion': emotion,
                    'file_size': os.path.getsize(output_path),
                    'duration_estimate': len(text) * 0.15  # 粗略估算时长（秒）
                })
            else:
                print(f"❌ AI角色TTS生成失败:")
                print(f"   成功标志: {success}")
                print(f"   文件存在: {os.path.exists(output_path)}")
                if os.path.exists(output_path):
                    print(f"   文件大小: {os.path.getsize(output_path)} bytes")
                
                return jsonify({
                    'success': False,
                    'error': 'AI角色语音生成失败，请检查TTS服务状态'
                }), 500
        else:
            print(f"❌ TTS管理器未初始化")
            return jsonify({
                'success': False,
                'error': 'TTS服务未初始化，请检查配置'
            }), 500
            
    except Exception as e:
        print(f"❌ 生成AI角色TTS时出错: {e}")
        import traceback
        print(f"详细错误信息: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/scenario/test', methods=['GET'])
def test_scenario_api():
    """测试场景对话API"""
    try:
        generator = get_deepseek_generator()
        test_result = generator.test_api_connection()
        
        return jsonify({
            'success': True,
            'api_test': test_result,
            'config': {
                'max_scenario_length': Config.MAX_SCENARIO_LENGTH,
                'default_dialogue_rounds': Config.DEFAULT_DIALOGUE_ROUNDS,
                'api_configured': bool(Config.DEEPSEEK_API_KEY)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# === 听觉反馈API端点 ===

@app.route('/api/feedback/start', methods=['POST'])
def start_feedback_session():
    """开始听觉反馈训练会话"""
    try:
        data = request.get_json()
        scenario = data.get('scenario', '').strip()
        
        if not scenario:
            return jsonify({
                'success': False,
                'error': '请输入场景描述'
            }), 400
        
        if len(scenario) > 200:
            return jsonify({
                'success': False,
                'error': '场景描述不能超过200个字符'
            }), 400
        
        print(f"🎧 开始听觉反馈训练会话: {scenario}")
        
        # 调用DeepSeek生成对话
        generator = get_deepseek_generator()
        result = generator.generate_scenario_dialogue(scenario, Config.DEFAULT_DIALOGUE_ROUNDS)
        
        if result.get('success'):
            dialogue_data = result['data']
            
            # 为每句对话生成TTS音频
            print(f"🔊 开始为 {len(dialogue_data['dialogues'])} 句对话生成音频...")
            for i, dialogue in enumerate(dialogue_data['dialogues']):
                text = dialogue['text']
                print(f"   [{i+1}] 生成音频: '{text}'")
                
                try:
                    # 调用TTS生成音频
                    audio_filename = f"feedback_{uuid.uuid4().hex[:8]}_{i}.mp3"
                    audio_path = os.path.join(Config.UPLOAD_FOLDER, audio_filename)
                    
                    # 使用系统TTS生成音频
                    tts_result = generate_tts_audio(text, audio_path)
                    
                    if tts_result:
                        dialogue['audio_url'] = f'/uploads/{audio_filename}'
                        print(f"   ✓ 音频生成成功: {audio_filename}")
                    else:
                        print(f"   ✗ 音频生成失败，使用文本模式")
                        dialogue['audio_url'] = None
                        
                except Exception as e:
                    print(f"   ✗ 音频生成异常: {e}")
                    dialogue['audio_url'] = None
            
            # 创建训练会话
            session_id = str(uuid.uuid4())
            feedback_sessions[session_id] = {
                'dialogue_data': dialogue_data,
                'scenario': scenario,
                'start_time': time.time(),
                'records': [],
                'current_index': 0
            }
            
            print(f"✓ 听觉反馈会话创建成功: {session_id}")
            print(f"场景: {dialogue_data.get('scenario_title', 'N/A')}")
            print(f"对话句数: {len(dialogue_data.get('dialogues', []))}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'dialogue_data': dialogue_data
            })
        else:
            print(f"✗ 对话生成失败: {result.get('error', '未知错误')}")
            return jsonify({
                'success': False,
                'error': result.get('error', '对话生成失败')
            }), 500
            
    except Exception as e:
        print(f"✗ 听觉反馈会话创建异常: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

@app.route('/api/feedback/compare', methods=['POST'])
def compare_feedback_text():
    """文字比对API"""
    try:
        data = request.get_json()
        original = data.get('original', '').strip()
        user_input = data.get('user_input', '').strip()
        session_id = data.get('session_id')
        sentence_index = data.get('sentence_index', 0)
        
        if not original:
            return jsonify({
                'success': False,
                'error': '缺少原文'
            }), 400
        
        if not user_input:
            return jsonify({
                'success': False,
                'error': '用户输入为空'
            }), 400
        
        print(f"📝 文字比对请求:")
        print(f"   会话ID: {session_id}")
        print(f"   句子索引: {sentence_index}")
        print(f"   原文: '{original}'")
        print(f"   用户输入: '{user_input}'")
        
        # 检查文字比对器是否初始化
        if not text_comparator:
            return jsonify({
                'success': False,
                'error': '文字比对器未初始化'
            }), 500
        
        # 进行文字比对
        result = text_comparator.compare(original, user_input)
        
        print(f"✓ 比对完成: 准确率 {result['accuracy']}%, 错误数 {result['error_count']}")
        
        # 保存到会话记录（如果提供了session_id）
        if session_id and session_id in feedback_sessions:
            feedback_sessions[session_id]['records'].append({
                'index': sentence_index,
                'original': original,
                'user_input': user_input,
                'accuracy': result['accuracy'],
                'error_count': result['error_count'],
                'timestamp': time.time()
            })
            
            print(f"✓ 记录已保存到会话: {session_id}")
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        print(f"✗ 文字比对失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'比对失败: {str(e)}'
        }), 500

@app.route('/api/feedback/stats/<session_id>', methods=['GET'])
def get_feedback_stats(session_id):
    """获取训练统计"""
    try:
        if session_id not in feedback_sessions:
            return jsonify({
                'success': False,
                'error': '会话不存在'
            }), 404
        
        session = feedback_sessions[session_id]
        records = session['records']
        
        # 计算统计数据
        total_sentences = len(session['dialogue_data'].get('dialogues', []))
        completed_sentences = len(records)
        
        if completed_sentences > 0:
            total_accuracy = sum(r['accuracy'] for r in records)
            avg_accuracy = total_accuracy / completed_sentences
            perfect_count = sum(1 for r in records if r['accuracy'] == 100)
            perfect_rate = (perfect_count / completed_sentences) * 100
        else:
            avg_accuracy = 0
            perfect_count = 0
            perfect_rate = 0
        
        training_duration = time.time() - session['start_time']
        
        stats = {
            'total_sentences': total_sentences,
            'completed_sentences': completed_sentences,
            'average_accuracy': round(avg_accuracy, 2),
            'perfect_count': perfect_count,
            'perfect_rate': round(perfect_rate, 2),
            'training_duration': round(training_duration, 2),
            'records': records
        }
        
        print(f"📊 获取会话统计: {session_id}")
        print(f"   完成: {completed_sentences}/{total_sentences}")
        print(f"   平均准确率: {avg_accuracy:.2f}%")
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        print(f"✗ 获取统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# === 频谱镜子API端点 ===

@app.route('/spectrogram_mirror')
def spectrogram_mirror():
    """频谱镜子页面"""
    return render_template('spectrogram_mirror.html')

@app.route('/api/spectrogram/analyze', methods=['POST'])
def analyze_spectrogram():
    """分析音频频谱"""
    try:
        # 获取上传的音频文件
        audio_file = request.files.get('audio')
        target_phoneme = request.form.get('target_phoneme')  # 'zhi' 或 'chi'
        
        if not audio_file:
            return jsonify({
                'success': False,
                'error': '未上传音频文件'
            }), 400
        
        # 保存临时文件
        temp_filename = f'temp_spec_{uuid.uuid4().hex}.wav'
        temp_path = os.path.join(Config.TEMP_FOLDER, temp_filename)
        audio_file.save(temp_path)
        
        print(f"📊 开始频谱分析: {temp_filename}")
        print(f"   目标音素: {target_phoneme if target_phoneme else '未指定'}")
        
        # 获取分析器
        analyzer = get_analyzer(sample_rate=16000)
        
        # 完整分析
        result = analyzer.analyze_audio(temp_path, target_phoneme)
        
        # 清理临时文件
        try:
            os.remove(temp_path)
        except:
            pass
        
        if result['success']:
            print(f"✓ 频谱分析完成")
            print(f"   识别结果: {result['classification']['prediction']}")
            print(f"   置信度: {result['classification']['confidence']*100:.1f}%")
            print(f"   VOT: {result['features']['vot_ms']:.1f}ms")
            print(f"   送气强度: {result['features']['aspiration_score']:.1f}")
            if result.get('score'):
                print(f"   评分: {result['score']:.1f} ({result['grade']})")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"✗ 频谱分析失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/spectrogram/classify', methods=['POST'])
def classify_phoneme():
    """快速分类 zhi/chi"""
    try:
        audio_file = request.files.get('audio')
        
        if not audio_file:
            return jsonify({
                'success': False,
                'error': '未上传音频文件'
            }), 400
        
        # 保存临时文件
        temp_filename = f'temp_classify_{uuid.uuid4().hex}.wav'
        temp_path = os.path.join(Config.TEMP_FOLDER, temp_filename)
        audio_file.save(temp_path)
        
        # 获取分析器
        analyzer = get_analyzer()
        
        # 分类
        result = analyzer.classify_zhi_chi(temp_path)
        
        # 清理
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/spectrogram/compare', methods=['POST'])
def compare_with_template():
    """与标准模板对比"""
    try:
        audio_file = request.files.get('audio')
        template_type = request.form.get('template_type', 'zhi')  # 'zhi' 或 'chi'
        
        if not audio_file:
            return jsonify({
                'success': False,
                'error': '未上传音频文件'
            }), 400
        
        # 保存临时文件
        temp_filename = f'temp_compare_{uuid.uuid4().hex}.wav'
        temp_path = os.path.join(Config.TEMP_FOLDER, temp_filename)
        audio_file.save(temp_path)
        
        # 分析
        analyzer = get_analyzer()
        result = analyzer.analyze_audio(temp_path, target_phoneme=template_type)
        
        # 清理
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/spectrogram/vot', methods=['POST'])
def detect_vot_api():
    """VOT检测API"""
    try:
        audio_file = request.files.get('audio')
        
        if not audio_file:
            return jsonify({
                'success': False,
                'error': '未上传音频文件'
            }), 400
        
        # 保存临时文件
        temp_filename = f'temp_vot_{uuid.uuid4().hex}.wav'
        temp_path = os.path.join(Config.TEMP_FOLDER, temp_filename)
        audio_file.save(temp_path)
        
        # VOT检测
        analyzer = get_analyzer()
        result = analyzer.detect_vot(temp_path)
        
        # 清理
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# === 语音识别API端点（国内服务商）===

@app.route('/api/speech/recognize', methods=['POST'])
def recognize_speech():
    """
    语音识别API - 使用国内服务商（阿里云/百度等）
    替代浏览器的 Web Speech API（依赖 Google）
    
    支持两种格式：
    1. PCM 原始数据（format=pcm）- 快速，无需格式转换
    2. 其他音频格式（webm/mp3/wav 等）- 需要转换
    """
    try:
        # 获取音频数据
        audio_file = request.files.get('audio')
        provider = request.form.get('provider', 'baidu')  # 默认使用百度
        audio_format = request.form.get('format', 'auto')  # 格式标记
        
        if not audio_file:
            return jsonify({
                'success': False,
                'error': '未上传音频文件'
            }), 400
        
        # 最终的 WAV 文件路径
        temp_filename = f'temp_speech_{uuid.uuid4().hex}.wav'
        temp_path = os.path.join(Config.TEMP_FOLDER, temp_filename)
        
        # ========== 处理 PCM 格式（新方法，快速无转换） ==========
        pcm_data = None  # 保存原始 PCM 数据用于百度识别
        pcm_sample_rate = 16000  # PCM 采样率
        
        if audio_format == 'pcm':
            try:
                import wave
                
                # 获取 PCM 参数
                sample_rate = int(request.form.get('sample_rate', 16000))
                channels = int(request.form.get('channels', 1))
                sample_width = int(request.form.get('sample_width', 2))  # 2 = 16-bit
                
                print(f"🎤 接收 PCM 数据: {sample_rate}Hz, {channels}ch, {sample_width*8}bit")
                
                # 读取 PCM 数据
                pcm_data = audio_file.read()
                pcm_sample_rate = sample_rate
                
                # 直接写入 WAV 文件（只需添加文件头）
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(pcm_data)
                
                print(f"✓ PCM 数据已准备（直接识别，零转换）")
                print(f"   同时保存 WAV 文件用于播放（仅添加44字节文件头）")
                print(f"   时长: {len(pcm_data) / (sample_rate * sample_width):.2f}s")
                print(f"   大小: {len(pcm_data)} bytes")
                
                # 检查音频能量
                pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
                avg_energy = np.mean(np.abs(pcm_array))
                max_amplitude = np.max(np.abs(pcm_array))
                print(f"   音频能量: 平均 {avg_energy:.0f}, 最大 {max_amplitude}")
                
                if avg_energy < 100:
                    print(f"   ⚠️ 警告：音频能量过低，可能为静音或噪音")
                
            except Exception as e:
                print(f"❌ PCM 转换失败: {e}")
                return jsonify({
                    'success': False,
                    'error': f'PCM 转换失败: {str(e)}'
                }), 500
        
        # ========== 处理其他音频格式（旧方法，需要编解码） ==========
        else:
            # 保存上传的原始音频文件
            original_filename = audio_file.filename or 'audio.webm'
            file_ext = os.path.splitext(original_filename)[1].lower()
            
            temp_original = f'temp_original_{uuid.uuid4().hex}{file_ext}'
            temp_original_path = os.path.join(Config.TEMP_FOLDER, temp_original)
            audio_file.save(temp_original_path)
            
            if file_ext in ['.webm', '.ogg', '.mp3', '.m4a']:
                # 需要转换格式
                try:
                    from pydub import AudioSegment
                    
                    print(f"🔄 转换音频格式: {file_ext} → .wav")
                    
                    # 读取原始音频
                    audio = AudioSegment.from_file(temp_original_path)
                    
                    # 转换为 16kHz, 单声道 WAV（语音识别标准格式）
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    audio.export(temp_path, format='wav')
                    
                    print(f"✓ 音频转换成功")
                    
                    # 删除原始文件
                    try:
                        os.remove(temp_original_path)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"❌ 音频格式转换失败: {e}")
                    # 清理临时文件
                    try:
                        os.remove(temp_original_path)
                    except:
                        pass
                    return jsonify({
                        'success': False,
                        'error': f'音频格式转换失败: {str(e)}'
                    }), 500
            else:
                # 已经是 WAV 格式，直接重命名
                os.rename(temp_original_path, temp_path)
        
        try:
            result_text = ''
            
            if provider == 'dashscope':
                # 使用阿里云 DashScope（推荐）
                from config.speech_config import DASHSCOPE_API_KEY
                from config.dashscope_speech import DashScopeSpeechRecognizer
                
                if not DASHSCOPE_API_KEY or not DASHSCOPE_API_KEY.startswith('sk-'):
                    return jsonify({
                        'success': False,
                        'error': 'DashScope API Key 未配置或格式错误'
                    }), 500
                
                recognizer = DashScopeSpeechRecognizer(DASHSCOPE_API_KEY)
                result_text = recognizer.recognize(temp_path)
                
            elif provider == 'baidu':
                # 使用百度语音识别
                from speech_recognition.baidu_speech import BaiduSpeech, BAIDU_SDK_AVAILABLE
                from config.speech_config import BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY
                
                if not BAIDU_SDK_AVAILABLE:
                    return jsonify({
                        'success': False,
                        'error': '百度语音 SDK 未安装，请运行: pip install baidu-aip'
                    }), 500
                
                if not all([BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY]):
                    return jsonify({
                        'success': False,
                        'error': '百度语音配置不完整，请在 config/speech_config.py 中配置密钥'
                    }), 500
                
                baidu = BaiduSpeech(BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY)
                
                # 🎯 优先使用 PCM 格式（百度推荐格式，无需转换）
                if pcm_data is not None:
                    print(f"🚀 使用 PCM 格式直接识别（百度推荐格式）")
                    result_text = baidu.recognize_bytes(pcm_data, format='pcm', rate=pcm_sample_rate)
                else:
                    print(f"📝 使用 WAV 文件识别")
                    result_text = baidu.recognize_file(temp_path, format='wav', rate=16000)
                
            elif provider == 'aliyun':
                # 使用阿里云语音识别（传统API）
                from speech_recognition.aliyun_speech import AliyunSpeechSimple, ALIYUN_SDK_AVAILABLE
                from config.speech_config import ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_APP_KEY
                
                if not ALIYUN_SDK_AVAILABLE:
                    return jsonify({
                        'success': False,
                        'error': '阿里云 SDK 未安装，请运行: pip install aliyun-python-sdk-core aliyun-nls-python3-sdk'
                    }), 500
                
                if not all([ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_APP_KEY]):
                    return jsonify({
                        'success': False,
                        'error': '阿里云配置不完整，请在 config/speech_config.py 中配置密钥'
                    }), 500
                
                aliyun = AliyunSpeechSimple(ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_APP_KEY)
                result_text = aliyun.recognize_file(temp_path)
                
            else:
                return jsonify({
                    'success': False,
                    'error': f'不支持的服务商: {provider}'
                }), 400
            
            # 清理临时文件
            try:
                os.remove(temp_path)
            except:
                pass
            
            if result_text:
                print(f"✓ 识别成功: {result_text}")
                return jsonify({
                    'success': True,
                    'text': result_text,
                    'provider': provider
                })
            else:
                print(f"⚠️ 识别失败: API 返回空结果")
                print(f"   音频文件: {temp_path}")
                print(f"   服务商: {provider}")
                
                # 检查音频文件信息
                try:
                    import wave
                    with wave.open(temp_path, 'rb') as wf:
                        print(f"   WAV 信息: {wf.getnchannels()}ch, {wf.getframerate()}Hz, {wf.getnframes()} frames, {wf.getnframes()/wf.getframerate():.2f}s")
                except:
                    pass
                
                return jsonify({
                    'success': False,
                    'error': '识别失败，未能识别到语音内容。可能原因：音频太短、无有效语音、或 API 配置问题'
                })
                
        except Exception as e:
            # 清理临时文件
            try:
                os.remove(temp_path)
            except:
                pass
            raise
            
    except Exception as e:
        print(f"语音识别错误: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/speech/recognize_whisper', methods=['POST'])
def recognize_speech_whisper():
    """
    Whisper API 已移除 - 系统现在使用百度/阿里云语音识别
    保留此端点是为了向后兼容，会返回错误提示
    """
    return jsonify({
        'success': False,
        'error': 'Whisper 离线识别已从系统中移除，请使用百度或阿里云语音识别服务'
    }), 410  # 410 Gone - 资源已永久删除


@app.route('/api/speech/providers', methods=['GET'])
def get_speech_providers():
    """获取可用的语音识别服务商列表"""
    try:
        from speech_recognition.baidu_speech import BAIDU_SDK_AVAILABLE
        from speech_recognition.aliyun_speech import ALIYUN_SDK_AVAILABLE
        from config.speech_config import (
            BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY,
            ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_APP_KEY,
            DASHSCOPE_API_KEY
        )
        
        providers = []
        
        # 检查百度（优先使用）
        if BAIDU_SDK_AVAILABLE and all([BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY]):
            providers.append({
                'id': 'baidu',
                'name': '百度语音',
                'available': True
            })
        else:
            providers.append({
                'id': 'baidu',
                'name': '百度语音',
                'available': False,
                'reason': '未配置或SDK未安装'
            })
        
        # 检查 DashScope（阿里云新API，备选）
        dashscope_available = False
        if DASHSCOPE_API_KEY and DASHSCOPE_API_KEY.startswith('sk-'):
            try:
                from config.dashscope_speech import DashScopeSpeechRecognizer
                recognizer = DashScopeSpeechRecognizer(DASHSCOPE_API_KEY)
                dashscope_available = recognizer.is_available()
            except Exception as e:
                print(f"DashScope 检查失败: {e}")
        
        if dashscope_available:
            providers.append({
                'id': 'dashscope',
                'name': '阿里云 DashScope',
                'available': True
            })
        else:
            providers.append({
                'id': 'dashscope',
                'name': '阿里云 DashScope',
                'available': False,
                'reason': '未配置或API Key无效'
            })
        
        # 检查阿里云传统API
        if ALIYUN_SDK_AVAILABLE and all([ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_APP_KEY]):
            providers.append({
                'id': 'aliyun',
                'name': '阿里云语音（传统）',
                'available': True
            })
        else:
            providers.append({
                'id': 'aliyun',
                'name': '阿里云语音（传统）',
                'available': False,
                'reason': '未配置或SDK未安装'
            })
        
        # Whisper 离线识别已移除，系统现在使用百度/阿里云语音识别
        
        return jsonify({
            'success': True,
            'providers': providers
        })
        
    except Exception as e:
        print(f"获取服务商列表错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'success': False,
        'error': '文件太大，请上传小于16MB的音频文件'
    }), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500

# 创建静态文件目录和模板目录
def create_web_directories():
    """创建Web应用所需的目录"""
    directories = ['templates', 'static', 'static/css', 'static/js', 'static/images']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

if __name__ == '__main__':
    # 创建Web目录
    create_web_directories()
    
    # 初始化系统
    if init_system():
        print("🚀 启动Web服务器...")
        print(f"访问地址: http://localhost:{Config.PORT}")
        
        # 启动Flask应用（支持WebSocket）
        if WEBSOCKET_AVAILABLE and socketio:
            print("✓ 使用WebSocket支持启动服务器")
            # 检查是否存在SSL证书文件
            ssl_cert_path = '/opt/ssl/cert.pem'
            ssl_key_path = '/opt/ssl/key.pem'
            
            if os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
                print(f"🔒 启用HTTPS WebSocket，访问地址: https://8.148.200.151:{Config.PORT}")
                import ssl
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(ssl_cert_path, ssl_key_path)
                socketio.run(
                    app,
                    host='0.0.0.0',
                    port=Config.PORT,
                    debug=Config.DEBUG,
                    use_reloader=False,  # WebSocket模式下禁用重载器
                    allow_unsafe_werkzeug=True,  # 生产环境允许Werkzeug
                    ssl_context=ssl_context
                )
            else:
                print(f"⚠️ 未找到SSL证书，使用HTTP WebSocket模式")
                print(f"📱 注意：手机录音需要HTTPS环境")
                socketio.run(
                    app,
                    host='0.0.0.0',
                    port=Config.PORT,
                    debug=Config.DEBUG,
                    use_reloader=False,  # WebSocket模式下禁用重载器
                    allow_unsafe_werkzeug=True  # 生产环境允许Werkzeug
                )
        else:
            print("⚠ 使用标准HTTP模式启动服务器")
            # 检查是否存在SSL证书文件
            ssl_cert_path = '/opt/ssl/cert.pem'
            ssl_key_path = '/opt/ssl/key.pem'
            
            if os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
                print(f"🔒 启用HTTPS，访问地址: https://8.148.200.151:{Config.PORT}")
                app.run(
                    host='0.0.0.0',
                    port=Config.PORT,
                    debug=Config.DEBUG,
                    threaded=True,
                    ssl_context=(ssl_cert_path, ssl_key_path)
                )
            else:
                print(f"⚠️ 未找到SSL证书，使用HTTP模式")
                print(f"📱 注意：手机录音需要HTTPS环境")
                print(f"访问地址: http://8.148.200.151:{Config.PORT}")
                app.run(
                    host='0.0.0.0',
                    port=Config.PORT,
                    debug=Config.DEBUG,
                    threaded=True
                )
    else:
        print("❌ 系统初始化失败，无法启动Web服务器")
        exit(1)
