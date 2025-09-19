# -*- coding: utf-8 -*-
"""
音高曲线比对系统配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """系统配置类"""
    
    # === TTS配置 ===
    # 阿里云情感TTS配置
    ALIBABA_TTS_CONFIG = {
        'api_key': 'sk-26cd7fe2661444f2804896a590bdbbc0',
        'default_voice': 'zhimiao_emo',      # 默认使用知妙女声（情感TTS）
        'default_emotion': 'neutral',         # 默认中性情感
        'sample_rate': 22050,                # 音频采样率（SDK推荐）
        'format': 'mp3',                     # 音频格式
        'enabled': True                      # 启用阿里云TTS
    }
    
    # Edge TTS配置 (备用)
    EDGE_TTS_CONFIG = {
        'enabled': True,
        'voice': 'zh-CN-XiaoxiaoNeural',
        'rate': '+0%',
        'volume': '+0%'
    }
    
    # === 阿里达摩院语音配置 ===
    ALIBABA_PARAFORMER_API_KEY = os.getenv('ALIBABA_PARAFORMER_API_KEY', '')
    ALIBABA_VAD_MODEL = 'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch'  # VAD模型名称
    ALIBABA_ASR_MODEL = 'iic/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404'  # 带时间戳的ASR模型
    
    # === DashScope API配置（Fun-ASR云端服务）===
    DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
    
    # === 音频配置 ===
    SAMPLE_RATE = 16000  # 采样率
    AUDIO_FORMAT = 'wav'  # 音频格式
    
    # === 文件路径配置 ===
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    TEMP_FOLDER = 'temp'
    STATIC_FOLDER = 'static'
    
    # === 音高分析配置 ===
    PITCH_MIN_FREQ = 75   # 最小基频 (Hz)
    PITCH_MAX_FREQ = 600  # 最大基频 (Hz)
    PITCH_TIME_STEP = 0.01  # 时间步长 (秒)
    
    # === VAD配置 ===
    VAD_MIN_SPEECH_DURATION = 0.1  # 最小语音段长度 (秒)
    VAD_MAX_SILENCE_DURATION = 0.5  # 最大静音段长度 (秒)
    VAD_ENERGY_THRESHOLD = 0.01  # 能量阈值
    VAD_ENABLED = True  # 是否启用VAD
    
    # === 评分配置 ===
    # 针对听障人士优化的权重配置 - 强调音调变化重要性
    SCORE_WEIGHTS = {
        'trend': 0.5,          # 趋势一致性权重 (提高到50% - 最重要)
        'correlation': 0.25,   # 相关性权重 (降低到25%)
        'stability': 0.15,     # 稳定性权重 (降低到15%)
        'range': 0.1           # 音域适配权重 (保持10%)
    }
    
    # === 中文声调特征配置 ===
    CHINESE_TONE_CONFIG = {
        'tone_patterns': {
            1: 'flat_high',     # 阴平：高平调
            2: 'rising',        # 阳平：升调
            3: 'dipping',       # 上声：降升调
            4: 'falling',       # 去声：降调
            0: 'neutral'        # 轻声
        },
        'tone_weights': {
            1: 1.0,  # 阴平权重
            2: 1.2,  # 阳平权重 (升调更重要)
            3: 1.5,  # 上声权重 (最复杂，权重最高)
            4: 1.3,  # 去声权重 (降调重要)
            0: 0.8   # 轻声权重
        },
        'pattern_sensitivity': 0.8  # 声调模式匹配敏感度
    }
    
    # === Web配置 ===
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key_change_in_production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 5001))
    
    # === DeepSeek API配置 ===
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    
    # === 场景对话配置 ===
    MAX_SCENARIO_LENGTH = 200  # 场景描述最大长度
    DEFAULT_DIALOGUE_ROUNDS = 6  # 默认对话轮数
    DIALOGUE_SESSION_TIMEOUT = 3600  # 对话会话超时时间（秒）
    
    # IndexTTS2配置已移除
    
    # === 情感TTS配置 ===
    AVAILABLE_EMOTIONS = {
        'neutral': '中性',
        'happy': '开心',
        'sad': '悲伤', 
        'angry': '生气',
        'gentle': '温柔',
        'serious': '严肃',
        'surprise': '惊讶',
        'fear': '害怕'
    }
    
    # 场景对话配置
    DIALOGUE_CONFIG = {
        'male_voice': 'zhifeng_emo',     # 男声发音人
        'female_voice': 'zhimiao_emo',   # 女声发音人
        'default_emotion': 'neutral',     # 默认情感
        'volume': 70,                     # 音量
        'speech_rate': 0                  # 语速
    }
    
    # === 对话语音缓存配置 ===
    DIALOGUE_AUDIO_CACHE_SIZE = 100  # 缓存的对话音频数量
    DIALOGUE_AUDIO_CACHE_TTL = 3600  # 缓存过期时间（秒）
    
    @classmethod
    def create_directories(cls):
        """创建必要的目录"""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.OUTPUT_FOLDER, 
            cls.TEMP_FOLDER,
            cls.STATIC_FOLDER
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
