# 阿里云情感TTS使用说明

## 概述

系统已成功集成阿里云智能语音情感TTS服务，支持多种情感表达的高质量中文语音合成。

## 主要特性

### 🎭 情感表达
- **知妙女声** (zhimiao_emo) - 支持17种情感
- **知锋男声** (zhifeng_emo) - 支持6种情感

### 📊 支持的情感类型

#### 知妙女声 (17种情感)
- `neutral` - 中性
- `happy` - 开心  
- `sad` - 悲伤
- `angry` - 生气
- `gentle` - 温柔
- `serious` - 严肃
- `surprise` - 惊讶
- `fear` - 害怕
- `affectionate` - 深情
- `frustrated` - 沮丧
- `embarrassed` - 尴尬
- `disgust` - 厌恶
- `jealousy` - 嫉妒
- `newscast` - 播报
- `customer-service` - 客服
- `story` - 小说
- `living` - 直播

#### 知锋男声 (6种情感)
- `neutral` - 中性
- `happy` - 开心
- `sad` - 悲伤
- `angry` - 生气
- `fear` - 害怕
- `surprise` - 惊讶

## 使用方法

### 基本语音合成
```python
from tts_module import get_tts_manager

# 获取TTS管理器
tts_manager = get_tts_manager()

# 生成标准发音
success = tts_manager.generate_standard_audio(
    text="你好，欢迎使用语音练习系统！",
    output_path="output.mp3"
)
```

### 情感语音合成
```python
# 生成开心的语音
success = tts_manager.generate_emotion_audio(
    text="今天天气真好！",
    emotion="happy",
    output_path="happy_audio.mp3"
)

# 生成温柔的女声
success = tts_manager.generate_emotion_audio(
    text="请慢慢说，我会耐心听。",
    emotion="gentle",
    voice="zhimiao_emo",
    output_path="gentle_audio.mp3"
)
```

### 角色对话语音
```python
# 男性角色
success = tts_manager.generate_dialogue_audio(
    text="我是AI助手小明。",
    role_type="serious",
    emotion="neutral",
    output_path="male_dialogue.mp3"
)

# 女性角色
success = tts_manager.generate_dialogue_audio(
    text="欢迎来到语音练习！",
    role_type="gentle",
    emotion="happy",
    output_path="female_dialogue.mp3"
)
```

## 系统优势

### 🔄 智能降级机制
1. **阿里云情感TTS** (最高优先级) - 高质量情感语音
2. **Edge TTS** (备用) - 免费在线TTS
3. **离线TTS** (最后备用) - 本地TTS引擎

### 🎯 针对中文优化
- 专门为中文语音合成优化
- 支持声调准确表达
- 自然的语音节奏和停顿

### 💡 易于使用
- 统一的API接口
- 自动错误处理和降级
- 详细的日志记录

## 配置说明

### API密钥配置
在 `config.py` 中设置：
```python
ALIBABA_TTS_CONFIG = {
    'api_key': 'your_dashscope_api_key_here',
    'default_voice': 'zhimiao_emo',
    'default_emotion': 'neutral',
    'sample_rate': 48000,
    'enabled': True
}
```

### 检查TTS状态
```python
# 检查可用的TTS引擎
engines = tts_manager.get_available_engines()
print(f"可用引擎: {engines}")

# 检查是否支持情感TTS
if tts_manager.is_emotion_supported():
    emotions = tts_manager.get_available_emotions()
    print(f"支持的情感: {emotions}")
```

## 故障排除

### 常见问题
1. **API密钥错误** - 检查DashScope API密钥是否正确
2. **网络连接问题** - 确保网络连接正常
3. **依赖包缺失** - 运行 `pip install dashscope>=1.20.0`

### 备用方案
如果阿里云TTS不可用，系统会自动降级到：
- Edge TTS (需要网络连接)
- 离线TTS (完全本地化)

## 性能优化

### 音频质量设置
- **高质量**: sample_rate=48000, format='mp3'
- **标准质量**: sample_rate=24000, format='mp3'  
- **快速合成**: sample_rate=16000, format='wav'

### 缓存机制
系统会自动缓存生成的音频文件，提高重复使用效率。

---

*注：阿里云TTS服务需要有效的API密钥，请确保账户余额充足。*
