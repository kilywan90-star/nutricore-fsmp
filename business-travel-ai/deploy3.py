import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko
import os

LOCAL = r'E:\qoder\business-travel-ai'
REMOTE = '/opt/business-travel-ai'
SKIP = {'__tests__', 'node_modules', '.git', 'data'}

def should_skip(n):
    return n in SKIP or n.startswith('.') and n not in ('.next',)

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

# Restart with env
print('Restarting PM2...')
stdin, stdout, stderr = ssh.exec_command(
    'pm2 delete business-travel-ai 2>&1; '
    f'cd {REMOTE} && pm2 start ecosystem.config.js --update-env 2>&1 && '
    'pm2 save 2>&1',
    timeout=30
)
out = stdout.read().decode('utf-8', errors='replace')
print(out.encode('ascii', errors='replace').decode('ascii'))

ssh.close()
print('Deploy done!')
