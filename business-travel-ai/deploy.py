"""Deploy business-travel-ai to server"""
import paramiko
import os
import stat

HOST = "47.109.151.238"
USER = "root"
PASS = "sql2k8!WF"
REMOTE_DIR = "/opt/business-travel-ai"
LOCAL_DIR = r"E:\qoder\business-travel-ai"

# Files/dirs to upload
UPLOAD = [
    ".next",
    "src",
    "package.json",
    "package-lock.json",
    "next.config.ts",
    "drizzle.config.ts",
    "tsconfig.json",
]

# Files/dirs to skip inside src
SKIP_DIRS = {"__tests__", "node_modules", ".git"}

def should_skip(name):
    return name in SKIP_DIRS or name.startswith(".")

def upload_dir(sftp, local_path, remote_path):
    try:
        sftp.stat(remote_path)
    except FileNotFoundError:
        sftp.mkdir(remote_path)

    for item in os.listdir(local_path):
        if should_skip(item):
            continue
        local_item = os.path.join(local_path, item)
        remote_item = remote_path + "/" + item
        if os.path.isdir(local_item):
            upload_dir(sftp, local_item, remote_item)
        else:
            sftp.put(local_item, remote_item)

def main():
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=15)
    sftp = ssh.open_sftp()
    print("Connected.")

    # Ensure remote dir exists
    try:
        sftp.stat(REMOTE_DIR)
    except FileNotFoundError:
        sftp.mkdir(REMOTE_DIR)

    for item in UPLOAD:
        local_path = os.path.join(LOCAL_DIR, item)
        remote_path = REMOTE_DIR + "/" + item

        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {item}")
            continue

        if os.path.isdir(local_path):
            print(f"  Uploading dir: {item}/")
            upload_dir(sftp, local_path, remote_path)
        else:
            print(f"  Uploading file: {item}")
            sftp.put(local_path, remote_path)

    sftp.close()
    print("Upload complete.")

    # Run npm install on server
    print("Running npm install on server...")
    stdin, stdout, stderr = ssh.exec_command(
        f"cd {REMOTE_DIR} && npm install --production 2>&1",
        timeout=120
    )
    output = stdout.read().decode()
    print(output[-500:] if len(output) > 500 else output)

    # Restart service - try common patterns
    print("Restarting service...")
    cmds = [
        # Try pm2
        f"cd {REMOTE_DIR} && pm2 restart business-travel-ai 2>&1 || pm2 restart all 2>&1",
        # Try systemd
        f"systemctl restart business-travel-ai 2>&1",
        # Try killing node process and restarting
        f"pkill -f 'next start.*{REMOTE_DIR}' 2>/dev/null; cd {REMOTE_DIR} && nohup npx next start -p 3001 > /tmp/travel-ai.log 2>&1 &",
    ]

    for cmd in cmds:
        print(f"  Trying: {cmd[:60]}...")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if out:
            print(f"  stdout: {out}")
        if err:
            print(f"  stderr: {err}")
        if stdout.channel.recv_exit_status() == 0:
            print("  Success!")
            break

    ssh.close()
    print("Deploy complete!")

if __name__ == "__main__":
    main()
