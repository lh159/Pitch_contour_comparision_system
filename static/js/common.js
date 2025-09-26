// 通用JavaScript功能

// H5移动端特有变量
let isMobile = false;
let isIOS = false;
let isAndroid = false;
let deviceOrientation = 'portrait';
let vibrationSupported = false;

// H5移动端设备检测和初始化
function initMobileDetection() {
    const userAgent = navigator.userAgent;
    isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
    isIOS = /iPad|iPhone|iPod/.test(userAgent);
    isAndroid = /Android/i.test(userAgent);
    
    // 检测振动支持
    vibrationSupported = 'vibrate' in navigator;
    
    // 获取初始屏幕方向
    if (screen.orientation) {
        deviceOrientation = screen.orientation.angle === 0 || screen.orientation.angle === 180 ? 'portrait' : 'landscape';
    }
    
    console.log('📱 设备信息:', {
        isMobile,
        isIOS,
        isAndroid,
        vibrationSupported,
        deviceOrientation,
        screenSize: `${screen.width}x${screen.height}`,
        pixelRatio: window.devicePixelRatio || 1
    });
    
    // 移动端特殊处理
    if (isMobile) {
        document.body.classList.add('mobile-device');
        if (isIOS) document.body.classList.add('ios-device');
        if (isAndroid) document.body.classList.add('android-device');
        
        // 防止iOS Safari地址栏影响视口高度
        if (isIOS) {
            const setViewportHeight = () => {
                document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
            };
            setViewportHeight();
            window.addEventListener('resize', setViewportHeight);
            window.addEventListener('orientationchange', () => {
                setTimeout(setViewportHeight, 100);
            });
        }
    }
}

// 触摸反馈函数
function triggerHapticFeedback(type = 'light') {
    if (!vibrationSupported || !isMobile) return;
    
    try {
        switch(type) {
            case 'light':
                navigator.vibrate(10);
                break;
            case 'medium':
                navigator.vibrate(25);
                break;
            case 'heavy':
                navigator.vibrate(50);
                break;
            case 'success':
                navigator.vibrate([100, 50, 100]);
                break;
            case 'error':
                navigator.vibrate([200, 100, 200, 100, 200]);
                break;
            case 'warning':
                navigator.vibrate([150, 75, 150]);
                break;
        }
    } catch (e) {
        console.warn('振动反馈失败:', e);
    }
}

// 显示警告信息（增强移动端体验）
function showAlert(message, type = 'info', duration = 8000) {
    // 移除现有的警告
    const existingAlerts = document.querySelectorAll('.alert-dismissible');
    existingAlerts.forEach(alert => alert.remove());
    
    // 创建新警告
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 插入到页面顶部
    const container = document.querySelector('.main-container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    // 移动端触摸反馈
    if (isMobile) {
        switch(type) {
            case 'success':
                triggerHapticFeedback('success');
                break;
            case 'danger':
            case 'error':
                triggerHapticFeedback('error');
                break;
            case 'warning':
                triggerHapticFeedback('warning');
                break;
            default:
                triggerHapticFeedback('light');
        }
    }
    
    // 自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, duration);
}

// 页面跳转函数
function navigateTo(page, params = {}) {
    const url = new URL(page, window.location.origin);
    
    // 添加参数
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
            url.searchParams.set(key, params[key]);
        }
    });
    
    // 触摸反馈
    triggerHapticFeedback('light');
    
    // 跳转
    window.location.href = url.toString();
}

// 获取URL参数
function getUrlParams() {
    const params = {};
    const urlParams = new URLSearchParams(window.location.search);
    for (const [key, value] of urlParams) {
        params[key] = value;
    }
    return params;
}

// 检查系统状态
async function checkSystemStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();
        
        const statusElement = document.getElementById('systemStatus');
        if (!statusElement) return data;
        
        if (data.success && data.status.system_ready) {
            statusElement.className = 'alert alert-success alert-custom';
            statusElement.innerHTML = `
                <i class="fas fa-check-circle me-2"></i>
                系统就绪 | 可用TTS引擎: ${data.status.tts_engines.join(', ')}
            `;
        } else {
            statusElement.className = 'alert alert-warning alert-custom';
            statusElement.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                系统部分功能不可用，请检查配置
            `;
        }
        
        return data;
    } catch (error) {
        const statusElement = document.getElementById('systemStatus');
        if (statusElement) {
            statusElement.className = 'alert alert-danger alert-custom';
            statusElement.innerHTML = `
                <i class="fas fa-times-circle me-2"></i>
                无法连接到服务器
            `;
        }
        return { success: false, error: error.message };
    }
}

// 屏幕方向变化处理
if (screen.orientation) {
    screen.orientation.addEventListener('change', function() {
        const newOrientation = screen.orientation.angle === 0 || screen.orientation.angle === 180 ? 'portrait' : 'landscape';
        if (newOrientation !== deviceOrientation) {
            deviceOrientation = newOrientation;
            console.log('📱 屏幕方向改变:', deviceOrientation);
            
            // 触摸反馈
            triggerHapticFeedback('light');
            
            // 可以在这里添加方向变化的特殊处理
            if (deviceOrientation === 'landscape') {
                // 横屏时的处理
                document.body.classList.add('landscape-mode');
                document.body.classList.remove('portrait-mode');
            } else {
                // 竖屏时的处理
                document.body.classList.add('portrait-mode');
                document.body.classList.remove('landscape-mode');
            }
        }
    });
}

// 页面加载完成后的通用初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 通用模块初始化...');
    
    // 初始化移动端检测
    initMobileDetection();
    
    // 添加移动端特殊CSS类
    if (isMobile) {
        // 初始方向类
        document.body.classList.add(deviceOrientation === 'landscape' ? 'landscape-mode' : 'portrait-mode');
    }
    
    // 为所有按钮添加触摸反馈
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn') || e.target.closest('.btn')) {
            triggerHapticFeedback('light');
        }
    });
    
    console.log('✓ 通用模块初始化完成');
});

// 导出全局函数
window.initMobileDetection = initMobileDetection;
window.triggerHapticFeedback = triggerHapticFeedback;
window.showAlert = showAlert;
window.navigateTo = navigateTo;
window.getUrlParams = getUrlParams;
window.checkSystemStatus = checkSystemStatus;
