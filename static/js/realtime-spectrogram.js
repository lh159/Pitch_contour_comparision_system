/**
 * 实时频谱可视化系统
 * 提供实时音频流处理和Canvas频谱渲染
 */

class RealtimeSpectrogramRenderer {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.width = canvas.width;
        this.height = canvas.height;
        
        // 配置参数
        this.options = {
            fftSize: options.fftSize || 2048,
            smoothingTimeConstant: options.smoothingTimeConstant || 0.8,
            minDecibels: options.minDecibels || -90,
            maxDecibels: options.maxDecibels || -10,
            scrollSpeed: options.scrollSpeed || 2,  // 像素/帧
            colorScheme: options.colorScheme || 'hot',  // 'hot', 'viridis', 'cool'
            showWaveform: options.showWaveform || true,
            showFrequencyLabels: options.showFrequencyLabels || true,
            maxFrequency: options.maxFrequency || 8000
        };
        
        // 状态
        this.isRunning = false;
        this.isPaused = false;  // 暂停状态
        this.animationId = null;
        this.spectrogramData = [];  // 存储历史频谱数据
        this.maxFrames = Math.ceil(this.width / this.options.scrollSpeed);
        
        // Web Audio API
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.waveformArray = null;
        this.microphoneStream = null;  // 保存麦克风流，用于语音识别复用
        
        // VOT检测
        this.votMarkers = [];
        this.energyHistory = [];
        this.energyThreshold = -40;  // dB
        
        // 共振峰检测
        this.formants = [];  // 存储当前检测到的共振峰
        this.showFormants = true;  // 是否显示共振峰标注
        this.lockedFormants = null;  // 锁定的共振峰（用于观察）
        this.isFormantsLocked = false;  // 是否锁定共振峰
        this.isVoicing = false;  // 当前是否正在发声
        this.voicingFormants = null;  // 发声时的共振峰
        this.lastVoicingTime = 0;  // 上次发声时间
        this.formantHoldTime = 5000;  // 共振峰保持显示时间（毫秒）
        
        // 拼音识别
        this.showPinyin = false;  // 是否显示拼音标注
        this.pinyinMarkers = [];  // 存储拼音标记
        this.recognition = null;  // 语音识别对象
        this.recognitionActive = false;  // 语音识别是否活跃
        this.recognitionLanguage = 'zh-CN';
        this.pinyinDisplayDuration = 8000;  // 拼音显示时长（毫秒）
        this.startTime = null;  // 记录启动时间
        this.recognitionLatency = 2000;  // 识别时延（毫秒），用于逆推标记位置
        
        // 性能优化
        this.offscreenCanvas = document.createElement('canvas');
        this.offscreenCanvas.width = this.width;
        this.offscreenCanvas.height = this.height;
        this.offscreenCtx = this.offscreenCanvas.getContext('2d');
        
        this.init();
    }
    
    init() {
        console.log('初始化实时频谱渲染器...');
        this.drawPlaceholder();
    }
    
    async start() {
        if (this.isRunning) {
            console.warn('实时渲染已在运行');
            return;
        }
        
        try {
            // 请求麦克风权限
            this.microphoneStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: false
                }
            });
            
            // 创建音频上下文
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.microphone = this.audioContext.createMediaStreamSource(this.microphoneStream);
            
            // 创建分析器
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = this.options.fftSize;
            this.analyser.smoothingTimeConstant = this.options.smoothingTimeConstant;
            this.analyser.minDecibels = this.options.minDecibels;
            this.analyser.maxDecibels = this.options.maxDecibels;
            
            // 连接节点
            this.microphone.connect(this.analyser);
            
            // 准备数据数组
            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(bufferLength);
            this.waveformArray = new Uint8Array(bufferLength);
            
            // 清空历史数据
            this.spectrogramData = [];
            this.votMarkers = [];
            this.energyHistory = [];
            this.pinyinMarkers = [];
            
            // 记录启动时间
            this.startTime = Date.now();
            
            // 开始渲染
            this.isRunning = true;
            this.render();
            
            // 如果启用拼音识别，启动语音识别
            if (this.showPinyin) {
                this.startSpeechRecognition();
            }
            
            console.log('✓ 实时频谱渲染已启动');
            console.log(`  FFT大小: ${this.options.fftSize}`);
            console.log(`  频率分辨率: ${this.audioContext.sampleRate / this.options.fftSize} Hz`);
            
            return true;
        } catch (error) {
            console.error('启动实时渲染失败:', error);
            alert('无法访问麦克风: ' + error.message);
            return false;
        }
    }
    
    pause() {
        if (!this.isRunning || this.isPaused) {
            return;
        }
        
        this.isPaused = true;
        console.log('✓ 频谱图滚动已暂停');
    }
    
    resume() {
        if (!this.isRunning || !this.isPaused) {
            return;
        }
        
        this.isPaused = false;
        console.log('✓ 频谱图滚动已继续');
    }
    
    stop() {
        if (!this.isRunning) {
            return;
        }
        
        this.isRunning = false;
        this.isPaused = false;
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        // 停止语音识别
        this.stopSpeechRecognition();
        
        if (this.microphone) {
            this.microphone.disconnect();
            this.microphone = null;
        }
        
        // 停止麦克风流
        if (this.microphoneStream) {
            this.microphoneStream.getTracks().forEach(track => track.stop());
            this.microphoneStream = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        console.log('✓ 实时频谱渲染已停止');
    }
    
    render() {
        if (!this.isRunning) {
            return;
        }
        
        // 获取频谱数据
        this.analyser.getByteFrequencyData(this.dataArray);
        
        // 获取波形数据
        if (this.options.showWaveform) {
            this.analyser.getByteTimeDomainData(this.waveformArray);
        }
        
        // 计算能量（用于VOT检测）
        const energy = this.calculateEnergy(this.waveformArray);
        this.energyHistory.push(energy);
        if (this.energyHistory.length > 100) {
            this.energyHistory.shift();
        }
        
        // VOT检测
        this.detectVOT(energy);
        
        // 共振峰检测
        if (this.showFormants) {
            this.detectFormants(this.dataArray, energy);
        }
        
        // 只有在未暂停时才添加新帧和滚动
        if (!this.isPaused) {
            // 添加当前帧到历史
            this.spectrogramData.push(new Uint8Array(this.dataArray));
            if (this.spectrogramData.length > this.maxFrames) {
                this.spectrogramData.shift();
            }
        }
        
        // 绘制（暂停时也继续绘制，只是不滚动）
        this.draw();
        
        // 继续下一帧
        this.animationId = requestAnimationFrame(() => this.render());
    }
    
    draw() {
        // 使用离屏canvas提高性能
        const ctx = this.offscreenCtx;
        
        // 清空画布
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, this.width, this.height);
        
        // 计算布局
        let spectrogramHeight = this.height;
        let waveformHeight = 0;
        let pinyinHeight = 0;
        
        if (this.options.showWaveform && this.showPinyin) {
            // 三层布局：频谱 70%，波形 15%，拼音 15%
            spectrogramHeight = this.height * 0.70;
            waveformHeight = this.height * 0.15;
            pinyinHeight = this.height * 0.15;
        } else if (this.options.showWaveform) {
            // 两层布局：频谱 75%，波形 25%
            spectrogramHeight = this.height * 0.75;
            waveformHeight = this.height * 0.25;
        } else if (this.showPinyin) {
            // 两层布局：频谱 85%，拼音 15%
            spectrogramHeight = this.height * 0.85;
            pinyinHeight = this.height * 0.15;
        }
        
        // 绘制频谱图
        this.drawSpectrogram(ctx, spectrogramHeight);
        
        // 绘制波形
        if (this.options.showWaveform) {
            this.drawWaveform(ctx, spectrogramHeight, waveformHeight);
        }
        
        // 绘制拼音区域
        if (this.showPinyin) {
            const pinyinOffsetY = spectrogramHeight + waveformHeight;
            this.drawPinyinArea(ctx, pinyinOffsetY, pinyinHeight);
        }
        
        // 绘制频率标签
        if (this.options.showFrequencyLabels) {
            this.drawFrequencyLabels(ctx, spectrogramHeight);
        }
        
        // 绘制VOT标记
        this.drawVOTMarkers(ctx, spectrogramHeight);
        
        // 绘制共振峰标注
        if (this.showFormants) {
            this.drawFormants(ctx, spectrogramHeight);
        }
        
        // 绘制时间轴
        this.drawTimeAxis(ctx, spectrogramHeight);
        
        // 复制到主canvas
        this.ctx.drawImage(this.offscreenCanvas, 0, 0);
    }
    
    drawSpectrogram(ctx, height) {
        const numFrames = this.spectrogramData.length;
        if (numFrames === 0) return;
        
        const frameWidth = this.width / this.maxFrames;
        const numBins = this.dataArray.length;
        
        // 计算显示的频率范围
        const nyquist = this.audioContext.sampleRate / 2;
        const maxBinIndex = Math.floor(this.options.maxFrequency / nyquist * numBins);
        const binHeight = height / maxBinIndex;
        
        for (let frameIdx = 0; frameIdx < numFrames; frameIdx++) {
            const frame = this.spectrogramData[frameIdx];
            const x = frameIdx * frameWidth;
            
            for (let binIdx = 0; binIdx < maxBinIndex; binIdx++) {
                const value = frame[binIdx] / 255;  // 归一化到 0-1
                
                // 应用颜色映射
                const color = this.getColor(value);
                ctx.fillStyle = color;
                
                // Y轴翻转（低频在下）
                const y = height - (binIdx + 1) * binHeight;
                ctx.fillRect(x, y, frameWidth + 1, binHeight + 1);
            }
        }
    }
    
    drawWaveform(ctx, offsetY, height) {
        if (!this.waveformArray) return;
        
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        const sliceWidth = this.width / this.waveformArray.length;
        let x = 0;
        
        for (let i = 0; i < this.waveformArray.length; i++) {
            const v = this.waveformArray[i] / 128.0;  // 归一化到 0-2
            const y = offsetY + (v * height / 2);
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            
            x += sliceWidth;
        }
        
        ctx.stroke();
        
        // 绘制中心线
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, offsetY + height / 2);
        ctx.lineTo(this.width, offsetY + height / 2);
        ctx.stroke();
    }
    
    drawFrequencyLabels(ctx, height) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        
        const frequencies = [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000];
        
        for (const freq of frequencies) {
            if (freq > this.options.maxFrequency) break;
            
            const y = height * (1 - freq / this.options.maxFrequency);
            
            // 绘制网格线
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.width, y);
            ctx.stroke();
            
            // 绘制标签
            ctx.fillText(`${freq}Hz`, 5, y - 2);
        }
    }
    
    drawTimeAxis(ctx, height) {
        const duration = this.spectrogramData.length / 60;  // 假设60fps
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        
        for (let i = 0; i <= 5; i++) {
            const x = (i / 5) * this.width;
            const time = (i / 5) * duration;
            
            ctx.fillText(`${time.toFixed(1)}s`, x, height + 15);
        }
    }
    
    drawVOTMarkers(ctx, height) {
        // 绘制最近的VOT标记
        const now = Date.now();
        
        this.votMarkers = this.votMarkers.filter(marker => {
            return now - marker.timestamp < 5000;  // 保留5秒
        });
        
        for (const marker of this.votMarkers) {
            const age = now - marker.timestamp;
            const alpha = Math.max(0, 1 - age / 5000);
            
            ctx.strokeStyle = `rgba(255, 0, 0, ${alpha})`;
            ctx.lineWidth = 3;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(marker.x, 0);
            ctx.lineTo(marker.x, height);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // 标签
            ctx.fillStyle = `rgba(255, 0, 0, ${alpha})`;
            ctx.font = 'bold 14px Arial';
            ctx.fillText(`VOT: ${marker.vot.toFixed(0)}ms`, marker.x + 5, 20);
        }
    }
    
    calculateEnergy(waveformData) {
        let sum = 0;
        for (let i = 0; i < waveformData.length; i++) {
            const normalized = (waveformData[i] - 128) / 128;
            sum += normalized * normalized;
        }
        const rms = Math.sqrt(sum / waveformData.length);
        const db = 20 * Math.log10(rms + 1e-10);
        return db;
    }
    
    detectVOT(currentEnergy) {
        if (this.energyHistory.length < 10) return;
        
        const recentEnergy = this.energyHistory.slice(-10);
        const avgEnergy = recentEnergy.reduce((a, b) => a + b, 0) / recentEnergy.length;
        
        // 检测能量突增（爆破音）
        if (currentEnergy > this.energyThreshold && 
            avgEnergy < this.energyThreshold - 10) {
            
            // 估算VOT（简化版）
            const burstFrame = this.energyHistory.length - 10;
            const voiceFrame = this.energyHistory.length;
            const vot = (voiceFrame - burstFrame) * (1000 / 60);  // 假设60fps
            
            // 添加标记
            this.votMarkers.push({
                x: this.width - 50,  // 当前位置
                vot: vot,
                timestamp: Date.now()
            });
            
            console.log(`检测到VOT: ${vot.toFixed(1)}ms`);
        }
    }
    
    /**
     * 检测共振峰频率
     * 共振峰是频谱中的能量峰值，代表声道的共振特性
     */
    detectFormants(spectrumData, currentEnergy) {
        if (!spectrumData || spectrumData.length === 0) return;
        
        const nyquist = this.audioContext.sampleRate / 2;
        const binWidth = nyquist / spectrumData.length;
        
        // 寻找频谱峰值
        const peaks = this.findPeaks(spectrumData, binWidth);
        
        // 过滤并选择前4个共振峰（F1-F4）
        // 典型人声共振峰范围：
        // F1: 200-1200 Hz（元音高低）
        // F2: 600-3000 Hz（元音前后）
        // F3: 1400-4000 Hz（音色）
        // F4: 2000-5000 Hz（音色细节）
        const formantRanges = [
            { name: 'F1', min: 200, max: 1200, color: '#ff3333' },
            { name: 'F2', min: 600, max: 3000, color: '#33ff33' },
            { name: 'F3', min: 1400, max: 4000, color: '#3333ff' },
            { name: 'F4', min: 2000, max: 5000, color: '#ffff33' }
        ];
        
        this.formants = [];
        
        for (const range of formantRanges) {
            // 在指定范围内找到最强峰值
            const peaksInRange = peaks.filter(peak => 
                peak.frequency >= range.min && peak.frequency <= range.max
            );
            
            if (peaksInRange.length > 0) {
                // 选择最强的峰值
                peaksInRange.sort((a, b) => b.magnitude - a.magnitude);
                const formant = peaksInRange[0];
                
                this.formants.push({
                    name: range.name,
                    frequency: formant.frequency,
                    magnitude: formant.magnitude,
                    color: range.color
                });
            }
        }
        
        // 检测当前是否正在发声（基于能量阈值）
        const wasVoicing = this.isVoicing;
        this.isVoicing = currentEnergy > this.energyThreshold && this.formants.length >= 2;
        
        // 如果正在发声且有共振峰，更新发声时的共振峰
        if (this.isVoicing && this.formants.length > 0) {
            this.voicingFormants = JSON.parse(JSON.stringify(this.formants));
            this.lastVoicingTime = Date.now();
            
            // 发声开始时的提示
            if (!wasVoicing) {
                console.log('🎤 检测到发声，共振峰已捕获');
            }
        }
    }
    
    /**
     * 在频谱数据中找峰值
     */
    findPeaks(data, binWidth) {
        const peaks = [];
        const minPeakHeight = 80;  // 最小峰值高度（0-255范围）
        const minPeakDistance = 3;  // 最小峰值间距（bin数）
        
        for (let i = minPeakDistance; i < data.length - minPeakDistance; i++) {
            const current = data[i];
            
            // 跳过低能量点
            if (current < minPeakHeight) continue;
            
            // 检查是否是局部最大值
            let isPeak = true;
            for (let j = 1; j <= minPeakDistance; j++) {
                if (data[i - j] >= current || data[i + j] >= current) {
                    isPeak = false;
                    break;
                }
            }
            
            if (isPeak) {
                const frequency = i * binWidth;
                peaks.push({
                    frequency: frequency,
                    magnitude: current,
                    binIndex: i
                });
            }
        }
        
        return peaks;
    }
    
    /**
     * 绘制共振峰标注
     */
    drawFormants(ctx, height) {
        // 决定显示哪个共振峰：锁定的 > 发声时的 > 当前实时的
        let displayFormants = null;
        let statusText = '';
        
        if (this.isFormantsLocked && this.lockedFormants) {
            displayFormants = this.lockedFormants;
            statusText = '🔒 已锁定';
        } else if (this.voicingFormants && (Date.now() - this.lastVoicingTime < this.formantHoldTime)) {
            displayFormants = this.voicingFormants;
            const elapsed = Date.now() - this.lastVoicingTime;
            const remaining = Math.ceil((this.formantHoldTime - elapsed) / 1000);
            statusText = this.isVoicing ? '🎤 发声中' : `⏱️ 保持 ${remaining}s`;
        } else {
            displayFormants = this.formants;
            statusText = '🔄 实时';
        }
        
        if (!displayFormants || displayFormants.length === 0) return;
        
        const maxDisplayFreq = this.options.maxFrequency;
        
        // 在频谱图右侧绘制共振峰标注
        const rightX = this.width - 150;
        
        for (let i = 0; i < displayFormants.length; i++) {
            const formant = displayFormants[i];
            
            // 计算频率对应的Y坐标
            const y = height * (1 - formant.frequency / maxDisplayFreq);
            
            if (y < 0 || y > height) continue;  // 超出显示范围
            
            // 绘制横线标记
            ctx.strokeStyle = formant.color;
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 3]);
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(this.width, y);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // 绘制圆点标记
            ctx.fillStyle = formant.color;
            ctx.beginPath();
            ctx.arc(rightX, y, 5, 0, Math.PI * 2);
            ctx.fill();
            
            // 绘制标签背景
            const label = `${formant.name}: ${Math.round(formant.frequency)}Hz`;
            ctx.font = 'bold 12px Arial';
            const textWidth = ctx.measureText(label).width;
            
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(rightX + 10, y - 10, textWidth + 10, 20);
            
            // 绘制标签文字
            ctx.fillStyle = formant.color;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(label, rightX + 15, y);
        }
        
        // 在左上角显示共振峰信息汇总
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.fillRect(5, 5, 180, 45 + displayFormants.length * 18);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'left';
        ctx.fillText('共振峰检测', 10, 20);
        
        // 显示状态
        ctx.font = '11px Arial';
        ctx.fillStyle = '#ffff00';
        ctx.fillText(statusText, 10, 35);
        
        ctx.font = '11px Arial';
        for (let i = 0; i < displayFormants.length; i++) {
            const formant = displayFormants[i];
            ctx.fillStyle = formant.color;
            ctx.fillText(
                `${formant.name}: ${Math.round(formant.frequency)} Hz`, 
                10, 
                55 + i * 18
            );
        }
    }
    
    getColor(value) {
        // 颜色映射
        switch (this.options.colorScheme) {
            case 'hot':
                return this.hotColormap(value);
            case 'viridis':
                return this.viridisColormap(value);
            case 'cool':
                return this.coolColormap(value);
            default:
                return this.hotColormap(value);
        }
    }
    
    hotColormap(value) {
        // 黑 -> 红 -> 黄 -> 白
        const r = Math.min(255, value * 3 * 255);
        const g = Math.min(255, Math.max(0, (value - 0.33) * 3 * 255));
        const b = Math.min(255, Math.max(0, (value - 0.66) * 3 * 255));
        return `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
    }
    
    viridisColormap(value) {
        // 简化的Viridis配色
        const colors = [
            [68, 1, 84],      // 紫
            [59, 82, 139],    // 蓝
            [33, 145, 140],   // 青
            [94, 201, 98],    // 绿
            [253, 231, 37]    // 黄
        ];
        
        const idx = value * (colors.length - 1);
        const i1 = Math.floor(idx);
        const i2 = Math.min(i1 + 1, colors.length - 1);
        const t = idx - i1;
        
        const r = colors[i1][0] + (colors[i2][0] - colors[i1][0]) * t;
        const g = colors[i1][1] + (colors[i2][1] - colors[i1][1]) * t;
        const b = colors[i1][2] + (colors[i2][2] - colors[i1][2]) * t;
        
        return `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
    }
    
    coolColormap(value) {
        // 蓝 -> 青 -> 白
        const r = value * 255;
        const g = value * 255;
        const b = 255;
        return `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
    }
    
    drawPlaceholder() {
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        this.ctx.fillStyle = '#666';
        this.ctx.font = '20px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('点击"开始实时监测"查看频谱', this.width / 2, this.height / 2);
    }
    
    /**
     * 启动语音识别
     * 优先使用后端API（百度/阿里云），fallback到浏览器 Web Speech API
     */
    async startSpeechRecognition() {
        // 检查是否已启动实时监测（必须先启动才能使用拼音功能）
        if (!this.isRunning || !this.microphoneStream) {
            console.warn('⚠️ 请先启动实时监测，拼音功能需要复用麦克风输入');
            alert('请先点击"启动实时监测"按钮，然后再启用拼音标注');
            return;
        }
        console.log('✓ 检测到实时监测已运行，复用麦克风输入');
        
        // 检查 cnchar 库
        if (typeof cnchar === 'undefined' || typeof cnchar.spell !== 'function') {
            console.error('❌ cnchar 库未加载，拼音功能无法使用');
            alert('拼音功能需要加载 cnchar 库，请检查网络连接后刷新页面');
            return;
        }
        console.log('✓ cnchar 库已加载');
        
        // 语音识别方案选择：
        // - 'web_speech': 浏览器 Web Speech API（Google 在线服务）
        // - 'backend': 后端 API（百度/阿里云）⭐ 推荐 - 快速准确
        const recognitionMethod = 'backend';  // 选择识别方法 - 使用百度语音识别
        
        if (recognitionMethod === 'backend') {
            console.log('🔄 使用后端语音识别API（百度/阿里云）');
            this.startBackendSpeechRecognition(recognitionMethod);
            return;
        }
        
        // 使用浏览器 Web Speech API + 本地 cnchar 拼音转换
        console.log('🔄 使用本地方案：Web Speech API + cnchar 拼音库（低延迟）');
        
        // 检查浏览器支持
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error('❌ 浏览器不支持 Web Speech API');
            alert('拼音功能需要使用 Chrome 或 Edge 浏览器');
            return;
        }
        console.log('✓ Web Speech API 已支持');
        
        try {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = this.recognitionLanguage;
            
            this.recognition.onresult = (event) => {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i];
                    const transcript = result[0].transcript;
                    
                    // 调试信息
                    if (!result.isFinal) {
                        console.log('⚡ 识别中（实时）:', transcript);
                    }
                    
                    // 处理临时结果（低延迟）或最终结果
                    if (result.isFinal) {
                        console.log('✓ 识别完成（最终）:', transcript);
                        this.processPinyinFromText(transcript, true);
                    } else {
                        // 实时显示临时结果（可选，降低延迟）
                        // 如果希望更快反馈，可以启用临时结果
                        // this.processPinyinFromText(transcript, false);
                    }
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('❌ 语音识别错误:', event.error);
                
                // 详细的错误说明
                if (event.error === 'network') {
                    console.error('详细说明: "network" 错误的真正原因（不是网络问题！）:');
                    console.error('1. 🌐 Web Speech API 使用 Google 在线服务');
                    console.error('2. 🔒 需要 HTTPS 连接（localhost 除外）');
                    console.error('3. 🚫 某些地区可能无法访问 Google 服务');
                    console.error('');
                    console.error('✅ 解决方法:');
                    console.error('- 确保使用 http://localhost:5001 访问（不要用 IP 地址）');
                    console.error('- 检查是否可以访问 Google 服务');
                    console.error('- 或考虑使用离线语音识别方案');
                    this.recognitionActive = false;
                } else if (event.error === 'not-allowed') {
                    console.error('详细说明: 麦克风权限被拒绝');
                    console.error('请在浏览器地址栏左侧点击 🔒 图标，允许使用麦克风');
                    this.recognitionActive = false;
                } else if (event.error === 'no-speech') {
                    console.warn('⚠️ 没有检测到语音，继续监听...');
                } else {
                    console.error('详细说明:', event.error);
                }
            };
            
            this.recognition.onend = () => {
                console.log('语音识别结束');
                // 如果还在运行，自动重启（但避免太快重启）
                if (this.isRunning && this.showPinyin && this.recognitionActive) {
                    setTimeout(() => {
                        if (this.isRunning && this.showPinyin) {
                            try {
                                this.recognition.start();
                                console.log('重启语音识别');
                            } catch (e) {
                                console.warn('重启识别失败:', e);
                                this.recognitionActive = false;
                            }
                        }
                    }, 100);  // 延迟 100ms 再重启
                }
            };
            
            this.recognitionActive = true;
            this.recognition.start();
            console.log('✓ 语音识别已启动，语言:', this.recognitionLanguage);
        } catch (error) {
            console.error('启动语音识别失败:', error);
        }
    }
    
    /**
     * 处理识别文字，转换为拼音并显示（字级别）
     * @param {string} text - 识别出的文字
     * @param {boolean} isFinal - 是否为最终结果
     */
    processPinyinFromText(text, isFinal) {
        if (!text || text.trim().length === 0) {
            return;
        }
        
        try {
            // 提取中文字符（忽略标点、数字等）
            const chineseChars = text.match(/[\u4e00-\u9fa5]/g);
            if (!chineseChars || chineseChars.length === 0) {
                console.log('⚠️ 未检测到中文字符:', text);
                return;
            }
            
            console.log(`📝 检测到 ${chineseChars.length} 个汉字，开始逐字转换拼音...`);
            
            // 逐字处理，生成拼音标注
            for (const char of chineseChars) {
                // 使用 cnchar 获取拼音（带声调）
                // 参数说明：
                // - 'tone': 返回带声调的拼音（如 "zhōng"）
                // - 'poly': 如果是多音字，返回所有读音的数组
                const pinyin = cnchar.spell(char, 'tone', 'poly');
                
                // 如果是多音字，取第一个常用读音
                let pinyinText;
                if (Array.isArray(pinyin)) {
                    pinyinText = pinyin[0];  // 第一个通常是最常用的读音
                } else {
                    pinyinText = pinyin;
                }
                
                // 格式化显示：汉字(拼音)
                const displayText = `${char}(${pinyinText})`;
                
                console.log(`  ${displayText} ${isFinal ? '✓' : '⚡'}`);
                
                // 添加拼音标注到频谱图
                this.addPinyinMarker(displayText);
            }
            
            console.log(`✓ 拼音标注完成 (${isFinal ? '最终' : '临时'})`);
            
        } catch (error) {
            console.error('❌ 拼音转换失败:', error);
        }
    }
    
    /**
     * 使用后端API进行语音识别（百度/阿里云）
     * @param {string} method - 识别方法：'backend'
     */
    async startBackendSpeechRecognition(method = 'backend') {
        console.log('🎤 启动 PCM 流式语音识别...');
        
        // 检查可用的服务商
        try {
            const providersResp = await fetch('/api/speech/providers');
            const providersData = await providersResp.json();
            
            if (!providersData.success) {
                console.error('❌ 获取语音识别服务商失败:', providersData.error);
                alert('后端语音识别服务不可用');
                return;
            }
            
            // 找到可用的云端服务商（百度/阿里云）
            const availableProvider = providersData.providers.find(p => p.available);
            
            if (!availableProvider) {
                console.error('❌ 没有可用的语音识别服务商');
                console.error('请配置百度或阿里云密钥，参考: config/speech_config.py');
                alert('请先配置语音识别服务（百度或阿里云）\n详见 env.example 文件');
                return;
            }
            
            console.log('✓ 使用语音识别服务:', availableProvider.name);
            this.recognitionProvider = availableProvider.id;
            
            // ========== 使用 AudioWorklet 捕获 PCM 数据 ==========
            
            // 创建 AudioContext（16kHz 采样率，语音识别标准）
            this.recognitionAudioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 48000  // 保持默认采样率，由 worklet 降采样
            });
            
            // 加载 PCM 捕获处理器
            try {
                await this.recognitionAudioContext.audioWorklet.addModule('/static/js/pcm-capture-processor.js');
                console.log('✓ PCM 捕获处理器加载成功');
            } catch (error) {
                console.error('❌ 加载 PCM 处理器失败:', error);
                alert('加载音频处理器失败，请刷新页面重试');
                return;
            }
            
            // 创建音频源
            const source = this.recognitionAudioContext.createMediaStreamSource(this.microphoneStream);
            
            // 创建 PCM 捕获节点
            this.pcmCaptureNode = new AudioWorkletNode(
                this.recognitionAudioContext, 
                'pcm-capture-processor'
            );
            
            // PCM 数据缓冲区（累积时间以提高识别率）
            this.pcmBuffer = [];
            this.pcmBufferDuration = 0;
            this.pcmBufferStartTime = null;  // 记录音频开始时间
            const TARGET_DURATION = 1.5;  // 累积 1.5 秒后识别
            const SILENCE_THRESHOLD = 200;  // 静音阈值
            
            // 监听 PCM 数据
            this.pcmCaptureNode.port.onmessage = async (event) => {
                const { type, data, sampleRate, samples, duration } = event.data;
                
                if (type === 'pcm_data') {
                    // 检测是否为静音（简单的能量检测）
                    const pcmArray = new Int16Array(data);
                    let energy = 0;
                    for (let i = 0; i < pcmArray.length; i++) {
                        energy += Math.abs(pcmArray[i]);
                    }
                    const avgEnergy = energy / pcmArray.length;
                    
                    // 如果缓冲区为空，使用更严格的阈值（避免背景噪音触发）
                    const effectiveThreshold = this.pcmBuffer.length === 0 ? SILENCE_THRESHOLD * 1.5 : SILENCE_THRESHOLD;
                    const isSilence = avgEnergy < effectiveThreshold;
                    
                    if (isSilence) {
                        console.log(`🔇 检测到静音，跳过 (能量: ${avgEnergy.toFixed(0)}, 阈值: ${effectiveThreshold.toFixed(0)})`);
                        return;
                    }
                    
                    console.log(`📦 接收到 PCM 数据: ${samples} samples (${duration.toFixed(2)}s, 能量: ${avgEnergy.toFixed(0)})`);
                    
                    // 记录音频开始时间（第一次收到数据时）
                    if (this.pcmBuffer.length === 0) {
                        this.pcmBufferStartTime = Date.now();
                    }
                    
                    // 累积数据
                    this.pcmBuffer.push(data);
                    this.pcmBufferDuration += duration;
                    
                    // 达到目标时长，发送识别
                    if (this.pcmBufferDuration >= TARGET_DURATION) {
                        // 合并所有 buffer
                        const totalLength = this.pcmBuffer.reduce((sum, arr) => sum + arr.byteLength / 2, 0);
                        const mergedData = new Int16Array(totalLength);
                        let offset = 0;
                        for (const arr of this.pcmBuffer) {
                            const int16Array = new Int16Array(arr);
                            mergedData.set(int16Array, offset);
                            offset += int16Array.length;
                        }
                        
                        console.log(`📤 累积 ${this.pcmBufferDuration.toFixed(2)}s 数据 (${mergedData.length} samples)，开始识别...`);
                        
                        // 记录音频的中点时间（作为发音时间）
                        const audioMidTime = this.pcmBufferStartTime + (this.pcmBufferDuration * 1000 / 2);
                        
                        // 发送 PCM 数据进行识别
                        await this.sendPCMForRecognition(mergedData.buffer, sampleRate, this.recognitionProvider, audioMidTime);
                        
                        // 清空缓冲区
                        this.pcmBuffer = [];
                        this.pcmBufferDuration = 0;
                        this.pcmBufferStartTime = null;
                    }
                }
            };
            
            // 连接音频节点
            source.connect(this.pcmCaptureNode);
            // 注意：不需要连接到 destination，避免回声
            
            this.recognitionActive = true;
            console.log('✓ PCM 流式语音识别已启动');
            
        } catch (error) {
            console.error('❌ 启动 PCM 语音识别失败:', error);
            alert('启动语音识别失败: ' + error.message);
        }
    }
    
    /**
     * 发送音频到后端进行识别（旧方法，保留兼容性）
     */
    async sendAudioForRecognition(audioChunks, provider) {
        try {
            // 创建音频 Blob
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            
            const formData = new FormData();
            formData.append('audio', audioBlob, 'audio.webm');
            formData.append('provider', provider);
            
            console.log('📤 发送音频数据到后端识别...');
            
            // 使用百度/阿里云 API 端点
            const apiEndpoint = '/api/speech/recognize';
            
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success && result.text) {
                console.log('✓ 识别结果:', result.text);
                this.addPinyinMarker(result.text);
            } else {
                console.warn('⚠️ 识别无结果:', result.error || '未识别到内容');
            }
            
        } catch (error) {
            console.error('❌ 发送识别请求失败:', error);
        }
    }
    
    /**
     * 发送 PCM 数据到后端进行识别（新方法）
     * @param {ArrayBuffer} pcmData - Int16 PCM 数据
     * @param {number} sampleRate - 采样率
     * @param {string} provider - 服务商 ID
     * @param {number} audioMidTime - 音频中点时间（毫秒时间戳）
     */
    async sendPCMForRecognition(pcmData, sampleRate, provider, audioMidTime) {
        try {
            // 创建 Blob
            const pcmBlob = new Blob([pcmData], { type: 'application/octet-stream' });
            
            const formData = new FormData();
            formData.append('audio', pcmBlob, 'audio.pcm');
            formData.append('provider', provider);
            formData.append('format', 'pcm');  // 标记为 PCM 格式
            formData.append('sample_rate', sampleRate.toString());
            formData.append('channels', '1');  // 单声道
            formData.append('sample_width', '2');  // 16-bit = 2 bytes
            
            console.log(`📤 发送 PCM 数据: ${pcmBlob.size} bytes, ${sampleRate} Hz`);
            
            // 记录发送时间（用于计算时延）
            const sendTime = Date.now();
            
            // 使用百度/阿里云 API 端点
            const apiEndpoint = '/api/speech/recognize';
            
            console.log(`🎯 使用 API: ${apiEndpoint}`);
            
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success && result.text) {
                // 计算实际时延（从音频中点到识别完成）
                const receiveTime = Date.now();
                const actualLatency = receiveTime - audioMidTime;
                
                console.log('✓ 识别结果:', result.text);
                console.log(`⏱️ 识别时延: ${actualLatency}ms (发送到接收: ${receiveTime - sendTime}ms)`);
                
                // 传递实际时延
                this.addPinyinMarker(result.text, actualLatency);
            } else {
                console.warn('⚠️ 识别无结果:', result.error || '未识别到内容');
            }
            
        } catch (error) {
            console.error('❌ 发送 PCM 识别请求失败:', error);
        }
    }
    
    /**
     * 停止语音识别
     */
    stopSpeechRecognition() {
        // 停止 PCM 捕获节点
        if (this.pcmCaptureNode) {
            try {
                this.pcmCaptureNode.port.close();
                this.pcmCaptureNode.disconnect();
                this.pcmCaptureNode = null;
                console.log('✓ PCM 捕获节点已停止');
            } catch (error) {
                console.error('停止 PCM 捕获失败:', error);
            }
        }
        
        // 关闭识别用的 AudioContext
        if (this.recognitionAudioContext) {
            try {
                this.recognitionAudioContext.close();
                this.recognitionAudioContext = null;
                console.log('✓ 识别 AudioContext 已关闭');
            } catch (error) {
                console.error('关闭 AudioContext 失败:', error);
            }
        }
        
        // 停止后端识别（旧方法兼容）
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            try {
                this.mediaRecorder.stop();
                this.mediaRecorder = null;
                console.log('✓ 后端语音识别已停止');
            } catch (error) {
                console.error('停止后端识别失败:', error);
            }
        }
        
        // 停止音量检查（旧方法兼容）
        if (this.audioLevelChecker) {
            clearInterval(this.audioLevelChecker);
            this.audioLevelChecker = null;
        }
        
        // 停止浏览器识别
        if (this.recognition) {
            try {
                this.recognition.stop();
                this.recognition = null;
                console.log('✓ 浏览器语音识别已停止');
            } catch (error) {
                console.error('停止浏览器识别失败:', error);
            }
        }
        
        this.recognitionActive = false;
    }
    
    /**
     * 添加拼音标记
     */
    addPinyinMarker(text, latency = null) {
        if (!text || text.trim().length === 0) {
            console.warn('⚠️ 拼音标注: 文本为空，跳过');
            return;
        }
        
        // 检查 cnchar 是否可用
        if (typeof cnchar === 'undefined' || typeof cnchar.spell !== 'function') {
            console.error('❌ cnchar 库未加载，无法转换拼音');
            console.error('   请检查网络连接，确保 cnchar 库正确加载');
            return;
        }
        
        try {
            // 使用 cnchar 转换拼音
            const pinyinText = cnchar.spell(text, 'tone');
            
            // 计算当前能量
            const energy = this.getCurrentEnergy();
            
            // 计算实际发音时间（逆推识别时延）
            const actualLatency = latency !== null ? latency : this.recognitionLatency;
            const actualSpeechTime = Date.now() - actualLatency;
            
            // 计算标记在频谱图上的位置（相对于频谱图的时间轴）
            // 保存发音时刻相对于录音开始的时间，这样标记就会随频谱图一起滚动
            const speechElapsedSinceStart = actualSpeechTime - this.startTime;
            
            // 创建标记
            const marker = {
                text: text,
                pinyin: pinyinText,
                timestamp: actualSpeechTime,  // 实际发音时间
                createdAt: Date.now(),  // 标记创建时间
                speechTime: speechElapsedSinceStart,  // 发音时刻（相对于录音开始）
                energy: energy,
                latency: actualLatency
            };
            
            this.pinyinMarkers.push(marker);
            
            console.log(`✅ ${text} → ${pinyinText} (时延: ${actualLatency}ms, 发音时刻: ${speechElapsedSinceStart.toFixed(0)}ms)`);
        } catch (error) {
            console.error('❌ 转换拼音失败:', error);
        }
    }
    
    /**
     * 获取当前能量
     */
    getCurrentEnergy() {
        if (this.energyHistory.length === 0) return -60;
        return this.energyHistory[this.energyHistory.length - 1];
    }
    
    /**
     * 绘制拼音区域
     */
    drawPinyinArea(ctx, offsetY, height) {
        if (!this.showPinyin) {
            return;
        }
        
        // 绘制背景
        ctx.fillStyle = 'rgba(20, 20, 40, 0.8)';
        ctx.fillRect(0, offsetY, this.width, height);
        
        // 绘制分隔线
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, offsetY);
        ctx.lineTo(this.width, offsetY);
        ctx.stroke();
        
        // 绘制中线（分隔拼音和汉字）
        const midY = offsetY + height / 2;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(0, midY);
        ctx.lineTo(this.width, midY);
        ctx.stroke();
        ctx.setLineDash([]);
        
        // 清理过期的标记
        const now = Date.now();
        this.pinyinMarkers = this.pinyinMarkers.filter(marker => {
            return now - marker.createdAt < this.pinyinDisplayDuration;
        });
        
        // 绘制拼音标记
        if (this.pinyinMarkers.length === 0) {
            // 显示提示文字
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('开始说话，拼音和汉字会在这里显示...', this.width / 2, offsetY + height / 2);
            return;
        }
        
        // 计算时间比例（用于将标记固定在频谱图的时间轴位置）
        const currentTime = Date.now();
        const elapsedSinceStart = currentTime - this.startTime;
        const msPerPixel = (1000 / 60) / this.options.scrollSpeed;  // 每像素对应的毫秒数
        
        for (const marker of this.pinyinMarkers) {
            // 计算标记在频谱图上的位置
            // 标记固定在发音时刻的频谱柱上，随频谱图一起向左滚动
            const currentPixelOffset = elapsedSinceStart / msPerPixel;
            const markerPixelOffset = marker.speechTime / msPerPixel;
            const x = this.width - (currentPixelOffset - markerPixelOffset);
            
            // 调试日志（仅首次绘制时输出）
            if (!marker._logged) {
                console.log(`📍 "${marker.text}" 位置: x=${x.toFixed(0)}, 发音时刻=${marker.speechTime.toFixed(0)}ms, 当前时刻=${elapsedSinceStart.toFixed(0)}ms`);
                marker._logged = true;
            }
            
            // 如果已经滚出屏幕，跳过
            if (x < -100 || x > this.width + 100) continue;
            
            // 计算透明度（渐隐效果）
            const age = now - marker.createdAt;
            const alpha = Math.max(0, 1 - age / this.pinyinDisplayDuration);
            
            // 绘制连接线（从频谱图到拼音区域）
            const spectrogramHeight = this.options.showWaveform ? this.height * 0.70 : this.height * 0.85;
            ctx.strokeStyle = `rgba(100, 200, 255, ${alpha * 0.3})`;
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 2]);
            ctx.beginPath();
            ctx.moveTo(x, spectrogramHeight);
            ctx.lineTo(x, offsetY);
            ctx.stroke();
            ctx.setLineDash([]);
            
            // 绘制拼音（上半部分）
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            ctx.fillStyle = `rgba(100, 200, 255, ${alpha})`;
            const pinyinY = offsetY + height * 0.3;
            ctx.fillText(marker.pinyin, x, pinyinY);
            
            // 绘制汉字（下半部分）
            ctx.font = 'bold 20px "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif';
            ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
            const textY = offsetY + height * 0.7;
            ctx.fillText(marker.text, x, textY);
            
            // 绘制时延标记（调试用，可选）
            if (marker.latency) {
                ctx.font = '9px Arial';
                ctx.fillStyle = `rgba(150, 150, 150, ${alpha * 0.6})`;
                ctx.fillText(`${marker.latency}ms`, x, offsetY + height - 5);
            }
        }
    }
    
    // 公共方法：更新配置
    updateOptions(newOptions) {
        Object.assign(this.options, newOptions);
        
        // 处理共振峰显示选项
        if ('showFormants' in newOptions) {
            this.showFormants = newOptions.showFormants;
        }
        
        console.log('配置已更新:', this.options);
    }
    
    // 公共方法：切换共振峰显示
    toggleFormants(show) {
        this.showFormants = show !== undefined ? show : !this.showFormants;
        console.log('共振峰显示:', this.showFormants ? '开启' : '关闭');
        return this.showFormants;
    }
    
    // 公共方法：锁定/解锁共振峰
    toggleLockFormants() {
        this.isFormantsLocked = !this.isFormantsLocked;
        
        if (this.isFormantsLocked) {
            // 锁定当前显示的共振峰
            if (this.voicingFormants && (Date.now() - this.lastVoicingTime < this.formantHoldTime)) {
                this.lockedFormants = JSON.parse(JSON.stringify(this.voicingFormants));
            } else {
                this.lockedFormants = JSON.parse(JSON.stringify(this.formants));
            }
            console.log('🔒 共振峰已锁定:', this.lockedFormants);
        } else {
            console.log('🔓 共振峰已解锁');
        }
        
        return this.isFormantsLocked;
    }
    
    // 公共方法：切换拼音显示
    togglePinyin(show) {
        const previousState = this.showPinyin;
        this.showPinyin = show !== undefined ? show : !this.showPinyin;
        
        // 如果从关闭到开启，且正在运行，则启动识别
        if (!previousState && this.showPinyin && this.isRunning) {
            this.startSpeechRecognition();
        }
        
        // 如果从开启到关闭，则停止识别
        if (previousState && !this.showPinyin) {
            this.stopSpeechRecognition();
        }
        
        console.log('拼音显示:', this.showPinyin ? '开启' : '关闭');
        return this.showPinyin;
    }
    
    // 公共方法：清除拼音标记
    clearPinyinMarkers() {
        this.pinyinMarkers = [];
        console.log('✓ 拼音标记已清除');
    }
    
    // 公共方法：截图
    captureFrame() {
        return this.canvas.toDataURL('image/png');
    }
    
    // 公共方法：获取当前频谱数据
    getCurrentSpectrum() {
        if (this.spectrogramData.length === 0) return null;
        return Array.from(this.spectrogramData[this.spectrogramData.length - 1]);
    }
}


/**
 * 音频流处理器
 * 用于实时音频分析和特征提取
 */
class AudioStreamProcessor {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.scriptProcessor = null;
        
        this.callbacks = {
            onData: null,
            onVOT: null,
            onFeature: null
        };
        
        this.isProcessing = false;
        this.buffer = [];
        this.bufferSize = 4096;
    }
    
    async start(callbacks = {}) {
        if (this.isProcessing) {
            console.warn('音频处理已在运行');
            return;
        }
        
        this.callbacks = { ...this.callbacks, ...callbacks };
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            
            // 创建ScriptProcessor用于实时处理
            this.scriptProcessor = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
            
            this.scriptProcessor.onaudioprocess = (event) => {
                const inputData = event.inputBuffer.getChannelData(0);
                this.processAudioData(inputData);
            };
            
            this.microphone.connect(this.scriptProcessor);
            this.scriptProcessor.connect(this.audioContext.destination);
            
            this.isProcessing = true;
            console.log('✓ 音频流处理器已启动');
            
            return true;
        } catch (error) {
            console.error('启动音频处理器失败:', error);
            return false;
        }
    }
    
    stop() {
        if (!this.isProcessing) return;
        
        if (this.scriptProcessor) {
            this.scriptProcessor.disconnect();
            this.scriptProcessor = null;
        }
        
        if (this.microphone) {
            this.microphone.disconnect();
            this.microphone = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        this.isProcessing = false;
        console.log('✓ 音频流处理器已停止');
    }
    
    processAudioData(data) {
        // 添加到缓冲区
        this.buffer.push(...data);
        
        // 保持缓冲区大小
        if (this.buffer.length > this.bufferSize * 10) {
            this.buffer = this.buffer.slice(-this.bufferSize * 10);
        }
        
        // 回调
        if (this.callbacks.onData) {
            this.callbacks.onData(data);
        }
        
        // 特征提取
        const features = this.extractFeatures(data);
        if (this.callbacks.onFeature) {
            this.callbacks.onFeature(features);
        }
    }
    
    extractFeatures(data) {
        // 计算能量
        let energy = 0;
        for (let i = 0; i < data.length; i++) {
            energy += data[i] * data[i];
        }
        const rms = Math.sqrt(energy / data.length);
        const db = 20 * Math.log10(rms + 1e-10);
        
        // 计算过零率
        let zeroCrossings = 0;
        for (let i = 1; i < data.length; i++) {
            if ((data[i] >= 0 && data[i-1] < 0) || (data[i] < 0 && data[i-1] >= 0)) {
                zeroCrossings++;
            }
        }
        const zcr = zeroCrossings / data.length;
        
        return {
            energy: rms,
            energyDB: db,
            zeroCrossingRate: zcr,
            timestamp: Date.now()
        };
    }
}


// 导出
window.RealtimeSpectrogramRenderer = RealtimeSpectrogramRenderer;
window.AudioStreamProcessor = AudioStreamProcessor;

