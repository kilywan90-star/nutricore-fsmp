import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import os

LOCAL = r'E:\qoder\business-travel-ai'
REMOTE = '/opt/business-travel-ai'
SKIP = {'__tests__', 'node_modules', '.git', 'data'}

def should_skip(n):
    return n in SKIP or n.startswith('.')

def upload_dir(sftp, lp, rp):
    try: sftp.stat(rp)
    except: sftp.mkdir(rp)
    for item in os.listdir(lp):
        if should_skip(item): continue
        li = os.path.join(lp, item); ri = rp + '/' + item
        if os.path.isdir(li): upload_dir(sftp, li, ri)
        else: sftp.put(li, ri)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.109.151.238', username='root', password='sql2k8!WF', timeout=15)
sftp = ssh.open_sftp()
print('Uploading...')

for item in ['.next', 'src', 'package.json', 'package-lock.json', 'next.config.ts', 'drizzle.config.ts', 'tsconfig.json']:
    lp = os.path.join(LOCAL, item)
    if not os.path.exists(lp): continue
    if os.path.isdir(lp):
        print(f'  {item}/')
        upload_dir(sftp, lp, REMOTE + '/' + item)
    else:
        print(f'  {item}')
        sftp.put(lp, REMOTE + '/' + item)

sftp.close()
print('Upload done.')

# Write ecosystem config with DeepSeek API key
eco = """module.exports = {
  apps: [{
    name: "business-travel-ai",
    script: "node_modules/next/dist/bin/next",
    args: "start -p 3001",
    cwd: "/opt/business-travel-ai",
    env: {
      NODE_ENV: "production",
      LLM_API_KEY: "sk-675bd28875d1498bbd7069d4fdd63c95",
      PORT: "3001"
    }
  }]
};
"""
cmd = f"cat > {REMOTE}/ecosystem.config.js << 'ENDOFSCRIPT'\n{eco}ENDOFSCRIPT"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
print('Ecosystem config written.')

# Verify
stdin, stdout, stderr = ssh.exec_command(f'cat {REMOTE}/ecosystem.config.js', timeout=15)
print('Config:', stdout.read().decode('utf-8', errors='replace'))

# Restart
stdin, stdout, stderr = ssh.exec_command(
    'pm2 delete business-travel-ai 2>&1; '
    f'cd {REMOTE} && pm2 start ecosystem.config.js 2>&1 && '
    'pm2 save 2>&1',
    timeout=30
)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print('Deploy done!')
