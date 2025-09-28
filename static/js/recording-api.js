/**
 * 录音API适配器 - 支持浏览器录音和服务器录音两种模式
 * 用于解决移动端和云服务器部署时的录音功能问题
 */

class RecordingAPIAdapter {
    constructor() {
        this.mode = 'browser'; // 'browser' 或 'server'
        this.session_id = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        
        // 检测录音支持情况
        this.detectRecordingSupport();
    }
    
    /**
     * 检测录音支持情况并选择最佳模式
     */
    async detectRecordingSupport() {
        try {
            // 首先检查是否支持浏览器录音
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                // 尝试获取麦克风权限（不开始录音）
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                
                // 检查MediaRecorder支持
                if (typeof MediaRecorder !== 'undefined') {
                    console.log('✅ 浏览器录音支持良好，使用浏览器模式');
                    this.mode = 'browser';
                    return;
                }
            }
        } catch (error) {
            console.warn('⚠️ 浏览器录音不可用:', error.message);
        }
        
        // 如果浏览器录音不可用，切换到服务器模式
        console.log('🔄 切换到服务器录音模式');
        this.mode = 'server';
    }
    
    /**
     * 开始录音
     */
    async startRecording() {
        if (this.isRecording) {
            throw new Error('录音已在进行中');
        }
        
        if (this.mode === 'browser') {
            return await this.startBrowserRecording();
        } else {
            return await this.startServerRecording();
        }
    }
    
    /**
     * 停止录音
     */
    async stopRecording() {
        console.log(`🎙️ 尝试停止录音，当前状态: ${this.isRecording}, 模式: ${this.mode}`);
        
        // 🔧 更宽松的状态检查，允许在某些异常情况下强制停止
        if (!this.isRecording) {
            console.warn('⚠️ 没有正在进行的录音，但继续尝试清理状态');
            // 不直接抛出错误，而是尝试清理状态
            this.cleanup();
            return {
                success: false,
                message: '没有正在进行的录音，已清理状态',
                mode: this.mode
            };
        }
        
        try {
            if (this.mode === 'browser') {
                return await this.stopBrowserRecording();
            } else {
                return await this.stopServerRecording();
            }
        } catch (error) {
            console.error('停止录音时出错:', error);
            // 确保状态被清理
            this.cleanup();
            throw error;
        }
    }
    
    /**
     * 浏览器录音 - 开始
     */
    async startBrowserRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // 选择最佳录音格式
            let options = {};
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                options.mimeType = 'audio/webm;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/webm')) {
                options.mimeType = 'audio/webm';
            } else if (MediaRecorder.isTypeSupported('audio/wav')) {
                options.mimeType = 'audio/wav';
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                options.mimeType = 'audio/mp4';
            }
            
            if (options.mimeType) {
                // 🔧 针对手机录音优化音质参数
                if (options.mimeType.includes('opus')) {
                    options.audioBitsPerSecond = 256000;  // Opus格式使用更高比特率
                } else if (options.mimeType.includes('webm')) {
                    options.audioBitsPerSecond = 192000;  // WebM格式
                } else {
                    options.audioBitsPerSecond = 128000;  // 其他格式
                }
            }
            
            this.mediaRecorder = new MediaRecorder(stream, options);
            this.audioChunks = [];
            
            return new Promise((resolve, reject) => {
                this.mediaRecorder.ondataavailable = (event) => {
                    this.audioChunks.push(event.data);
                };
                
                this.mediaRecorder.onstart = () => {
                    this.isRecording = true;
                    console.log('🎙️ 浏览器录音开始');
                    resolve({
                        success: true,
                        mode: 'browser',
                        message: '浏览器录音已开始'
                    });
                };
                
                this.mediaRecorder.onerror = (error) => {
                    this.isRecording = false;
                    reject(error);
                };
                
                this.mediaRecorder.start();
            });
            
        } catch (error) {
            throw new Error(`浏览器录音启动失败: ${error.message}`);
        }
    }
    
    /**
     * 浏览器录音 - 停止
     */
    async stopBrowserRecording() {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder) {
                reject(new Error('录音器未初始化'));
                return;
            }
            
            this.mediaRecorder.onstop = async () => {
                console.log('🎙️ MediaRecorder停止事件触发');
                this.isRecording = false;
                
                // 停止所有音频轨道
                if (this.mediaRecorder.stream) {
                    this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
                }
                
                // 创建音频Blob
                const audioBlob = new Blob(this.audioChunks, { 
                    type: this.mediaRecorder.mimeType 
                });
                
                console.log(`📦 创建音频Blob: ${audioBlob.size} bytes, 类型: ${audioBlob.type}`);
                
                try {
                    // 上传录音
                    const result = await this.uploadRecording(audioBlob);
                    console.log('🎙️ 浏览器录音完成并上传');
                    resolve(result);
                } catch (error) {
                    console.error('📤 上传录音失败:', error);
                    // 确保状态被重置
                    this.isRecording = false;
                    reject(error);
                }
            };
            
            this.mediaRecorder.stop();
        });
    }
    
    /**
     * 服务器录音 - 开始
     */
    async startServerRecording() {
        try {
            const response = await fetch('/api/recording/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.session_id
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.session_id = data.session_id;
                this.isRecording = true;
                
                console.log('🎙️ 服务器录音开始，会话ID:', this.session_id);
                
                return {
                    success: true,
                    mode: 'server',
                    session_id: this.session_id,
                    message: '服务器录音已开始'
                };
            } else {
                throw new Error(data.error);
            }
            
        } catch (error) {
            throw new Error(`服务器录音启动失败: ${error.message}`);
        }
    }
    
    /**
     * 服务器录音 - 停止
     */
    async stopServerRecording() {
        try {
            if (!this.session_id) {
                throw new Error('录音会话ID不存在');
            }
            
            const response = await fetch('/api/recording/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.session_id
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.isRecording = false;
                console.log('🎙️ 服务器录音完成');
                
                return {
                    success: true,
                    mode: 'server',
                    file_id: data.file_id,
                    filename: data.filename,
                    audioUrl: data.audioUrl,  // 添加音频URL
                    duration: data.duration,
                    message: data.message
                };
            } else {
                throw new Error(data.error);
            }
            
        } catch (error) {
            throw new Error(`服务器录音停止失败: ${error.message}`);
        }
    }
    
    /**
     * 上传录音文件（浏览器模式使用）
     */
    async uploadRecording(audioBlob) {
        const formData = new FormData();
        
        // 根据录音格式设置文件名
        let filename = 'recording.wav';
        if (this.mediaRecorder && this.mediaRecorder.mimeType) {
            if (this.mediaRecorder.mimeType.includes('webm')) {
                filename = 'recording.webm';
            } else if (this.mediaRecorder.mimeType.includes('mp4')) {
                filename = 'recording.mp4';
            } else if (this.mediaRecorder.mimeType.includes('ogg')) {
                filename = 'recording.ogg';
            }
        }
        
        formData.append('audio', audioBlob, filename);
        
        const response = await fetch('/api/audio/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            return {
                success: true,
                file_id: data.file_id,
                filename: data.filename,
                audioUrl: data.audioUrl,  // 添加音频URL
                duration: data.pitch_info?.duration || 0,
                message: '录音上传成功'
            };
        } else {
            throw new Error(data.error);
        }
    }
    
    /**
     * 获取录音状态
     */
    async getRecordingStatus() {
        if (this.mode === 'browser') {
            return {
                success: true,
                is_recording: this.isRecording,
                mode: 'browser'
            };
        } else if (this.session_id) {
            try {
                const response = await fetch(`/api/recording/status/${this.session_id}`);
                const data = await response.json();
                return {
                    ...data,
                    mode: 'server'
                };
            } catch (error) {
                return {
                    success: false,
                    error: error.message,
                    mode: 'server'
                };
            }
        } else {
            return {
                success: true,
                is_recording: false,
                mode: 'server'
            };
        }
    }
    
    /**
     * 获取当前录音模式
     */
    getMode() {
        return this.mode;
    }
    
    /**
     * 强制切换录音模式
     */
    setMode(mode) {
        if (['browser', 'server'].includes(mode)) {
            this.mode = mode;
            console.log(`🔄 录音模式已切换到: ${mode}`);
        } else {
            console.warn('⚠️ 无效的录音模式:', mode);
        }
    }
    
    /**
     * 清理资源
     */
    cleanup() {
        console.log('🧹 清理录音状态和资源');
        
        // 重置录音状态
        this.isRecording = false;
        
        // 清理浏览器录音资源
        if (this.mediaRecorder) {
            if (this.mediaRecorder.state === 'recording') {
                try {
                    this.mediaRecorder.stop();
                } catch (e) {
                    console.warn('停止MediaRecorder时出错:', e);
                }
            }
            
            // 停止所有音频轨道
            if (this.mediaRecorder.stream) {
                this.mediaRecorder.stream.getTracks().forEach(track => {
                    try {
                        track.stop();
                    } catch (e) {
                        console.warn('停止音频轨道时出错:', e);
                    }
                });
            }
            
            this.mediaRecorder = null;
        }
        
        // 清理音频数据
        this.audioChunks = [];
        this.session_id = null;
        
        console.log('✅ 录音状态和资源已清理');
    }
}

// 导出到全局作用域
window.RecordingAPIAdapter = RecordingAPIAdapter;
