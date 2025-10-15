#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共振峰功能测试脚本
测试共振峰检测和可视化功能是否正常工作
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def test_formant_feature():
    """测试共振峰功能"""
    
    print("=" * 60)
    print("共振峰功能测试")
    print("=" * 60)
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--use-fake-ui-for-media-stream')  # 自动允许麦克风
    chrome_options.add_argument('--use-fake-device-for-media-stream')
    
    print("\n1. 启动浏览器...")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 访问频谱镜子页面
        url = "http://localhost:5000/spectrogram-mirror"
        print(f"2. 访问页面: {url}")
        driver.get(url)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 10)
        
        # 检查页面标题
        print("3. 检查页面标题...")
        assert "频谱镜子" in driver.title
        print("   ✓ 页面标题正确")
        
        # 检查共振峰开关是否存在
        print("4. 检查共振峰控制开关...")
        formant_toggle = wait.until(
            EC.presence_of_element_located((By.ID, "formant-toggle"))
        )
        assert formant_toggle is not None
        print("   ✓ 共振峰开关存在")
        
        # 检查开关默认状态
        is_checked = formant_toggle.is_selected()
        print(f"   ✓ 开关默认状态: {'已勾选' if is_checked else '未勾选'}")
        assert is_checked, "共振峰开关应该默认勾选"
        
        # 检查共振峰说明信息
        print("5. 检查共振峰说明信息...")
        formant_info = driver.find_element(By.ID, "formant-info")
        assert formant_info is not None
        print("   ✓ 共振峰说明信息存在")
        
        # 检查F1-F4说明
        info_text = formant_info.text
        for formant_name in ["F1", "F2", "F3", "F4"]:
            assert formant_name in info_text, f"{formant_name} 说明缺失"
        print("   ✓ F1-F4 说明完整")
        
        # 检查开始监测按钮
        print("6. 检查开始监测按钮...")
        start_btn = driver.find_element(By.ID, "start-monitoring")
        assert start_btn is not None
        print("   ✓ 开始监测按钮存在")
        
        # 测试开关切换
        print("7. 测试共振峰开关切换...")
        formant_toggle.click()
        time.sleep(0.5)
        assert not formant_toggle.is_selected(), "开关应该被取消勾选"
        print("   ✓ 取消勾选成功")
        
        formant_toggle.click()
        time.sleep(0.5)
        assert formant_toggle.is_selected(), "开关应该被重新勾选"
        print("   ✓ 重新勾选成功")
        
        # 检查Canvas
        print("8. 检查频谱图Canvas...")
        canvas = driver.find_element(By.ID, "spectrogram-canvas")
        assert canvas is not None
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        print(f"   ✓ Canvas尺寸: {width}x{height}")
        
        # 检查JavaScript是否加载
        print("9. 检查JavaScript加载...")
        js_check = driver.execute_script(
            "return typeof RealtimeSpectrogramRenderer !== 'undefined'"
        )
        assert js_check, "RealtimeSpectrogramRenderer类未加载"
        print("   ✓ RealtimeSpectrogramRenderer已加载")
        
        # 检查共振峰方法是否存在
        print("10. 检查共振峰相关方法...")
        has_detect_method = driver.execute_script("""
            return typeof RealtimeSpectrogramRenderer.prototype.detectFormants === 'function';
        """)
        assert has_detect_method, "detectFormants方法不存在"
        print("   ✓ detectFormants方法存在")
        
        has_draw_method = driver.execute_script("""
            return typeof RealtimeSpectrogramRenderer.prototype.drawFormants === 'function';
        """)
        assert has_draw_method, "drawFormants方法不存在"
        print("   ✓ drawFormants方法存在")
        
        has_toggle_method = driver.execute_script("""
            return typeof RealtimeSpectrogramRenderer.prototype.toggleFormants === 'function';
        """)
        assert has_toggle_method, "toggleFormants方法不存在"
        print("   ✓ toggleFormants方法存在")
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！共振峰功能正常工作")
        print("=" * 60)
        
        # 暂停以便查看
        print("\n浏览器将在5秒后关闭...")
        time.sleep(5)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 保存截图
        screenshot_path = "test_formant_error.png"
        driver.save_screenshot(screenshot_path)
        print(f"\n已保存错误截图: {screenshot_path}")
        
        return False
        
    finally:
        driver.quit()

if __name__ == "__main__":
    # 检查服务器是否运行
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:5000", timeout=2)
    except:
        print("错误: Flask服务器未运行")
        print("请先运行: python app.py")
        sys.exit(1)
    
    # 运行测试
    success = test_formant_feature()
    sys.exit(0 if success else 1)

