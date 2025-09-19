# 音高曲线比对系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**AI智能发音练习与评估平台**

*帮助您改进中文发音准确性*

</div>

## 🌟 系统特色

- 🎯 **精准音高分析**: 基于parselmouth库进行专业级音高提取
- 🎨 **智能对比算法**: DTW时间对齐 + 多维度相似度计算
- 📊 **可视化分析**: 直观的音高曲线对比图表
- 🎯 **智能评分**: 四维度评分体系，提供个性化改进建议
- 🔊 **多TTS支持**: 百度TTS、Edge TTS、离线TTS多重选择
- 🌐 **Web界面**: 现代化响应式设计，支持在线录音
- 🚀 **增强对齐**: VAD语音检测 + ASR时间轴对齐，精确同步用户发音
- 🛡️ **录音质量验证**: 智能检测真实录音，拒绝静音和假音频
- ✂️ **精确时长截断**: 音高曲线显示精准匹配TTS实际语音时长

## 🚀 快速开始

### 1. 环境要求

- Python 3.8或更高版本
- 8GB RAM（推荐）
- 支持音频设备的系统
- 网络连接（用于TTS API调用）

### 2. 一键安装

```bash
# 克隆项目
git clone https://github.com/lh159/Pitch_contour_comparision_system.git
cd Pitch_contour_comparision_system

# 运行自动安装脚本
python install_dependencies.py
```

安装脚本会自动：
- ✅ 检查系统要求
- ✅ 安装所有必需依赖
- ✅ 询问安装可选TTS组件
- ✅ 创建环境配置文件
- ✅ 验证系统完整性

### 3. 配置TTS服务（可选）

如果需要使用百度TTS（推荐），请：

1. 在百度智能云申请TTS服务并获取密钥
2. 编辑 `.env` 文件，填入你的密钥：

```env
BAIDU_API_KEY=your_baidu_api_key_here
BAIDU_SECRET_KEY=your_baidu_secret_key_here
BAIDU_VOICE_PER=0
```

> 💡 **提示**: 系统支持多种TTS服务，即使不配置百度TTS也能正常运行（会使用Edge TTS或离线TTS）

### 4. 启动系统

```bash
python web_interface.py
```

然后在浏览器中访问：`http://localhost:5000`

## 📖 使用指南

### Web界面使用

1. **输入词汇**: 在文本框中输入要练习的中文词汇
2. **生成标准音**: 点击"生成标准发音"按钮
3. **录制发音**: 点击"开始录音"录制您的发音
4. **比对分析**: 点击"开始比对分析"获得评分结果

### 命令行使用

```python
from main_controller import PitchComparisonSystem

# 初始化系统
system = PitchComparisonSystem()
system.initialize()

# 处理单个词汇
result = system.process_word("你好", "user_audio.wav")
print(f"得分: {result['score']['total_score']}")
```

## 🏗️ 系统架构

```
音高曲线比对系统
├── 🎤 TTS模块 (tts_module.py)                    # 多TTS服务支持
├── 🎵 音频处理 (audio_plot.py)                   # 基于parselmouth
├── 🔍 比对算法 (pitch_comparison.py)             # DTW对齐 + 相似度计算  
├── 🚀 增强对齐 (enhanced_pitch_alignment.py)     # VAD + ASR增强对齐
├── 🛡️ VAD模块 (vad_module.py)                   # 语音活动检测
├── 🎯 ASR模块 (fun_asr_module.py)               # Fun-ASR时间戳对齐
├── 📊 评分系统 (scoring_algorithm.py)            # 四维度智能评分
├── 📈 可视化 (visualization.py)                  # 图表生成
├── 🌐 Web界面 (web_interface.py)                 # Flask后端
├── 🎯 主控制器 (main_controller.py)              # 系统集成
└── ⚙️ 配置管理 (config.py)                       # 系统配置
```

## 🎯 评分体系

### 四维度评分

| 维度 | 权重 | 说明 |
|------|------|------|
| 🎵 **音高准确性** | 40% | 基于皮尔逊相关系数 |
| 📈 **音调变化** | 30% | 声调趋势一致性 |
| 🎯 **发音稳定性** | 20% | 基于RMSE稳定度 |
| 🎼 **音域适配** | 10% | 音高范围合理性 |

### 评级标准

- 🌟 **优秀** (90-100分): 发音非常准确
- 👍 **良好** (80-89分): 发音基本准确
- 📖 **中等** (70-79分): 需要练习改进
- 📚 **及格** (60-69分): 基础掌握
- 💪 **需要改进** (<60分): 建议多练习

## 🚀 增强功能详解

### VAD语音活动检测

系统集成Fun-ASR的VAD模块，能够：
- 🎯 **精确检测语音段落**：自动识别TTS和用户录音的有效语音时间
- ✂️ **智能截断显示**：音高曲线图只显示实际说话时间，不包含静音
- 🔍 **质量验证**：检测录音是否包含真实语音内容

### ASR时间轴对齐

基于Fun-ASR的高精度语音识别：
- 📐 **字级别时间戳**：获取每个字的准确发音时间
- 🎯 **智能对齐策略**：用户发音与TTS标准发音精确同步
- 🔄 **多重降级方案**：ASR失败时自动使用VAD对齐

### 录音质量验证

多维度检测确保录音真实性：
- 🛡️ **静音检测**：拒绝空白或静音录音
- 📊 **能量分析**：检测音频动态范围和信号强度
- ⏱️ **时长验证**：确保录音时长合理（>0.3秒）
- 🎵 **音高有效性**：验证是否能提取到有效音高数据

### 增强可视化

- 📈 **精确时间轴**：图表X轴精确对应实际语音时长
- 🎨 **智能标注**：TTS文本标注准确对应音高曲线位置
- 🔍 **对齐状态显示**：实时显示使用的对齐方法和效果

## 🔧 高级配置

### 增强功能开关

```python
# config.py中的增强功能配置
ENABLE_VAD = True                    # 语音活动检测
ENABLE_ENHANCED_ALIGNMENT = True     # 增强对齐功能
ENABLE_FUNASR = True                # Fun-ASR时间戳功能

# VAD配置
VAD_CONFIG = {
    'model': 'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch',
    'model_revision': 'v2.0.4',
    'mode': 'offline'
}

# ASR配置  
ASR_CONFIG = {
    'model': 'iic/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404',
    'model_revision': 'v2.0.4',
    'mode': 'offline'
}
```

### TTS服务配置

系统支持多种TTS服务，按优先级自动选择：

1. **百度TTS** - 质量高，性价比好，需要API密钥
2. **Edge TTS** - 免费使用，质量良好
3. **离线TTS** - 本地合成，无需网络

### 音高分析参数

```python
# config.py中可调整的参数
PITCH_MIN_FREQ = 75      # 最小基频 (Hz)
PITCH_MAX_FREQ = 600     # 最大基频 (Hz)
PITCH_TIME_STEP = 0.01   # 时间步长 (秒)
```

### 评分权重调整

```python
SCORE_WEIGHTS = {
    'correlation': 0.4,    # 相关性权重
    'trend': 0.3,          # 趋势权重  
    'stability': 0.2,      # 稳定性权重
    'range': 0.1           # 音域权重
}
```

## 🎨 自定义扩展

### 添加新的TTS引擎

```python
from tts_module import TTSBase

class MyTTS(TTSBase):
    def synthesize(self, text: str, output_path: str) -> bool:
        # 实现你的TTS逻辑
        pass
```

### 自定义评分算法

```python
from scoring_algorithm import ScoringSystem

class CustomScoring(ScoringSystem):
    def calculate_score(self, metrics: dict) -> dict:
        # 实现自定义评分逻辑
        pass
```

## 📊 API接口

### REST API端点

- `POST /api/tts/generate` - 生成标准发音
- `POST /api/audio/upload` - 上传用户音频
- `POST /api/compare` - 执行音高比对
- `GET /api/system/status` - 获取系统状态

### 响应格式

```json
{
  "success": true,
  "score": {
    "total_score": 85.5,
    "level": "良好",
    "component_scores": {
      "accuracy": 82.0,
      "trend": 88.0,
      "stability": 85.0,
      "range": 87.0
    },
    "feedback": "您的发音基本准确..."
  }
}
```

## 🧪 测试

### 运行单元测试

```bash
# 测试TTS模块
python tts_module.py

# 测试音高比较
python pitch_comparison.py

# 测试评分系统
python scoring_algorithm.py

# 测试增强功能
python test_enhanced_pitch_comparison.py

# 测试VAD模块
python vad_module.py

# 测试ASR功能
python fun_asr_module.py

# 完整系统测试
python main_controller.py "你好" "test_audio.wav"
```

### 增强功能测试

```bash
# 测试增强音高对齐功能
python test_enhanced_pitch_comparison.py

# 测试录音质量验证
python -c "
from enhanced_pitch_alignment import EnhancedPitchAligner
aligner = EnhancedPitchAligner()
result = aligner.validate_user_audio('your_audio.wav')
print(f'录音质量: {result}')
"

# 测试VAD检测
python -c "
from vad_module import VADProcessor
vad = VADProcessor()
result = vad.detect_speech('your_audio.wav')
print(f'语音段落: {result}')
"
```

### 性能基准

| 操作 | 预期时间 |
|------|----------|
| TTS生成 | < 3秒 |
| 音高提取 | < 2秒 |
| 曲线比对 | < 3秒 |
| 图表生成 | < 2秒 |
| **总响应时间** | **< 10秒** |

## 🔧 故障排除

### 常见问题

**Q: TTS生成失败**
```bash
# 检查网络连接和API密钥
python -c "from tts_module import TTSManager; TTSManager().get_available_engines()"
```

**Q: 音频录制无权限**
- 检查浏览器麦克风权限设置
- 确保使用HTTPS或localhost访问

**Q: 依赖安装失败**
```bash
# 手动安装核心依赖
pip install parselmouth numpy matplotlib flask
```

**Q: 图表显示异常**
- 检查中文字体安装
- 确保matplotlib后端配置正确

### 日志查看

系统运行时会在控制台输出详细日志：
- ✅ 成功操作
- ⚠️ 警告信息
- ❌ 错误信息

## 🚀 部署指南

### 本地部署

```bash
python web_interface.py
# 访问: http://localhost:5000
```

### Docker部署

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "web_interface.py"]
```

### 云端部署

支持部署到各大云平台：
- 阿里云
- AWS
- Google Cloud

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 开发规范

- 遵循PEP 8代码风格
- 添加适当的注释和文档
- 编写单元测试
- 更新README文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [parselmouth](https://github.com/YannickJadoul/Parselmouth) - 音频分析核心
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [百度智能云TTS](https://cloud.baidu.com/product/speech) - TTS服务
- [Bootstrap](https://getbootstrap.com/) - 前端UI框架

## 📮 联系我们

- 📧 Email: lh159@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/lh159/Pitch_contour_comparision_system/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/lh159/Pitch_contour_comparision_system/discussions)

---

<div align="center">

**用智能科技，让发音更准确** 🎯

Made with ❤️ by lh159

</div>
