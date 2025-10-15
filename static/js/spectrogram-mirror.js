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
        const stopBtn = document.getElementById('stop-monitoring');
        const indicator = document.getElementById('monitoring-indicator');
        
        if (startBtn) {
            startBtn.addEventListener('click', async () => {
                const success = await this.startMonitoring();
                if (success) {
                    startBtn.style.display = 'none';
                    stopBtn.style.display = 'inline-flex';
                    indicator.style.display = 'flex';
                }
            });
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.stopMonitoring();
                stopBtn.style.display = 'none';
                startBtn.style.display = 'inline-flex';
                indicator.style.display = 'none';
            });
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
                    maxDecibels: -10
                });
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
let spectrogramMirror;
document.addEventListener('DOMContentLoaded', () => {
    spectrogramMirror = new SpectrogramMirror();
    console.log('✓ 频谱镜子已加载（简化版）');
});
