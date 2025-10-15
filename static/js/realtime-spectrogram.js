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
        this.animationId = null;
        this.spectrogramData = [];  // 存储历史频谱数据
        this.maxFrames = Math.ceil(this.width / this.options.scrollSpeed);
        
        // Web Audio API
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.waveformArray = null;
        
        // VOT检测
        this.votMarkers = [];
        this.energyHistory = [];
        this.energyThreshold = -40;  // dB
        
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
            const stream = await navigator.mediaDevices.getUserMedia({
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
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            
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
            
            // 开始渲染
            this.isRunning = true;
            this.render();
            
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
    
    stop() {
        if (!this.isRunning) {
            return;
        }
        
        this.isRunning = false;
        
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        if (this.microphone) {
            this.microphone.disconnect();
            this.microphone = null;
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
        
        // 添加当前帧到历史
        this.spectrogramData.push(new Uint8Array(this.dataArray));
        if (this.spectrogramData.length > this.maxFrames) {
            this.spectrogramData.shift();
        }
        
        // 绘制
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
        
        // 计算频谱显示区域
        const spectrogramHeight = this.options.showWaveform ? this.height * 0.75 : this.height;
        const waveformHeight = this.height - spectrogramHeight;
        
        // 绘制频谱图
        this.drawSpectrogram(ctx, spectrogramHeight);
        
        // 绘制波形
        if (this.options.showWaveform) {
            this.drawWaveform(ctx, spectrogramHeight, waveformHeight);
        }
        
        // 绘制频率标签
        if (this.options.showFrequencyLabels) {
            this.drawFrequencyLabels(ctx, spectrogramHeight);
        }
        
        // 绘制VOT标记
        this.drawVOTMarkers(ctx, spectrogramHeight);
        
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
    
    // 公共方法：更新配置
    updateOptions(newOptions) {
        Object.assign(this.options, newOptions);
        console.log('配置已更新:', this.options);
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

