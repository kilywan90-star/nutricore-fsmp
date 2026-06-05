const https = require('https');

const BACKEND = '47.109.151.238';
const PORT = 443;

const server = require('http').createServer((req, res) => {
    const opts = {
        hostname: BACKEND,
        port: PORT,
        path: req.url,
        method: req.method,
        headers: { ...req.headers, host: BACKEND },
        rejectUnauthorized: false
    };

    if (req.method === 'OPTIONS') {
        res.writeHead(200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': '*',
            'Content-Disposition': 'inline'
        });
        res.end();
        return;
    }

    const proxy = https.request(opts, (upstream) => {
        const h = {};
        for (const [k, v] of Object.entries(upstream.headers)) {
            if (k.toLowerCase() !== 'content-disposition') {
                h[k] = v;
            }
        }
        h['access-control-allow-origin'] = '*';
        h['content-disposition'] = 'inline';
        res.writeHead(upstream.statusCode, h);
        upstream.pipe(res);
    });

    proxy.on('error', (e) => {
        res.writeHead(502, { 'Content-Disposition': 'inline' });
        res.end('Proxy error: ' + e.message);
    });

    req.pipe(proxy);
});

server.listen(9000, () => console.log('proxy ready'));
