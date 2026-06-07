#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音采集 + 阿里云百炼ASR + 匹配引擎 = 端到端语音报告
"""
import json, re, os, sys, io, tempfile, wave, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ===== 导入匹配引擎 =====
from voice_matcher import match, generate

# ===== 读取API配置 =====
import dotenv
dotenv.load_dotenv('E:/claude/.env')
API_KEY = os.getenv('DASHSCOPE_API_KEY')
VOCAB_ID = os.getenv('DASHSCOPE_VOCABULARY_ID')
if not API_KEY:
    print('错误: 未配置 DASHSCOPE_API_KEY')
    sys.exit(1)

from dashscope.audio.asr import Transcription, Recognition

# ===== 录音（使用pyaudio） =====
RECORD_SECONDS = 8  # 默认录音时长
SAMPLE_RATE = 16000

def record_audio(duration=RECORD_SECONDS, filename=None):
    """从麦克风录音，返回音频文件路径"""
    try:
        import pyaudio
    except ImportError:
        print('需要安装 pyaudio: pip install pyaudio')
        print('Windows 可用: pip install pipwin && pipwin install pyaudio')
        sys.exit(1)

    if not filename:
        filename = tempfile.mktemp(suffix='.wav')

    print(f'🎤 请说话（录音{duration}秒）...', end='', flush=True)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE,
                    input=True, frames_per_buffer=1024)

    frames = []
    for _ in range(0, int(SAMPLE_RATE / 1024 * duration)):
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream(); stream.close(); p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(1); wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(SAMPLE_RATE); wf.writeframes(b''.join(frames)); wf.close()

    print(' 完成')
    return filename


# ===== ASR识别 =====
def recognize(audio_file):
    """调用阿里云百炼ASR（录音文件）"""
    print(f'  ASR识别中...', end='', flush=True)
    try:
        result = Transcription.asr(
            api_key=API_KEY,
            model='paraformer-v2',
            audio_url=None,
            audio_data=open(audio_file, 'rb').read(),
            sample_rate=SAMPLE_RATE,
            vocabulary_id=VOCAB_ID or None,
        )
        print(' 完成')
        return result.get_output().get_text() if result else None
    except Exception as e:
        print(f'\n  ASR失败: {e}')
        return None


def recognize_stream(audio_file):
    """实时流式识别（一边说话一边出结果）"""
    print('  ASR流式识别中...')
    results = []
    try:
        recognition = Recognition(
            model='paraformer-v2',
            format='pcm',
            sample_rate=SAMPLE_RATE,
            vocabulary_id=VOCAB_ID or None,
            callback=lambda evt: results.append(evt.get_text()) if evt.get_text() else None
        )
        recognition.start()
        with open(audio_file, 'rb') as f:
            while True:
                chunk = f.read(3200)
                if not chunk: break
                recognition.send_audio(chunk)
                time.sleep(0.01)
        recognition.stop()
    except Exception as e:
        print(f'  流式ASR失败: {e}')
        return None

    return ''.join(results) if results else None


# ===== 朗读确认 =====
def speak(text):
    """用系统TTS朗读（Windows）"""
    try:
        import win32com.client
        speaker = win32com.client.Dispatch('SAPI.SpVoice')
        speaker.Speak(text)
    except:
        print(f'  [TTS] {text[:60]}')


# ===== 主流程 =====
def voice_report_flow(record_seconds=8, stream_mode=False):
    """完整的语音报告流程"""
    print('\n' + '='*60)
    print('超声语音报告系统')
    print('='*60)

    # 1. 录音
    audio_file = record_audio(record_seconds)

    # 2. ASR识别
    if stream_mode:
        text = recognize_stream(audio_file)
    else:
        text = recognize(audio_file)

    if not text:
        print('未识别到语音')
        return

    print(f'\n📝 识别结果: {text}')
    print()

    # 3. 匹配引擎
    top5, locked = match(text)
    print('TOP5 匹配:')
    for i, m in enumerate(top5[:5], 1):
        print(f'  #{i}  {m["score"]*100:.0f}%  rid={m["rid"]}  {m["discname"]}')

    # 4. 自动锁定
    if locked:
        report = generate(locked)
        print(f'\n✅ 自动锁定: {report["discname"]}')
        print(f'   诊断分组: {report["discgroup"]}')
        print(f'   诊断提示: {report["tpl_hint"]}')
        print(f'   随访建议: {report["suggestion"]}')
        print(f'   置信度:   {report["confidence"]*100:.0f}%')

        # 朗读确认
        speak(f'已锁定{report["discname"]}，诊断提示{report["tpl_hint"][:30]}')
    else:
        print(f'\n⏳ 未锁定(最高{top5[0]["score"]*100:.0f}%)，请重新说')
        speak(f'未锁定，最高匹配{top5[0]["discname"]}')

    # 清理临时文件
    try: os.remove(audio_file)
    except: pass

    return text, top5, locked, generate(locked) if locked else None


# ===== 命令行模式 =====
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='超声语音报告系统')
    parser.add_argument('--seconds', type=int, default=8, help='录音时长(秒)')
    parser.add_argument('--stream', action='store_true', help='流式模式')
    args = parser.parse_args()

    voice_report_flow(args.seconds, args.stream)
