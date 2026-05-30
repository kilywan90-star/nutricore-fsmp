// bridge.js — Native ↔ H5 communication utilities for WebView pages

const app = getApp();

/**
 * Post a message from mini-program to the H5 page inside a WebView.
 * The H5 page must listen for `message` events on `window`.
 *
 * Usage (mini-program side):
 *   postToH5(webviewContext, { type: 'navigate', path: '/patient/risk' });
 *
 * Usage (H5 side):
 *   window.addEventListener('message', (e) => { ... });
 */
function postToH5(webviewContext, data) {
  if (!webviewContext) return;
  webviewContext.postMessage({ data });
}

/**
 * Build a URL for a WebView page, attaching the JWT token as a query parameter.
 *
 * @param {string} path — the H5 route, e.g. '/patient/coach'
 * @returns {string} full URL with token appended
 */
function buildWebViewUrl(path) {
  const baseUrl = app.globalData.baseUrl;
  const token = app.globalData.token || '';
  const separator = path.includes('?') ? '&' : '?';
  return `${baseUrl}${path}${separator}token=${encodeURIComponent(token)}`;
}

/**
 * Handle messages received from an H5 WebView.
 * The H5 side sends messages via wx.miniProgram.postMessage({ data }).
 *
 * Supported message types:
 *   { type: 'navigate', path: '/patient/risk' } — navigate inside WebView
 *   { type: 'subscribeReminder', templateId: '...' } — request subscription
 *   { type: 'getToken' } — request the current JWT token
 */
function handleH5Message(e, webviewContext) {
  const messages = e.detail?.data || [];
  for (const msg of messages) {
    switch (msg.type) {
      case 'navigate':
        // The WebView will handle navigation internally; we forward the path
        if (webviewContext && msg.path) {
          const url = buildWebViewUrl(msg.path);
          webviewContext.loadURL({ url });
        }
        break;

      case 'subscribeReminder':
        wx.requestSubscribeMessage({
          tmplIds: [msg.templateId || 'medication_reminder'],
          success: (res) => {
            postToH5(webviewContext, {
              type: 'subscribeResult',
              templateId: msg.templateId,
              result: res,
            });
          },
          fail: (err) => {
            postToH5(webviewContext, {
              type: 'subscribeResult',
              templateId: msg.templateId,
              error: err.errMsg,
            });
          },
        });
        break;

      case 'getToken':
        postToH5(webviewContext, {
          type: 'token',
          token: app.globalData.token,
        });
        break;

      default:
        console.log('Unhandled H5 message type:', msg.type);
    }
  }
}

module.exports = {
  postToH5,
  buildWebViewUrl,
  handleH5Message,
};
