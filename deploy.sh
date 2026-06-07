server {
    listen 80;
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/nginx/ssl/ultrasound.crt;
    ssl_certificate_key /etc/nginx/ssl/ultrasound.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # 主服务（前端 + API）
    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /v1/ {
        proxy_pass http://127.0.0.1:8800;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2?)$ {
        proxy_pass http://127.0.0.1:9999;
        expires 7d;
    }
}
