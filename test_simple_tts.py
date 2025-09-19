#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试简单的TTS调用
"""
import dashscope
from dashscope.audio.tts import SpeechSynthesizer

def test_simple_tts():
    """测试最简单的TTS调用"""
    
    # 设置API密钥
    api_key = "sk-26cd7fe2661444f2804896a590bdbbc0"
    dashscope.api_key = api_key
    
    print("=== 测试简单TTS ===")
    
    # 测试不同的模型和声音组合
    test_configs = [
        {
            'model': 'sambert-zhichu-v1',
            'voice': 'zhichu',
            'text': '你好'
        },
        {
            'model': 'sambert-zhimiao-v1', 
            'voice': 'zhimiao',
            'text': '你好'
        },
        {
            'model': 'cosyvoice-v1',
            'voice': 'longwan',
            'text': '你好'
        },
        {
            'model': 'cosyvoice-v1',
            'voice': 'longxiaochun',
            'text': '你好'
        }
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n--- 测试配置 {i}: {config['model']} + {config['voice']} ---")
        try:
            result = SpeechSynthesizer.call(
                model=config['model'],
                text=config['text'],
                voice=config['voice'],
                format='mp3'
            )
            
            if result.get_response().status_code == 200:
                print(f"✅ 成功: {config['model']} + {config['voice']}")
                
                # 保存音频文件
                filename = f"test_{config['model'].replace('-', '_')}_{config['voice']}.mp3"
                with open(filename, 'wb') as f:
                    f.write(result.get_audio_data())
                print(f"✅ 音频文件保存: {filename}")
                return True, config
                
            else:
                print(f"❌ 失败: 状态码 {result.get_response().status_code}")
                print(f"   错误信息: {result.get_response().message}")
                
        except Exception as e:
            print(f"❌ 异常: {e}")
    
    return False, None

if __name__ == "__main__":
    success, working_config = test_simple_tts()
    
    if success:
        print(f"\n🎉 找到可用配置: {working_config}")
    else:
        print("\n😞 所有配置都失败了")
