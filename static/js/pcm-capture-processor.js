/**
 * PCM 音频捕获处理器（AudioWorklet）
 * 用于实时语音识别的 PCM 数据采集
 * 
 * 功能：
 * - 实时捕获麦克风 PCM 数据
 * - 降采样到 16kHz（语音识别标准采样率）
 * - 转换为 Int16 格式（WAV 标准）
 * - 批量发送数据，减少网络请求
 */

class PCMCaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        
        // 配置参数
        this.targetSampleRate = 16000;  // 目标采样率（语音识别标准）
        this.sourceSampleRate = sampleRate;  // 当前采样率（通常是 48000）
        this.bufferSize = this.targetSampleRate * 0.5;  // 0.5秒的缓冲区
        
        // 降采样参数
        this.downsampleRatio = this.sourceSampleRate / this.targetSampleRate;
        this.downsampleOffset = 0;
        
        // PCM 数据缓冲区
        this.pcmBuffer = [];
        
        console.log(`🎤 PCM Processor 初始化:
            源采样率: ${this.sourceSampleRate} Hz
            目标采样率: ${this.targetSampleRate} Hz
            降采样比率: ${this.downsampleRatio.toFixed(2)}
            缓冲区大小: ${this.bufferSize} samples (0.5秒)
        `);
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        
        // 如果没有输入，跳过
        if (!input || !input[0]) {
            return true;
        }
        
        const inputChannel = input[0];  // 获取第一个声道（单声道）
        
        // 降采样并转换为 Int16
        for (let i = 0; i < inputChannel.length; i++) {
            this.downsampleOffset += 1;
            
            // 按照降采样比率采样
            if (this.downsampleOffset >= this.downsampleRatio) {
                this.downsampleOffset -= this.downsampleRatio;
                
                // 转换 Float32 [-1, 1] 到 Int16 [-32768, 32767]
                let sample = inputChannel[i];
                
                // 限幅
                sample = Math.max(-1, Math.min(1, sample));
                
                // 转换为 Int16
                const int16Sample = sample < 0 
                    ? sample * 0x8000  // -32768
                    : sample * 0x7FFF; // 32767
                
                this.pcmBuffer.push(Math.round(int16Sample));
            }
        }
        
        // 当缓冲区达到 0.5 秒时，发送数据
        if (this.pcmBuffer.length >= this.bufferSize) {
            // 转换为 Int16Array
            const int16Data = new Int16Array(this.pcmBuffer);
            
            // 发送到主线程
            this.port.postMessage({
                type: 'pcm_data',
                data: int16Data.buffer,  // ArrayBuffer
                sampleRate: this.targetSampleRate,
                samples: int16Data.length,
                duration: int16Data.length / this.targetSampleRate
            }, [int16Data.buffer]);  // Transfer ownership
            
            // 清空缓冲区
            this.pcmBuffer = [];
        }
        
        return true;  // 保持处理器运行
    }
}

// 注册处理器
registerProcessor('pcm-capture-processor', PCMCaptureProcessor);

