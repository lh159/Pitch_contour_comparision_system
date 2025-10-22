/**
 * 频谱镜子 - 简化版（仅实时监测模式）
 */

class SpectrogramMirror {
    constructor() {
        this.canvas = document.getElementById('spectrogram-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.realtimeRenderer = null;
        this.isMonitoring = false;
        
        this.init();
    }

    init() {
        console.log('初始化频谱镜子（实时监测模式）...');
        this.setupEventListeners();
        this.drawPlaceholder();
    }

    setupEventListeners() {
        // 开始监测按钮
        const startBtn = document.getElementById('start-monitoring');
        const pauseBtn = document.getElementById('pause-monitoring');
        const resumeBtn = document.getElementById('resume-monitoring');
        const stopBtn = document.getElementById('stop-monitoring');
        const indicator = document.getElementById('monitoring-indicator');
        const pausedIndicator = document.getElementById('paused-indicator');
        
        if (startBtn) {
            startBtn.addEventListener('click', async () => {
                const success = await this.startMonitoring();
                if (success) {
                    startBtn.style.display = 'none';
                    pauseBtn.style.display = 'inline-flex';
                    stopBtn.style.display = 'inline-flex';
                    indicator.style.display = 'flex';
                }
            });
        }
        
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => {
                this.pauseMonitoring();
                pauseBtn.style.display = 'none';
                resumeBtn.style.display = 'inline-flex';
                indicator.style.display = 'none';
                pausedIndicator.style.display = 'flex';
            });
        }
        
        if (resumeBtn) {
            resumeBtn.addEventListener('click', () => {
                this.resumeMonitoring();
                resumeBtn.style.display = 'none';
                pauseBtn.style.display = 'inline-flex';
                pausedIndicator.style.display = 'none';
                indicator.style.display = 'flex';
            });
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.stopMonitoring();
                stopBtn.style.display = 'none';
                pauseBtn.style.display = 'none';
                resumeBtn.style.display = 'none';
                startBtn.style.display = 'inline-flex';
                indicator.style.display = 'none';
                pausedIndicator.style.display = 'none';
            });
        }
        
        // 共振峰显示开关
        const formantToggle = document.getElementById('formant-toggle');
        if (formantToggle) {
            formantToggle.addEventListener('change', (e) => {
                this.toggleFormants(e.target.checked);
            });
        }
        
        // 拼音显示开关
        const pinyinToggle = document.getElementById('pinyin-toggle');
        const clearPinyinBtn = document.getElementById('clear-pinyin');
        const pinyinInfo = document.getElementById('pinyin-info');
        
        if (pinyinToggle) {
            pinyinToggle.addEventListener('change', (e) => {
                this.togglePinyin(e.target.checked);
                
                // 显示/隐藏清除按钮
                if (clearPinyinBtn) {
                    clearPinyinBtn.style.display = e.target.checked ? 'inline-flex' : 'none';
                }
                
                // 显示/隐藏拼音说明
                if (pinyinInfo) {
                    pinyinInfo.style.display = e.target.checked ? 'block' : 'none';
                }
            });
        }
        
        // 清除拼音按钮
        if (clearPinyinBtn) {
            clearPinyinBtn.addEventListener('click', () => {
                this.clearPinyinMarkers();
            });
        }
    }
    
    toggleFormants(show) {
        console.log('切换共振峰显示:', show);
        if (this.realtimeRenderer) {
            this.realtimeRenderer.toggleFormants(show);
        }
    }
    
    togglePinyin(show) {
        console.log('切换拼音显示:', show);
        if (this.realtimeRenderer) {
            this.realtimeRenderer.togglePinyin(show);
        }
    }
    
    clearPinyinMarkers() {
        console.log('清除拼音标记');
        if (this.realtimeRenderer) {
            this.realtimeRenderer.clearPinyinMarkers();
        }
    }

    async startMonitoring() {
        try {
            console.log('启动实时监测模式...');
            
            // 隐藏占位符
            const placeholder = document.getElementById('canvas-placeholder');
            if (placeholder) {
                placeholder.style.display = 'none';
            }
            
            // 创建实时渲染器
            if (!this.realtimeRenderer) {
                this.realtimeRenderer = new RealtimeSpectrogramRenderer(this.canvas, {
                    fftSize: 2048,
                    smoothingTimeConstant: 0.75,
                    scrollSpeed: 2,
                    colorScheme: 'hot',
                    showWaveform: true,
                    showFrequencyLabels: true,
                    maxFrequency: 8000,
                    minDecibels: -90,
                    maxDecibels: -10,
                    showFormants: true  // 默认显示共振峰
                });
                
                // 同步拼音开关状态
                const pinyinToggle = document.getElementById('pinyin-toggle');
                if (pinyinToggle && pinyinToggle.checked) {
                    this.realtimeRenderer.showPinyin = true;
                    console.log('同步拼音开关状态: 已开启');
                }
                
                // 同步共振峰开关状态
                const formantToggle = document.getElementById('formant-toggle');
                if (formantToggle) {
                    this.realtimeRenderer.showFormants = formantToggle.checked;
                }
            }
            
            // 启动实时渲染
            const success = await this.realtimeRenderer.start();
            
            if (success) {
                this.isMonitoring = true;
                console.log('✓ 实时监测模式已启动');
                return true;
            } else {
                // 恢复占位符
                if (placeholder) {
                    placeholder.style.display = 'flex';
                }
                return false;
            }
        } catch (error) {
            console.error('启动实时监测失败:', error);
            alert('启动实时监测失败: ' + error.message);
            return false;
        }
    }

    pauseMonitoring() {
        console.log('暂停实时监测...');
        
        if (this.realtimeRenderer) {
            this.realtimeRenderer.pause();
        }
        
        console.log('✓ 实时监测已暂停');
    }
    
    resumeMonitoring() {
        console.log('继续实时监测...');
        
        if (this.realtimeRenderer) {
            this.realtimeRenderer.resume();
        }
        
        console.log('✓ 实时监测已继续');
    }

    stopMonitoring() {
        console.log('停止实时监测模式...');
        
        // 停止实时渲染
        if (this.realtimeRenderer) {
            this.realtimeRenderer.stop();
        }
        
        this.isMonitoring = false;
        
        // 清空画布并显示占位符
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        const placeholder = document.getElementById('canvas-placeholder');
        if (placeholder) {
            placeholder.style.display = 'flex';
        }
        
        console.log('✓ 实时监测模式已停止');
    }

    drawPlaceholder() {
        // 占位符已在HTML中，这里只确保画布是黑色背景
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    const _spectrogramMirror = new SpectrogramMirror();
    console.log('✓ 频谱镜子已加载（简化版）');
});
