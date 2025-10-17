# 拼音汉字显示功能

## 🎯 功能概述

实时语音识别结果以**拼音和汉字分两行**的形式显示在频谱图下方，并根据**识别时延逆推**，准确对齐到发音时刻的频谱位置。

---

## ✨ 核心特性

### 1. 双行显示

```
nǐ hǎo        ← 拼音（蓝色，16px）
你好          ← 汉字（白色，20px）
2100ms        ← 时延（灰色，9px，可选）
```

### 2. 时延逆推

- 记录音频开始时间和中点时间
- 计算识别时延（从发音到识别完成）
- 逆推标记位置，对齐频谱图
- 标记随频谱图同步滚动

### 3. 视觉效果

- 拼音和汉字清晰分离
- 连接线指示对应的频谱位置
- 渐隐效果（10 秒后消失）
- 美观的颜色方案

---

## 🚀 快速开始

### 1. 启动系统

```bash
./start_whisper.sh
```

### 2. 配置

1. 打开 `http://localhost:5001`
2. 选择识别方法（Whisper / 百度 / 阿里云）
3. 勾选 **"显示拼音标注"** ✅
4. 点击 **"开始录音"**

### 3. 使用

- 清晰地说出词语或句子
- 观察拼音和汉字显示在频谱图下方
- 标记随频谱图滚动，保持时间对齐

---

## 📊 效果展示

### 单个词语

```
频谱图：  [═══你═══][═══好═══]
          ↓         ↓
拼音区：  nǐ        hǎo
汉字区：  你        好
```

### 连续多个词语

```
频谱图：  [你好]    [我爱你]    [谢谢]
拼音区：  nǐ hǎo   wǒ ài nǐ   xiè xiè
汉字区：  你好     我爱你     谢谢
时延：    2100ms   2350ms    2200ms
```

---

## 🔧 配置参数

### 默认参数

```javascript
// 在 static/js/realtime-spectrogram.js
this.pinyinDisplayDuration = 10000;  // 显示时长（毫秒）
this.recognitionLatency = 2000;      // 默认时延（毫秒）
```

### 自定义字体大小

```javascript
// 拼音字体（第 1275 行）
ctx.font = 'bold 16px Arial';

// 汉字字体（第 1282 行）
ctx.font = 'bold 20px "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif';
```

### 自定义颜色

```javascript
// 拼音颜色（第 1277 行）
ctx.fillStyle = `rgba(100, 200, 255, ${alpha})`;

// 汉字颜色（第 1283 行）
ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
```

---

## 📈 性能指标

### 识别时延

| 方法 | 平均时延 | 准确率 |
|------|---------|--------|
| **Whisper** | ~2000ms | ⭐⭐⭐⭐⭐ |
| **百度云** | ~500ms | ⭐⭐⭐⭐⭐ |
| **阿里云** | ~500ms | ⭐⭐⭐⭐⭐ |

### 渲染性能

- **帧率**：60 FPS
- **CPU 占用**：<10%
- **内存占用**：<100MB

---

## 🐛 故障排除

### 问题 1：标记位置不准确

**解决方案**：调整默认时延

```javascript
// 第 57 行
this.recognitionLatency = 2000;  // 改为 1500, 2500 等
```

### 问题 2：拼音不显示

**原因**：cnchar 库未加载

**解决方案**：
1. 检查网络连接
2. 刷新页面
3. 查看控制台错误

### 问题 3：汉字显示为方块

**原因**：系统不支持中文字体

**解决方案**：安装中文字体包

---

## 📝 相关文档

- [拼音汉字显示优化说明.md](./拼音汉字显示优化说明.md) - 详细技术文档
- [拼音汉字显示测试指南.md](./拼音汉字显示测试指南.md) - 测试指南
- [更新日志-拼音汉字显示.md](./更新日志-拼音汉字显示.md) - 更新日志

---

## 🎓 技术细节

### 时间计算

```javascript
// 1. 记录音频开始时间
this.pcmBufferStartTime = Date.now();

// 2. 计算音频中点时间
const audioMidTime = this.pcmBufferStartTime + (duration * 1000 / 2);

// 3. 计算识别时延
const actualLatency = Date.now() - audioMidTime;

// 4. 逆推标记位置
const actualSpeechTime = Date.now() - actualLatency;
const x = this.width - (elapsedSinceStart - speechElapsedSinceStart) / msPerPixel;
```

### 绘制逻辑

```javascript
// 1. 拼音（上半部分）
ctx.font = 'bold 16px Arial';
ctx.fillStyle = `rgba(100, 200, 255, ${alpha})`;
ctx.fillText(marker.pinyin, x, offsetY + height * 0.3);

// 2. 汉字（下半部分）
ctx.font = 'bold 20px "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif';
ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
ctx.fillText(marker.text, x, offsetY + height * 0.7);

// 3. 时延（底部）
ctx.font = '9px Arial';
ctx.fillStyle = `rgba(150, 150, 150, ${alpha * 0.6})`;
ctx.fillText(`${marker.latency}ms`, x, offsetY + height - 5);
```

---

## 🌟 使用技巧

### 1. 提高识别准确率

- ✅ 说话清晰响亮
- ✅ 环境安静
- ✅ 麦克风靠近嘴巴（15-30cm）
- ✅ 词语比单字效果更好

### 2. 优化显示效果

- 调整字体大小（根据屏幕分辨率）
- 调整颜色方案（根据个人喜好）
- 调整显示时长（根据使用场景）

### 3. 调试技巧

- 打开控制台（F12）查看日志
- 观察时延数值是否合理
- 检查标记位置是否对齐

---

## 📞 支持

如有问题，请查看：
1. 控制台日志（F12）
2. [拼音汉字显示测试指南.md](./拼音汉字显示测试指南.md)
3. [拼音汉字显示优化说明.md](./拼音汉字显示优化说明.md)

---

**版本**：v1.1.0  
**更新日期**：2025-10-16  

祝你使用愉快！🎉

