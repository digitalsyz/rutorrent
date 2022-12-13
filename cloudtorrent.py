import subprocess


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


print(
    f"""
{bcolors.BOLD}{bcolors.HEADER}{bcolors.UNDERLINE}
Cloudtorrent Script.\n
{bcolors.ENDC}
"""
)
# parimatch.i9.ar
# datadome.i9.ar
# apidatadome.i9.ar
inp = input("START >>>")
domain = input("\nIp or domain: ")
domain = domain.strip()

print(
    f"""
-----------------------------------------------------------------------------
{bcolors.WARNING} Process baslady sabyrly bolyn...{bcolors.ENDC}
-----------------------------------------------------------------------------
"""
)
subprocess.run(
    ["apt-get update -y && apt-get upgrade -y && apt install docker.io -y"],
    shell=True,
)

subprocess.run(
    [
        "docker run --name cy -d -p 63000:63000 --restart always -v /root/downloads:/downloads jpillora/cloud-torrent --port 63000"
    ],
    # stdout=subprocess.PIPE,
    shell=True,
)
subprocess.run(
    [
        "apt install python3-pip python3-dev libpq-dev postgresql python3-virtualenv postgresql-contrib nginx curl python3-venv -y"
    ],
    # stdout=subprocess.PIPE,
    shell=True,
)
subprocess.run(
    ["git clone https://github.com/batyok32/autoupload.git"],
    # stdout=subprocess.PIPE,
    shell=True,
)
subprocess.run(
    [
        "cd /root/ && python3 -m venv env && source /root/env/bin/activate && cd autoupload/ && pip install -r requirements.txt && pip install django gunicorn && python manage.py collectstatic && python manage.py migrate"
    ],
    # stdout=subprocess.PIPE,
    shell=True,
)

f = open("/etc/systemd/system/gunicorn.socket", "w")
f.write(
    f"""
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
"""
)
f.close()


f = open("/etc/systemd/system/gunicorn.service", "w")
f.write(
    """
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/root/autoupload
ExecStart=/root/env/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
"""
)
f.close()

subprocess.run(
    [
        f"systemctl start gunicorn.socket && systemctl enable gunicorn.socket && systemctl status gunicorn.socket && file /run/gunicorn.sock && systemctl start gunicorn.service"
    ],
    shell=True,
)

f = open("/etc/nginx/sites-available/default", "w")
f.write(
    f"""
server {{
    listen 80;
    server_name {domain};

    location = /favicon.ico {{ access_log off; log_not_found off; }}

    location /static {{
        autoindex on;
        alias /root/autoupload/static; 
    }}

    location /media {{
        autoindex on;
        alias /root/autoupload/media; 
    }}

    location /cloud/ {{
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:63000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}

    location / {{
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }}
}}
"""
)
f.close()

subprocess.run(
    [f"nginx -t && systemctl restart nginx"],
    shell=True,
)

subprocess.run(
    [f"apt install redis-server -y && systemctl status redis"],
    shell=True,
)


f = open("/etc/default/celeryd", "w")
f.write(
    f"""
#  Names of nodes to start
# most people will only start one node:
CELERYD_NODES = "worker1"
# Absolute or relative path to the 'celery' command:
CELERY_BIN = "/root/env/bin/celery"
# App instance to use
CELERY_APP = "config"
# How to call manage.py
CELERYD_MULTI = "multi"
# Extra command-line arguments to the worker
CELERYD_OPTS = "--time-limit=300 --concurrency=8"
# Set logging level to DEBUG
CELERYD_LOG_LEVEL = "DEBUG"
# %n will be replaced with the first part of the nodename.
CELERYD_LOG_FILE = "/var/log/celery/%n%I.log"
CELERYD_PID_FILE = "/var/run/celery/%n.pid"
CELERYBEAT_PID_FILE = "/var/run/celery/beat.pid"
CELERYBEAT_LOG_FILE = "/var/log/celery/beat.log"
# Workers should run as an unprivileged user.
# You need to create this user manually (or you can choose
# a user/group combination that already exists (e.g., nobody).
CELERYD_USER = "root"
CELERYD_GROUP = "root"
# If enabled pid and log directories will be created if missing,
# and owned by the userid/group configured.
CELERY_CREATE_DIRS = 1
"""
)
f.close()


subprocess.run(
    [
        f"mkdir -p /var/log/celery/ && mkdir -p /var/run/celery/ && chown -R root:root /var/log/celery/ && chown -R root:root /var/run/celery/"
    ],
    shell=True,
)

f = open("/etc/systemd/system/celery.service", "w")
f.write(
    """
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=root
Group=root

EnvironmentFile=/etc/default/celeryd
WorkingDirectory=/root/autoupload
ExecStart=/root/env/bin/celery multi start ${CELERYD_NODES} \
  -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
  --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}
ExecStop=/root/env/bin/celery ${CELERY_BIN} multi stopwait ${CELERYD_NODES} \
  --pidfile=${CELERYD_PID_FILE}
ExecReload=/root/env/bin/celery ${CELERY_BIN} multi restart ${CELERYD_NODES} \
  -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
  --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}

[Install]
WantedBy=multi-user.target
"""
)
f.close()

subprocess.run(
    [
        f"systemctl daemon-reload && systemctl enable celery && systemctl restart celery && systemctl status celery "
    ],
    shell=True,
)

# DJANGO VIEWS
# Read in the file
with open("/root/autoupload/main/views.py", "r") as file:
    filedata = file.read()

# Replace the target string
filedata = filedata.replace(
    'directory = "/home/batyr/Загрузки/"', 'directory = "/root/downloads/"'
)

# Write the file out again
with open("/root/autoupload/main/views.py", "w") as file:
    file.write(filedata)

subprocess.run(
    [
        f"systemctl restart gunicorn.service && systemctl restart gunicorn.socket && systemctl restart nginx && systemctl daemon-reload && systemctl restart celery"
    ],
    shell=True,
)

subprocess.run(
    [f"apt-get install rclone && rclone config"],
    shell=True,
)


print(f"\n\n{bcolors.OKGREEN}Process gutardy!{bcolors.ENDC}")
print(f"\n\nBOLDY WEBSITE TAYYAR - http://{domain}:63000")
