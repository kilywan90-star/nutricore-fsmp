/**
 * Node.js 网关层
 * 处理微信小程序专用协议：登录鉴权、支付签名
 * 其余业务请求透传到 Python FastAPI 后端
 */
require('dotenv').config({ path: '../.env' });
const express = require('express');
const axios = require('axios');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');

const app = express();
app.use(express.json());

const PORT = process.env.GATEWAY_PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const JWT_SECRET = process.env.JWT_SECRET || 'bid-generator-secret-change-in-production';

// 微信小程序配置
const WECHAT_APPID = process.env.WECHAT_APPID || '';
const WECHAT_SECRET = process.env.WECHAT_SECRET || '';
const WECHAT_MCHID = process.env.WECHAT_MCHID || '';
const WECHAT_API_V3_KEY = process.env.WECHAT_API_V3_KEY || '';

// ── 全局限流 ──────────────────────────────────────
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 分钟
  max: 100,
  message: { error: '请求过于频繁，请稍后再试' }
});
app.use('/api/', limiter);

// ── 微信登录 ──────────────────────────────────────

app.post('/api/auth/wechat-login', async (req, res) => {
  try {
    const { code, nickname, avatar_url } = req.body;

    if (!code) {
      return res.status(400).json({ error: '缺少登录凭证 code' });
    }

    // 调用微信接口获取 openid
    let openid, session_key;

    if (!WECHAT_APPID || !WECHAT_SECRET) {
      // 开发环境 mock
      console.warn('[DEV] 微信未配置，使用 mock openid');
      openid = `dev_${crypto.createHash('md5').update(code).digest('hex').slice(0, 16)}`;
      session_key = 'dev_session_key';
    } else {
      const wxResp = await axios.get('https://api.weixin.qq.com/sns/jscode2session', {
        params: { appid: WECHAT_APPID, secret: WECHAT_SECRET, js_code: code, grant_type: 'authorization_code' }
      });
      if (wxResp.data.errcode) {
        return res.status(400).json({ error: `微信登录失败: ${wxResp.data.errmsg}` });
      }
      openid = wxResp.data.openid;
      session_key = wxResp.data.session_key;
    }

    // 转发到 Python 后端处理用户创建/查询
    const backendResp = await axios.post(`${BACKEND_URL}/api/auth/login/wechat`, {
      code, nickname, avatar_url
    }, {
      headers: { 'X-Internal-Openid': openid, 'X-Internal-Session-Key': session_key }
    });

    res.json(backendResp.data);

  } catch (err) {
    console.error('登录失败:', err.message);
    res.status(500).json({ error: '登录服务异常' });
  }
});

// ── JWT 验证中间件 ──────────────────────────────

function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: '未登录' });
  }
  try {
    const token = authHeader.slice(7);
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (err) {
    return res.status(401).json({ error: '登录已过期，请重新登录' });
  }
}

// ── 代理：将认证请求透传到 Python 后端 ─────────────

app.all('/api/*', async (req, res) => {
  try {
    // 跳过已在网关层处理的路由
    if (req.path === '/api/auth/wechat-login') return;

    const headers = { ...req.headers };
    delete headers.host;
    delete headers['content-length'];

    // 如果用户已认证，将 user_id 传给后端
    if (req.user) {
      headers['X-User-Id'] = String(req.user.user_id);
      headers['X-User-Openid'] = req.user.openid;
    }

    const backendResp = await axios({
      method: req.method,
      url: `${BACKEND_URL}${req.path}`,
      params: req.query,
      data: req.body,
      headers,
      responseType: 'stream',
      timeout: 120000, // 2 分钟超时（AI 生成可能较慢）
    });

    // 透传 SSE 流式响应
    if (backendResp.headers['content-type']?.includes('text/event-stream')) {
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no');
      backendResp.data.pipe(res);
    } else {
      res.setHeader('Content-Type', backendResp.headers['content-type'] || 'application/json');
      backendResp.data.pipe(res);
    }

  } catch (err) {
    if (err.response) {
      res.status(err.response.status);
      err.response.data.pipe(res);
    } else {
      console.error('代理请求失败:', err.message);
      res.status(502).json({ error: '后端服务不可用' });
    }
  }
});

// ── 健康检查 ──────────────────────────────────────

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'bid-generator-gateway', version: '1.0.0' });
});

// ── 启动 ──────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`[Gateway] 运行在 http://localhost:${PORT}`);
  console.log(`[Gateway] 后端地址: ${BACKEND_URL}`);
  console.log(`[Gateway] 微信配置: ${WECHAT_APPID ? '已配置' : '未配置 (开发模式)'}`);
});
