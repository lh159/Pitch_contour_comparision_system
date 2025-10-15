/**
 * Web Worker for Audio Processing
 * 在后台线程处理音频数据，避免阻塞主线程
 */

// FFT实现（简化版，用于频谱计算）
class FFT {
    constructor(size) {
        this.size = size;
        this.cosTable = new Float32Array(size);
        this.sinTable = new Float32Array(size);
        
        for (let i = 0; i < size; i++) {
            const angle = -2 * Math.PI * i / size;
            this.cosTable[i] = Math.cos(angle);
            this.sinTable[i] = Math.sin(angle);
        }
    }
    
    forward(input) {
        const n = input.length;
        const output = new Float32Array(n);
        
        for (let k = 0; k < n; k++) {
            let real = 0;
            let imag = 0;
            
            for (let t = 0; t < n; t++) {
                const angle = 2 * Math.PI * k * t / n;
                real += input[t] * Math.cos(angle);
                imag -= input[t] * Math.sin(angle);
            }
            
            output[k] = Math.sqrt(real * real + imag * imag);
        }
        
        return output;
    }
}

// 音频特征提取器
class AudioFeatureExtractor {
    constructor(sampleRate = 16000) {
        this.sampleRate = sampleRate;
        this.fftSize = 2048;
        this.hopLength = 512;
        this.fft = new FFT(this.fftSize);
    }
    
    // 计算短时能量
    calculateEnergy(samples) {
        let sum = 0;
        for (let i = 0; i < samples.length; i++) {
            sum += samples[i] * samples[i];
        }
        const rms = Math.sqrt(sum / samples.length);
        const db = 20 * Math.log10(rms + 1e-10);
        return { rms, db };
    }
    
    // 计算过零率
    calculateZeroCrossingRate(samples) {
        let crossings = 0;
        for (let i = 1; i < samples.length; i++) {
            if ((samples[i] >= 0 && samples[i-1] < 0) || 
                (samples[i] < 0 && samples[i-1] >= 0)) {
                crossings++;
            }
        }
        return crossings / samples.length;
    }
    
    // 计算频谱质心
    calculateSpectralCentroid(spectrum, frequencies) {
        let weightedSum = 0;
        let sum = 0;
        
        for (let i = 0; i < spectrum.length; i++) {
            weightedSum += spectrum[i] * frequencies[i];
            sum += spectrum[i];
        }
        
        return sum > 0 ? weightedSum / sum : 0;
    }
    
    // 计算频谱平坦度
    calculateSpectralFlatness(spectrum) {
        let geometricMean = 1;
        let arithmeticMean = 0;
        const n = spectrum.length;
        
        for (let i = 0; i < n; i++) {
            geometricMean *= Math.pow(spectrum[i] + 1e-10, 1/n);
            arithmeticMean += spectrum[i];
        }
        
        arithmeticMean /= n;
        
        return geometricMean / (arithmeticMean + 1e-10);
    }
    
    // 检测VOT
    detectVOT(samples, threshold = -40) {
        const frameSize = Math.floor(0.01 * this.sampleRate);  // 10ms
        const hopSize = frameSize / 2;
        const energyFrames = [];
        
        // 计算每帧能量
        for (let i = 0; i < samples.length - frameSize; i += hopSize) {
            const frame = samples.slice(i, i + frameSize);
            const { db } = this.calculateEnergy(frame);
            energyFrames.push({ index: i, db });
        }
        
        // 找到爆破点（第一个超过阈值的帧）
        let burstIndex = -1;
        for (let i = 0; i < energyFrames.length; i++) {
            if (energyFrames[i].db > threshold) {
                burstIndex = i;
                break;
            }
        }
        
        if (burstIndex === -1) {
            return { success: false, error: '未检测到爆破音' };
        }
        
        // 找到浊音开始点（能量稳定增长）
        const maxEnergy = Math.max(...energyFrames.slice(burstIndex).map(f => f.db));
        const voiceThreshold = maxEnergy - 10;
        
        let voiceIndex = -1;
        for (let i = burstIndex; i < energyFrames.length; i++) {
            if (energyFrames[i].db > voiceThreshold) {
                voiceIndex = i;
                break;
            }
        }
        
        if (voiceIndex === -1) {
            return { success: false, error: '未检测到浊音开始' };
        }
        
        // 计算VOT（毫秒）
        const votFrames = voiceIndex - burstIndex;
        const votMs = votFrames * hopSize / this.sampleRate * 1000;
        
        return {
            success: true,
            vot_ms: votMs,
            burst_time: burstIndex * hopSize / this.sampleRate,
            voice_time: voiceIndex * hopSize / this.sampleRate
        };
    }
    
    // 完整特征提取
    extractFeatures(samples) {
        const energy = this.calculateEnergy(samples);
        const zcr = this.calculateZeroCrossingRate(samples);
        
        // 计算频谱
        const paddedSamples = new Float32Array(this.fftSize);
        paddedSamples.set(samples.slice(0, Math.min(samples.length, this.fftSize)));
        const spectrum = this.fft.forward(paddedSamples);
        
        // 频率轴
        const frequencies = new Float32Array(spectrum.length);
        for (let i = 0; i < spectrum.length; i++) {
            frequencies[i] = i * this.sampleRate / this.fftSize;
        }
        
        const centroid = this.calculateSpectralCentroid(spectrum, frequencies);
        const flatness = this.calculateSpectralFlatness(spectrum);
        
        return {
            energy: energy.rms,
            energyDB: energy.db,
            zeroCrossingRate: zcr,
            spectralCentroid: centroid,
            spectralFlatness: flatness,
            spectrum: Array.from(spectrum),
            frequencies: Array.from(frequencies)
        };
    }
}

// Worker全局变量
let featureExtractor = null;

// 消息处理
self.onmessage = function(e) {
    const { type, data } = e.data;
    
    switch (type) {
        case 'init':
            featureExtractor = new AudioFeatureExtractor(data.sampleRate || 16000);
            self.postMessage({ type: 'init_complete' });
            break;
            
        case 'process_audio':
            if (!featureExtractor) {
                self.postMessage({ 
                    type: 'error', 
                    error: 'Feature extractor not initialized' 
                });
                return;
            }
            
            const samples = new Float32Array(data.samples);
            const features = featureExtractor.extractFeatures(samples);
            
            self.postMessage({
                type: 'features',
                data: features,
                timestamp: data.timestamp
            });
            break;
            
        case 'detect_vot':
            if (!featureExtractor) {
                self.postMessage({ 
                    type: 'error', 
                    error: 'Feature extractor not initialized' 
                });
                return;
            }
            
            const audioSamples = new Float32Array(data.samples);
            const votResult = featureExtractor.detectVOT(
                audioSamples, 
                data.threshold || -40
            );
            
            self.postMessage({
                type: 'vot_result',
                data: votResult,
                timestamp: data.timestamp
            });
            break;
            
        case 'batch_process':
            if (!featureExtractor) {
                self.postMessage({ 
                    type: 'error', 
                    error: 'Feature extractor not initialized' 
                });
                return;
            }
            
            const batchResults = [];
            for (const item of data.batch) {
                const samples = new Float32Array(item.samples);
                const features = featureExtractor.extractFeatures(samples);
                batchResults.push({
                    id: item.id,
                    features: features
                });
            }
            
            self.postMessage({
                type: 'batch_results',
                data: batchResults
            });
            break;
            
        default:
            self.postMessage({ 
                type: 'error', 
                error: `Unknown message type: ${type}` 
            });
    }
};

// 错误处理
self.onerror = function(error) {
    self.postMessage({
        type: 'error',
        error: error.message
    });
};

console.log('Audio Processor Worker initialized');

