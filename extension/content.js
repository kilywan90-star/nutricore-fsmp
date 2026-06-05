(function() {
    /* ============================================================
       Streaming Ultrasound Voice Assistant — Chrome Extension
       WebSocket + Web Speech API + Real-time DOM injection
       ============================================================ */

    /* ---------- Sidebar UI ---------- */
    const sidebar = document.createElement('div');
    sidebar.id = 'ai-voice-sidebar';
    sidebar.innerHTML = `
        <div id="ai-panel" style="
            position:fixed; top:20px; right:20px; width:260px;
            background:#fff; box-shadow:0 4px 16px rgba(0,0,0,0.12);
            border-radius:10px; padding:16px; z-index:99999;
            font-family: 'Segoe UI', system-ui, sans-serif; font-size:13px;
        ">
            <div style="font-size:15px; font-weight:700; color:#1a1a2e; margin-bottom:2px;">
                超声语音助手
            </div>
            <div style="font-size:10px; color:#888; margin-bottom:10px;">流式感知版 v2.0</div>

            <div id="ai-template-badge" style="
                font-size:12px; color:#555; margin-bottom:10px;
                background:#f0f4ff; padding:8px; border-radius:6px;
                text-align:center; min-height:18px;
            ">科室: 检测中...</div>

            <button id="ai-dictate-btn" style="
                width:100%; padding:12px; background:#2563eb; color:#fff;
                border:none; border-radius:8px; cursor:pointer;
                font-weight:600; font-size:14px; transition:background 0.2s;
            ">开始听写</button>

            <button id="ai-finish-btn" style="
                width:100%; padding:10px; margin-top:8px;
                background:#fff; color:#2563eb; border:1px solid #2563eb;
                border-radius:8px; cursor:pointer; font-weight:600; font-size:12px;
                display:none;
            ">停止并核对</button>

            <div id="ai-transcript-preview" style="
                margin-top:12px; padding:10px; background:#f9fafb;
                border-radius:6px; font-size:11px; color:#374151;
                min-height:40px; max-height:120px; overflow-y:auto;
                line-height:1.5; word-break:break-word;
            ">等待语音输入...</div>

            <div id="ai-status-log" style="
                margin-top:8px; font-size:10px; color:#9ca3af; line-height:1.4;
            ">系统就绪</div>
        </div>
    `;
    document.body.appendChild(sidebar);

    /* ---------- DOM refs ---------- */
    const dictateBtn = document.getElementById('ai-dictate-btn');
    const finishBtn  = document.getElementById('ai-finish-btn');
    const badge      = document.getElementById('ai-template-badge');
    const transcript = document.getElementById('ai-transcript-preview');
    const statusLog  = document.getElementById('ai-status-log');
    const panel      = document.getElementById('ai-panel');

    /* ---------- State ---------- */
    let ws = null;
    let recognition = null;
    let isDictating = false;
    let currentTemplate = null;
    let latestSlots = {};

    /* ---------- Helpers ---------- */
    function setStatus(msg) { statusLog.innerText = msg; }

    function highlightField(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.transition = 'background-color 0.3s ease';
        el.style.backgroundColor = '#dbeafe';
        setTimeout(function() { el.style.backgroundColor = ''; }, 2000);
    }

    function injectSlotsToPage(slots) {
        if (!slots) return;
        Object.keys(slots).forEach(function(key) {
            const el = document.getElementById('input_' + key);
            if (el) {
                el.value = slots[key] || '';
                el.style.transition = 'background-color 0.3s ease';
                el.style.backgroundColor = '#fef3c7';
                setTimeout(function() { el.style.backgroundColor = ''; }, 1200);
            }
        });
    }

    /* ---------- WebSocket ---------- */
    function connectWebSocket() {
        ws = new WebSocket('ws://127.0.0.1:8002/api/v1/stream-report');

        ws.onopen = function() {
            setStatus('WebSocket 已连接');
        };

        ws.onmessage = function(event) {
            var msg = JSON.parse(event.data);

            if (msg.type === 'INTENT_PENDING') {
                badge.innerText = msg.msg;
                badge.style.background = '#fef3c7';
            }

            if (msg.type === 'TEMPLATE_LOCKED') {
                currentTemplate = msg.template;
                badge.innerText = '已锁定模板: ' + msg.template;
                badge.style.background = '#d1fae5';
                badge.style.color = '#065f46';
                badge.style.fontWeight = '700';
                setStatus('模板已锁定 — 开始流式填充...');

                // Highlight the matching section on the page
                if (msg.template === 'breast') {
                    highlightField('input_left_breast_nodule');
                } else if (msg.template === 'abdominal') {
                    highlightField('input_liver_size');
                }
            }

            if (msg.type === 'SLOT_UPDATES') {
                latestSlots = msg.slots;
                injectSlotsToPage(msg.slots);
                setStatus('实时更新中...');
            }

            if (msg.type === 'FINAL_REVIEW') {
                finishBtn.style.display = 'none';
                dictateBtn.style.display = 'block';
                dictateBtn.innerText = '开始听写';
                dictateBtn.style.background = '#2563eb';
                isDictating = false;
                injectSlotsToPage(msg.slots);
                setStatus('审核完成: ' + (msg.review || ''));
                badge.innerText = '已完成 — ' + (msg.template || '');
                badge.style.background = '#e0e7ff';
            }

            if (msg.type === 'RESET') {
                currentTemplate = null;
                latestSlots = {};
                badge.innerText = '科室: 检测中...';
                badge.style.background = '#f0f4ff';
                badge.style.color = '#555';
                badge.style.fontWeight = 'normal';
            }

            if (msg.type === 'ERROR') {
                setStatus('错误: ' + (msg.msg || ''));
            }
        };

        ws.onclose = function() {
            setStatus('WebSocket 已断开');
            ws = null;
        };

        ws.onerror = function() {
            setStatus('WebSocket 连接失败');
        };
    }

    /* ---------- Web Speech API ---------- */
    function startDictation() {
        var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setStatus('当前浏览器不支持语音识别，请使用 Chrome');
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'zh-CN';
        recognition.continuous = true;
        recognition.interimResults = true;

        var finalTranscript = '';

        recognition.onresult = function(event) {
            var interimTranscript = '';
            for (var i = event.resultIndex; i < event.results.length; i++) {
                var result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript;
                } else {
                    interimTranscript += result[0].transcript;
                }
            }

            var displayText = finalTranscript + interimTranscript;
            transcript.innerText = displayText || '聆听中...';

            // Send the latest finalized text over WebSocket
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'text_update', text: finalTranscript }));
            }
        };

        recognition.onerror = function(event) {
            setStatus('语音识别错误: ' + event.error);
        };

        recognition.onend = function() {
            if (isDictating) {
                // Auto-restart for continuous dictation
                try { recognition.start(); } catch(e) {}
            }
        };

        recognition.start();
    }

    function stopDictation() {
        if (recognition) {
            recognition.onend = null; // prevent auto-restart
            recognition.stop();
            recognition = null;
        }
    }

    /* ---------- Button handlers ---------- */
    dictateBtn.addEventListener('click', function() {
        if (!isDictating) {
            // Start
            connectWebSocket();
            startDictation();
            isDictating = true;
            dictateBtn.innerText = '听写中...';
            dictateBtn.style.background = '#dc2626';
            finishBtn.style.display = 'block';
            setStatus('正在聆听...');
        }
    });

    finishBtn.addEventListener('click', function() {
        if (isDictating) {
            stopDictation();
            isDictating = false;
            dictateBtn.innerText = '正在提交...';
            dictateBtn.style.background = '#6b7280';
            finishBtn.style.display = 'none';

            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'finish' }));
            }
            setStatus('已停止，等待最终审核...');
        }
    });
})();
