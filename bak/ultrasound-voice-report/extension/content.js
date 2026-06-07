(function() {
    const sidebar = document.createElement('div');
    sidebar.id = 'ai-voice-sidebar';
    sidebar.innerHTML = `
        <div style="position:fixed; top:20px; right:20px; width:220px; background:#fff; box-shadow:0 4px 12px rgba(0,0,0,0.15); border-radius:8px; padding:15px; z-index:99999; font-family:sans-serif;">
            <h3 style="margin:0 0 10px 0; font-size:14px; color:#333;">超声语音助手</h3>
            <div id="part-display" style="font-size:12px; color:#666; margin-bottom:10px; background:#f5f5f5; padding:5px; border-radius:4px;">检测部位: 未知</div>
            <button id="record-btn" style="width:100%; padding:10px; background:#007bff; color:#fff; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">开始录音</button>
            <div id="status-log" style="margin-top:10px; font-size:11px; color:#999; max-height:60px; overflow-y:auto;">系统就绪</div>
        </div>
    `;
    document.body.appendChild(sidebar);

    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let currentPart = "breast";

    const examItemEl = document.getElementById('exam_item');
    if (examItemEl) {
        const text = examItemEl.innerText;
        if (text.includes("肝胆")) {
            currentPart = "abdominal";
            document.getElementById('part-display').innerText = "检测部位: 腹部(肝胆)";
        } else if (text.includes("乳腺")) {
            currentPart = "breast";
            document.getElementById('part-display').innerText = "检测部位: 乳腺";
        }
    }

    const recordBtn = document.getElementById('record-btn');
    const logDiv = document.getElementById('status-log');

    recordBtn.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
                mediaRecorder.onstop = async () => {
                    logDiv.innerText = "发送AI处理中...";
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

                    const formData = new FormData();
                    formData.append('audio', audioBlob, 'voice.wav');

                    try {
                        const response = await fetch(`http://127.0.0.1:8000/api/v1/analyze-voice?exam_part=${currentPart}`, {
                            method: 'POST',
                            body: formData
                        });
                        const resData = await response.json();
                        if (resData.is_valid && resData.extracted_slots) {
                            logDiv.innerText = "解析成功，原生注入中!";
                            Object.keys(resData.extracted_slots).forEach(key => {
                                const inputEl = document.getElementById(`input_${key}`);
                                if (inputEl) {
                                    inputEl.value = resData.extracted_slots[key];
                                    inputEl.style.backgroundColor = '#fff3cd';
                                    setTimeout(() => inputEl.style.backgroundColor = '', 1500);
                                }
                            });
                        } else {
                            logDiv.innerText = "数据过滤或解析失败";
                        }
                    } catch (err) {
                        logDiv.innerText = "通信失败: " + err.message;
                    }
                };

                mediaRecorder.start();
                isRecording = true;
                recordBtn.innerText = "停止录音";
                recordBtn.style.background = "#dc3545";
                logDiv.innerText = "正在录音...";
            } catch (err) {
                logDiv.innerText = "麦克风权限拒绝: " + err.message;
            }
        } else {
            mediaRecorder.stop();
            isRecording = false;
            recordBtn.innerText = "开始录音";
            recordBtn.style.background = "#007bff";
        }
    });
})();
