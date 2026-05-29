"""
Tiny proxy that translates OpenAI Responses API to Chat Completions API.
Codex → this proxy (port 15800) → DeepSeek
"""
import json, sys, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TARGET = "https://api.deepseek.com/v1/chat/completions"
API_KEY = "sk-707a90a4206b45e9962d606d7a6434f3"
PORT = 15800

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # silent

    def do_POST(self):
        # Read incoming request
        body_len = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(body_len)
        try:
            req = json.loads(raw)
        except:
            self._error(400, "Invalid JSON"); return

        # Debug: log first 500 chars of request
        print(f"[PROXY] {self.path} | {json.dumps(req, ensure_ascii=False)[:500]}")

        # Translate Responses API → Chat Completions
        model = req.get("model", "deepseek-v4-pro")
        max_tokens = req.get("max_output_tokens", 4096)

        # Handle system instructions and input
        messages = []
        instructions = req.get("instructions")
        if instructions:
            messages.append({"role": "system", "content": str(instructions)})

        user_input = req.get("input", "")
        # input can be: string, list of messages, or list of content parts
        if isinstance(user_input, str):
            messages.append({"role": "user", "content": user_input})
        elif isinstance(user_input, list):
            for item in user_input:
                # Item can be a message object with role/content
                if isinstance(item, dict):
                    role = item.get("role", "user")
                    content = item.get("content", "")
                    if isinstance(content, list):
                        # Content can be list of parts (e.g. [{"type":"input_text","text":"..."}])
                        text_parts = []
                        for c in content:
                            if isinstance(c, dict):
                                t = c.get("text", "") or c.get("content", "") or str(c)
                                text_parts.append(t)
                            else:
                                text_parts.append(str(c))
                        content = "\n".join(text_parts)
                    elif not isinstance(content, str):
                        content = str(content)
                    messages.append({"role": role, "content": content})
                elif isinstance(item, str):
                    messages.append({"role": "user", "content": item})

        # Handle conversation history if present
        previous = req.get("previous_response_id")
        if previous:
            # We don't have the history, but this is a continuation
            pass

        # Handle tools (Codex may send tool definitions)
        tools = req.get("tools")
        tool_choice = req.get("tool_choice")

        # Build Chat Completions request
        cc_req = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if tools:
            # Map Responses API tools to Chat Completions tools
            cc_tools = []
            for t in tools:
                if isinstance(t, dict) and t.get("type") == "function":
                    cc_tools.append({"type": "function", "function": t})
                elif isinstance(t, dict):
                    cc_tools.append(t)
            if cc_tools:
                cc_req["tools"] = cc_tools
        if tool_choice:
            cc_req["tool_choice"] = tool_choice

        # Forward to DeepSeek
        try:
            data = json.dumps(cc_req, ensure_ascii=False).encode('utf-8')
            r = Request(TARGET, data=data, headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            })
            resp = urlopen(r, timeout=120)
            cc_resp = json.loads(resp.read())
        except HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            print(f"[PROXY] Upstream {e.code}: {err_body[:300]}")
            self._error(e.code, f"Upstream error: {e.reason}"); return
        except URLError as e:
            self._error(502, f"Upstream unreachable: {e.reason}"); return

        # Translate Chat Completions response → Responses API format
        choice = cc_resp.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        if not content:
            content = msg.get("reasoning_content", "")

        output_parts = []
        if content:
            output_parts.append({"type": "output_text", "text": content})

        # Handle tool calls in response
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            fn = tc.get("function", {})
            output_parts.append({
                "type": "function_call",
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", ""),
            })

        responses_reply = {
            "id": cc_resp.get("id", "resp_unknown"),
            "object": "response",
            "model": cc_resp.get("model", model),
            "output": output_parts,
            "usage": {
                "input_tokens": cc_resp.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": cc_resp.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": cc_resp.get("usage", {}).get("total_tokens", 0),
            },
        }

        if choice.get("finish_reason"):
            responses_reply["status"] = "completed"

        self._json(200, responses_reply)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        else:
            self._json(200, {"endpoint": "DeepSeek proxy", "target": TARGET})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        self._json(code, {"error": {"message": msg, "type": "proxy_error"}})

if __name__ == "__main__":
    print(f"DeepSeek proxy: http://127.0.0.1:{PORT} → {TARGET}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
