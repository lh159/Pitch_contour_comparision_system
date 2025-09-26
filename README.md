# 音高曲线比对系统

一个基于Python的中文语音音高曲线比对分析系统，专为语音训练和发音纠正设计。

## 功能特性

- 🎯 **音高曲线比对**: 对比用户发音与标准发音的音高曲线
- 🎙️ **实时录音指导**: 提供实时的发音指导和提示
- 📊 **详细分析报告**: 生成可视化的音高对比图表
- 🔊 **多种TTS支持**: 支持阿里云TTS和Edge TTS
- 🎨 **现代化界面**: 响应式Web界面，支持多页面导航
- 📱 **移动端适配**: 支持手机和平板设备

## 系统架构

### 多页面应用结构
- **首页** (`/home`): 选择练习模式
- **标准发音** (`/standard_audio`): 播放和分析标准发音
- **录音界面** (`/recording`): 用户录音和实时指导
- **结果分析** (`/results`): 显示对比分析结果

### 核心组件
- `web_interface.py`: Flask Web应用主程序
- `chinese_tone_analyzer.py`: 中文声调分析核心
- `realtime_sync.py`: 实时同步和WebSocket服务
- `recording-guide.js`: 前端录音指导组件

## 快速开始

### 1. 环境要求
- Python 3.8+
- FFmpeg (音频处理)
- 现代浏览器 (Chrome/Firefox/Safari)

### 2. 安装依赖
```bash
# 运行自动安装脚本
python install_dependencies.py
```

### 3. 配置API密钥
```bash
# 复制配置模板
cp config.template.py config.py

# 编辑配置文件，填入您的API密钥
# - ALIBABA_TTS_CONFIG['api_key']: 阿里云TTS API密钥
# - DASHSCOPE_API_KEY: 阿里云DashScope API密钥
# - DEEPSEEK_API_KEY: DeepSeek API密钥
```

### 4. 启动应用
```bash
python start.py
```

访问 http://localhost:9999 开始使用

## 使用说明

### 基本流程
1. **选择模式**: 在首页选择"文本练习"或"场景对话"
2. **标准发音**: 输入文本，生成标准发音音频
3. **用户录音**: 选择录音模式（自由录音/实时指导）
4. **结果分析**: 查看音高对比图表和详细分析

### 录音模式
- **自由录音**: 用户自由录制，适合熟练用户
- **实时指导**: 根据标准发音时间戳提供实时提示，适合初学者

### 分析功能
- 音高曲线对比可视化
- 中文声调识别和分析
- 发音准确度评分
- 详细的改进建议

## API接口

### 主要端点
- `POST /api/tts/generate`: 生成TTS音频
- `POST /api/audio/upload`: 上传用户录音
- `POST /api/compare`: 执行音高比对分析
- `WebSocket /socket.io`: 实时通信

### WebSocket事件
- `recording_guide_started`: 录音指导开始
- `recording_guide_stopped`: 录音指导结束
- `pitch_analysis_progress`: 音高分析进度

## 技术栈

### 后端
- **Flask**: Web框架
- **Socket.IO**: 实时通信
- **librosa**: 音频分析
- **numpy**: 数值计算
- **matplotlib**: 图表生成

### 前端
- **Bootstrap 5**: UI框架
- **Chart.js**: 图表库
- **Socket.IO Client**: 实时通信
- **Web Audio API**: 音频录制

### AI/语音处理
- **FunASR**: 阿里达摩院语音识别
- **Edge TTS**: 微软语音合成
- **阿里云TTS**: 情感语音合成

## 配置选项

### TTS配置
```python
ALIBABA_TTS_CONFIG = {
    'api_key': 'your_api_key',
    'default_voice': 'zhimiao_emo',
    'default_emotion': 'neutral'
}
```

### 音高分析配置
```python
PITCH_MIN_FREQ = 75   # 最小基频
PITCH_MAX_FREQ = 600  # 最大基频
PITCH_TIME_STEP = 0.01  # 时间步长
```

### 评分权重配置
```python
SCORE_WEIGHTS = {
    'trend': 0.5,        # 趋势一致性
    'correlation': 0.25, # 相关性
    'stability': 0.15,   # 稳定性
    'range': 0.1         # 音域适配
}
```

## 开发说明

### 项目结构
```
├── web_interface.py          # Flask应用主程序
├── chinese_tone_analyzer.py  # 音高分析核心
├── realtime_sync.py         # 实时同步服务
├── config.py                # 配置文件
├── templates/               # HTML模板
├── static/                  # 静态资源
│   ├── css/                # 样式文件
│   └── js/                 # JavaScript文件
├── uploads/                # 用户上传音频
├── outputs/                # 分析结果输出
└── temp/                   # 临时文件
```

### 添加新功能
1. 在相应的Python模块中添加后端逻辑
2. 在`templates/`中添加HTML模板
3. 在`static/js/`中添加前端JavaScript
4. 更新路由配置

## 故障排除

### 常见问题
1. **音频录制失败**: 检查浏览器麦克风权限
2. **TTS生成失败**: 验证API密钥配置
3. **分析结果异常**: 检查音频文件格式和质量

### 日志查看
应用运行时会在控制台输出详细日志，包括：
- API调用状态
- 音频处理进度
- WebSocket连接状态
- 错误信息

## 许可证

本项目采用MIT许可证。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 联系方式

如有问题或建议，请通过GitHub Issues联系。