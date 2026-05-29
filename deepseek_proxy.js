// Proxy: Codex (Responses API) → DeepSeek (Chat Completions)
// Codex sends POST /responses expecting SSE stream
// We translate to DeepSeek Chat Completions, then wrap response in SSE stream
const http = require('http');
const https = require('https');

const TARGET = 'https://api.deepseek.com/v1/chat/completions';
const API_KEY = 'sk-707a90a4206b45e9962d606d7a6434f3';
const PORT = 15800;

function translateRequest(rawBody) {
    const req = JSON.parse(rawBody);
    const model = req.model || 'deepseek-v4-pro';
    const maxTokens = req.max_output_tokens || 16000;

    const messages = [];
    const instructions = req.instructions;
    if (instructions) messages.push({ role: 'system', content: String(instructions) });

    const input = req.input;
    if (typeof input === 'string') {
        messages.push({ role: 'user', content: input });
    } else if (Array.isArray(input)) {
        for (const item of input) {
            if (typeof item === 'string') {
                messages.push({ role: 'user', content: item });
            } else if (item && typeof item === 'object') {
                let role = item.role || 'user';
                // Map unsupported roles
                const validRoles = ['system', 'user', 'assistant', 'tool'];
                if (!validRoles.includes(role)) {
                    role = (role === 'developer') ? 'system' : 'user';
                }
                let content = item.content;
                if (Array.isArray(content)) {
                    content = content.map(c => c.text || c.content || '').join('\n');
                }
                if (content) messages.push({ role, content: String(content) });
            }
        }
    }

    return { model, messages, max_tokens: maxTokens, stream: false };
}

function doRequest(ccReq) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify(ccReq);
        const url = new URL(TARGET);
        const opts = {
            hostname: url.hostname, port: 443, path: url.pathname, method: 'POST',
            headers: {
                'Authorization': `Bearer ${API_KEY}`,
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            },
            timeout: 180000
        };
        const upstream = https.request(opts, upstreamRes => {
            let data = '';
            upstreamRes.on('data', chunk => data += chunk);
            upstreamRes.on('end', () => {
                try { resolve(JSON.parse(data)); }
                catch (e) { reject(new Error('Parse error: ' + e.message)); }
            });
        });
        upstream.on('error', e => reject(e));
        upstream.on('timeout', () => { upstream.destroy(); reject(new Error('timeout')); });
        upstream.write(postData);
        upstream.end();
    });
}

const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST,GET,OPTIONS');

    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }
    if (req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok' }));
        return;
    }
    if (req.method !== 'POST') { res.writeHead(405); res.end(); return; }

    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
        const preview = body.length > 200 ? body.substring(0, 200) + '...' : body;
        console.log(`[${new Date().toISOString()}] POST ${req.url} | ${preview}`);

        let ccReq;
        try { ccReq = translateRequest(body); }
        catch (e) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: { message: e.message } }));
            return;
        }

        const respId = 'resp_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);

        try {
            const ccResp = await doRequest(ccReq);
            console.log(`[${new Date().toISOString()}] Upstream raw: ${JSON.stringify(ccResp).substring(0, 300)}`);
            const choice = (ccResp.choices || [{}])[0];
            const msg = choice.message || {};
            let fullText = msg.content || '';
            if (!fullText) fullText = msg.reasoning_content || '';

            // SSE headers
            res.writeHead(200, {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            });

            // event: response.created
            const created = {
                type: 'response.created',
                response: {
                    id: respId, object: 'response', model: ccResp.model || 'deepseek-v4-pro',
                    status: 'in_progress', output: []
                }
            };
            res.write(`event: response.created\ndata: ${JSON.stringify(created)}\n\n`);

            if (fullText) {
                const itemId = 'msg_' + respId;
                const partId = 'part_' + respId;

                // event: response.output_item.added
                const itemAdded = {
                    type: 'response.output_item.added',
                    output_index: 0,
                    item: {
                        id: itemId,
                        type: 'message',
                        role: 'assistant',
                        status: 'in_progress',
                        content: []
                    }
                };
                res.write(`event: response.output_item.added\ndata: ${JSON.stringify(itemAdded)}\n\n`);

                // event: response.content_part.added
                const partAdded = {
                    type: 'response.content_part.added',
                    item_id: itemId,
                    output_index: 0,
                    content_index: 0,
                    part: {
                        type: 'output_text',
                        text: ''
                    }
                };
                res.write(`event: response.content_part.added\ndata: ${JSON.stringify(partAdded)}\n\n`);

                // event: response.output_text.delta
                const delta = {
                    type: 'response.output_text.delta',
                    item_id: itemId,
                    output_index: 0,
                    content_index: 0,
                    delta: fullText
                };
                res.write(`event: response.output_text.delta\ndata: ${JSON.stringify(delta)}\n\n`);

                // event: response.output_text.done
                const textDone = {
                    type: 'response.output_text.done',
                    item_id: itemId,
                    output_index: 0,
                    content_index: 0,
                    text: fullText
                };
                res.write(`event: response.output_text.done\ndata: ${JSON.stringify(textDone)}\n\n`);

                // event: response.content_part.done
                const partDone = {
                    type: 'response.content_part.done',
                    item_id: itemId,
                    output_index: 0,
                    content_index: 0,
                    part: {
                        type: 'output_text',
                        text: fullText
                    }
                };
                res.write(`event: response.content_part.done\ndata: ${JSON.stringify(partDone)}\n\n`);

                // event: response.output_item.done
                const itemDone = {
                    type: 'response.output_item.done',
                    output_index: 0,
                    item: {
                        id: itemId,
                        type: 'message',
                        role: 'assistant',
                        status: 'completed',
                        content: [{ type: 'output_text', text: fullText }]
                    }
                };
                res.write(`event: response.output_item.done\ndata: ${JSON.stringify(itemDone)}\n\n`);
            }

            // event: response.completed
            const done = {
                type: 'response.completed',
                response: {
                    id: respId, object: 'response', model: ccResp.model || 'deepseek-v4-pro',
                    status: 'completed',
                    output: fullText ? [{
                        id: 'msg_' + respId,
                        type: 'message',
                        role: 'assistant',
                        status: 'completed',
                        content: [{ type: 'output_text', text: fullText }]
                    }] : [],
                    usage: {
                        input_tokens: (ccResp.usage || {}).prompt_tokens || 0,
                        output_tokens: (ccResp.usage || {}).completion_tokens || 0,
                        total_tokens: (ccResp.usage || {}).total_tokens || 0
                    }
                }
            };
            res.write(`event: response.completed\ndata: ${JSON.stringify(done)}\n\n`);
            res.end();

        } catch (e) {
            console.error(`[PROXY ERROR] ${e.message}`);
            res.writeHead(200, { 'Content-Type': 'text/event-stream' });
            const errEvt = JSON.stringify({
                type: 'error',
                error: { message: 'Upstream error: ' + e.message }
            });
            res.write(`event: error\ndata: ${errEvt}\n\n`);
            res.end();
        }
    });
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`DeepSeek proxy: http://127.0.0.1:${PORT} → ${TARGET}`);
});
