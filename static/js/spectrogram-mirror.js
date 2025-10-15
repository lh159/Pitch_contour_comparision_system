/**
 * 频谱镜子 - 前端交互脚本
 * 实现录音、频谱图可视化、AI分析展示
 */

class SpectrogramMirror {
    constructor() {
        this.canvas = document.getElementById('spectrogram-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.currentMode = 'free';  // 'free', 'zhi', 'chi'
        this.showTemplate = false;
        this.history = JSON.parse(localStorage.getItem('spectrogram_history') || '[]');
        
        // 实时模式
        this.realtimeMode = false;
        this.realtimeRenderer = null;
        
        this.init();
    }

    init() {
        console.log('初始化频谱镜子...');
        this.setupEventListeners();
        this.renderHistory();
        this.drawPlaceholder();
    }

    setupEventListeners() {
        // 录音控制
        document.getElementById('start-recording').addEventListener('click', () => this.startRecording());
        document.getElementById('stop-recording').addEventListener('click', () => this.stopRecording());

        // 模式切换
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchMode(e.target.dataset.mode));
        });

        // 模板显示切换
        document.getElementById('show-template').addEventListener('change', (e) => {
            this.showTemplate = e.target.checked;
            this.updateCanvas();
        });

        // 实时模式切换
        document.getElementById('realtime-mode').addEventListener('change', (e) => {
            this.toggleRealtimeMode(e.target.checked);
        });

        // 清空历史
        document.getElementById('clear-history').addEventListener('click', () => this.clearHistory());
    }

    switchMode(mode) {
        this.currentMode = mode;
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        console.log(`切换模式: ${mode}`);
    }

    async startRecording() {
        try {
            console.log('请求麦克风权限...');
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.audioChunks = [];
            this.mediaRecorder = new MediaRecorder(stream);

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.analyzeAudio(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start();

            // 更新UI
            document.getElementById('start-recording').style.display = 'none';
            document.getElementById('stop-recording').style.display = 'inline-flex';
            document.getElementById('recording-indicator').style.display = 'flex';

            console.log('✓ 录音开始');
        } catch (error) {
            console.error('录音失败:', error);
            alert('无法访问麦克风，请确保已授予权限');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();

            // 更新UI
            document.getElementById('start-recording').style.display = 'inline-flex';
            document.getElementById('stop-recording').style.display = 'none';
            document.getElementById('recording-indicator').style.display = 'none';

            console.log('✓ 录音停止');
        }
    }

    async analyzeAudio(audioBlob) {
        try {
            // 显示加载状态
            this.showLoading(true);

            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            // 如果有目标音素，添加到请求中
            if (this.currentMode !== 'free') {
                formData.append('target_phoneme', this.currentMode);
            }

            console.log('发送音频到服务器进行分析...');
            const response = await fetch('/api/spectrogram/analyze', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('分析结果:', result);

            this.showLoading(false);

            if (result.success) {
                this.displayResults(result);
                this.addToHistory(result);
            } else {
                alert('分析失败: ' + result.error);
            }
        } catch (error) {
            console.error('分析出错:', error);
            this.showLoading(false);
            alert('分析出错: ' + error.message);
        }
    }

    displayResults(result) {
        // 显示分析区域
        document.getElementById('analysis-section').style.display = 'block';

        // 绘制频谱图
        this.drawSpectrogram(result.spectrogram_data);

        // 显示分类结果
        const prediction = result.classification.prediction;
        const confidence = result.classification.confidence;
        
        const predictionEl = document.getElementById('prediction-result');
        predictionEl.innerHTML = `
            <span class="phoneme-text ${prediction}">${prediction.toUpperCase()}</span>
            <span class="confidence-text">置信度: ${(confidence * 100).toFixed(1)}%</span>
        `;

        // 如果有评分，显示评分
        if (result.score !== null && result.score !== undefined) {
            document.getElementById('score-display').style.display = 'flex';
            document.getElementById('score-value').textContent = Math.round(result.score);
            document.getElementById('grade-badge').textContent = result.grade;
            document.getElementById('grade-badge').className = `grade-badge grade-${result.grade}`;
        } else {
            document.getElementById('score-display').style.display = 'none';
        }

        // 显示特征参数
        const vot = result.features.vot_ms;
        const aspiration = result.features.aspiration_score;

        document.getElementById('vot-value').textContent = vot.toFixed(1);
        document.getElementById('aspiration-value').textContent = aspiration.toFixed(1);

        // 更新进度条
        document.getElementById('vot-bar').style.width = Math.min(vot / 100 * 100, 100) + '%';
        document.getElementById('aspiration-bar').style.width = Math.min(aspiration, 100) + '%';

        // 更新对比条
        const zhiConf = result.classification.zhi_confidence;
        const chiConf = result.classification.chi_confidence;

        document.getElementById('zhi-bar').style.width = (zhiConf * 100) + '%';
        document.getElementById('chi-bar').style.width = (chiConf * 100) + '%';
        document.getElementById('zhi-percent').textContent = (zhiConf * 100).toFixed(1) + '%';
        document.getElementById('chi-percent').textContent = (chiConf * 100).toFixed(1) + '%';

        // 显示反馈
        document.getElementById('feedback-text').textContent = result.feedback;

        // 滚动到结果区域
        document.getElementById('analysis-section').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    drawSpectrogram(data) {
        const { spec, times, frequencies } = data;
        
        if (!spec || spec.length === 0) {
            console.error('频谱数据为空');
            return;
        }

        // 隐藏占位符
        document.getElementById('canvas-placeholder').style.display = 'none';

        const freqBins = spec.length;
        const timeFrames = spec[0].length;
        const pixelWidth = this.canvas.width / timeFrames;
        const pixelHeight = this.canvas.height / freqBins;

        console.log(`绘制频谱图: ${freqBins} 频率 × ${timeFrames} 时间帧`);

        // 清空画布
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // 绘制频谱图
        for (let f = 0; f < freqBins; f++) {
            for (let t = 0; t < timeFrames; t++) {
                const db = spec[f][t];
                const normalized = (db + 80) / 80;  // 假设范围 -80 到 0 dB
                const value = Math.max(0, Math.min(1, normalized));
                
                // Hot colormap: 黑->红->黄->白
                const r = Math.min(255, value * 3 * 255);
                const g = Math.min(255, Math.max(0, (value - 0.33) * 3 * 255));
                const b = Math.min(255, Math.max(0, (value - 0.66) * 3 * 255));
                
                this.ctx.fillStyle = `rgb(${Math.floor(r)}, ${Math.floor(g)}, ${Math.floor(b)})`;
                
                // Y轴翻转（频率从低到高）
                const x = t * pixelWidth;
                const y = this.canvas.height - (f + 1) * pixelHeight;
                this.ctx.fillRect(x, y, pixelWidth + 1, pixelHeight + 1);
            }
        }

        // 绘制网格和坐标轴
        this.drawAxes(times, frequencies);

        // 如果启用模板，绘制模板提示
        if (this.showTemplate && this.currentMode !== 'free') {
            this.drawTemplate(this.currentMode);
        }
    }

    drawAxes(times, frequencies) {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        this.ctx.lineWidth = 1;
        this.ctx.font = '12px sans-serif';
        this.ctx.fillStyle = 'white';

        const maxTime = times[times.length - 1];
        const maxFreq = frequencies[frequencies.length - 1];

        // 时间轴（X轴）
        for (let i = 0; i <= 5; i++) {
            const x = (i / 5) * this.canvas.width;
            const time = (i / 5) * maxTime;

            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();

            this.ctx.fillText(
                `${time.toFixed(2)}s`,
                x + 2,
                this.canvas.height - 5
            );
        }

        // 频率轴（Y轴）
        for (let i = 0; i <= 5; i++) {
            const y = (i / 5) * this.canvas.height;
            const freq = ((5 - i) / 5) * maxFreq;

            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();

            this.ctx.fillText(
                `${Math.round(freq)}Hz`,
                5,
                y - 2
            );
        }
    }

    drawTemplate(templateType) {
        this.ctx.strokeStyle = 'rgba(0, 255, 255, 0.8)';
        this.ctx.lineWidth = 3;
        this.ctx.setLineDash([5, 5]);

        if (templateType === 'zhi') {
            // 绘制"瘦条"引导
            const x = this.canvas.width * 0.1;
            const width = this.canvas.width * 0.05;
            this.ctx.strokeRect(x, 0, width, this.canvas.height * 0.6);

            this.ctx.fillStyle = 'cyan';
            this.ctx.font = 'bold 20px sans-serif';
            this.ctx.fillText('目标：短促的瘦条', x, this.canvas.height - 20);
        } else if (templateType === 'chi') {
            // 绘制"胖云"引导
            const x = this.canvas.width * 0.1;
            const width = this.canvas.width * 0.15;
            this.ctx.strokeRect(x, 0, width, this.canvas.height * 0.8);

            this.ctx.fillStyle = 'cyan';
            this.ctx.font = 'bold 20px sans-serif';
            this.ctx.fillText('目标：长而密集的胖云', x, this.canvas.height - 20);
        }

        this.ctx.setLineDash([]);
    }

    drawPlaceholder() {
        // 占位符已在HTML中，这里不需要操作
    }

    updateCanvas() {
        // 当切换模板显示时，重新绘制
        // （需要保存上次的数据）
    }

    addToHistory(result) {
        const record = {
            timestamp: new Date().toISOString(),
            mode: this.currentMode,
            prediction: result.classification.prediction,
            confidence: result.classification.confidence,
            vot: result.features.vot_ms,
            aspiration: result.features.aspiration_score,
            score: result.score,
            grade: result.grade
        };

        this.history.unshift(record);
        
        // 最多保存20条
        if (this.history.length > 20) {
            this.history = this.history.slice(0, 20);
        }

        localStorage.setItem('spectrogram_history', JSON.stringify(this.history));
        this.renderHistory();
    }

    renderHistory() {
        const historyList = document.getElementById('history-list');
        
        if (this.history.length === 0) {
            historyList.innerHTML = `
                <div class="empty-state">
                    <p>暂无练习记录</p>
                </div>
            `;
            return;
        }

        historyList.innerHTML = this.history.map((record, index) => {
            const date = new Date(record.timestamp);
            const timeStr = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            
            return `
                <div class="history-item">
                    <div class="history-time">${timeStr}</div>
                    <div class="history-content">
                        <div class="history-result">
                            <span class="phoneme-badge ${record.prediction}">${record.prediction.toUpperCase()}</span>
                            <span class="confidence-small">${(record.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div class="history-features">
                            <span>VOT: ${record.vot.toFixed(1)}ms</span>
                            <span>强度: ${record.aspiration.toFixed(1)}</span>
                            ${record.score !== null ? `<span>评分: ${Math.round(record.score)} (${record.grade})</span>` : ''}
                        </div>
                    </div>
                    <div class="history-mode">${this.getModeName(record.mode)}</div>
                </div>
            `;
        }).join('');
    }

    getModeName(mode) {
        const names = {
            'free': '自由',
            'zhi': 'zhi',
            'chi': 'chi'
        };
        return names[mode] || mode;
    }

    clearHistory() {
        if (confirm('确定要清空所有练习记录吗？')) {
            this.history = [];
            localStorage.removeItem('spectrogram_history');
            this.renderHistory();
            console.log('历史记录已清空');
        }
    }

    showLoading(show) {
        document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
    }

    // 实时模式控制
    async toggleRealtimeMode(enabled) {
        this.realtimeMode = enabled;
        
        if (enabled) {
            console.log('启用实时监测模式...');
            
            // 隐藏占位符
            document.getElementById('canvas-placeholder').style.display = 'none';
            
            // 创建实时渲染器
            if (!this.realtimeRenderer) {
                this.realtimeRenderer = new RealtimeSpectrogramRenderer(this.canvas, {
                    fftSize: 2048,
                    smoothingTimeConstant: 0.8,
                    scrollSpeed: 2,
                    colorScheme: 'hot',
                    showWaveform: true,
                    showFrequencyLabels: true,
                    maxFrequency: 8000
                });
            }
            
            // 启动实时渲染
            const success = await this.realtimeRenderer.start();
            
            if (success) {
                // 禁用录音按钮
                document.getElementById('start-recording').disabled = true;
                document.getElementById('start-recording').style.opacity = '0.5';
                
                console.log('✓ 实时监测模式已启动');
            } else {
                // 回退
                document.getElementById('realtime-mode').checked = false;
                this.realtimeMode = false;
            }
        } else {
            console.log('关闭实时监测模式...');
            
            // 停止实时渲染
            if (this.realtimeRenderer) {
                this.realtimeRenderer.stop();
            }
            
            // 恢复录音按钮
            document.getElementById('start-recording').disabled = false;
            document.getElementById('start-recording').style.opacity = '1';
            
            // 显示占位符
            this.drawPlaceholder();
            document.getElementById('canvas-placeholder').style.display = 'flex';
            
            console.log('✓ 实时监测模式已关闭');
        }
    }
}

// 初始化
let spectrogramMirror;
document.addEventListener('DOMContentLoaded', () => {
    spectrogramMirror = new SpectrogramMirror();
    console.log('✓ 频谱镜子已加载');
});

