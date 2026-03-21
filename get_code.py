import subprocess
import sys

process = subprocess.Popen(
    'az login --tenant 9c10867c-ca41-4ab6-a9f0-639e50b6ba33 --use-device-code',
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

with open('code5.txt', 'w') as f:
    for line in iter(process.stdout.readline, ''):
        f.write(line)
        f.flush()
        if "login.microsoft.com/device" in line or "https://microsoft.com/devicelogin" in line:
            break
