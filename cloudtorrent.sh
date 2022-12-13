# !/bin/bash

# Update upgrade
function init {
    apt-get update -y && apt-get upgrade -y && apt install docker.io -y
    docker run --name cy -d -p 63000:63000 \
        --restart always \
        -v /root/downloads:/downloads \
        jpillora/cloud-torrent --port 63000
}

function python_init {
    apt install python3-pip python3-dev libpq-dev postgresql python3-virtualenv postgresql-contrib nginx curl git -y
    git clone https://github.com/batyok32/autoupload.git
    apt-get install python3-venv -y && python3 -m venv env && source env/bin/activate && cd autoupload/ && pip install -r requirements.txt && pip install django gunicorn && python manage.py collectstatic && python manage.py migrate
}

function gunicorn_init {
    touch /etc/systemd/system/gunicorn.socket
    cat << EOF >> /etc/systemd/system/gunicorn.socket
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
EOF  
    touch /etc/systemd/system/gunicorn.service
    cat << EOF >> /etc/systemd/system/gunicorn.service
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
EOF 
    systemctl start gunicorn.socket
    systemctl enable gunicorn.socket    
}

function check_status_gunicorn {
    systemctl status gunicorn.socket
    file /run/gunicorn.sock
}

function nginx_init {
    rm -rf /etc/nginx/sites-available/default 
    touch /etc/nginx/sites-available/default 
    read -p 'Ip: ' ip
    cat << EOF >> /etc/nginx/sites-available/default
server {
    listen 80;
    server_name $ip;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        autoindex on;
        alias /root/autoupload/static; 
    } 

    location /media/ {
        autoindex on;
        alias /root/autoupload/media; 
    } 

    location /cloud/ {
        include proxy_params;
        proxy_pass http://127.0.0.1:63000;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
EOF
    nginx -t
    systemctl restart nginx
}

function redis_init {
    apt install redis-server -y
    systemctl status redis
}

function celery_init {
    touch /etc/default/celeryd
    cat << EOF >> /etc/default/celeryd
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
EOF
    mkdir -p /var/log/celery/
    mkdir -p /var/run/celery/
    chown -R root:root /var/log/celery/
    chown -R root:root /var/run/celery/
    touch /etc/systemd/system/celery.service
    cat << EOF >> /etc/systemd/system/celery.service
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
EOF
    systemctl daemon-reload
    systemctl enable celery
    systemctl restart celery
    
}

function rclone_init {
    apt-get install -y rclone
    rclone config
}

function django_setup  {
    apt-get install -y nano
    nano main/views.py
}

function restart_everything {
    systemctl restart gunicorn.service
    systemctl restart gunicorn.socket
    systemctl restart nginx
    systemctl daemon-reload
    systemctl restart celery
}



function hello {
    cat << EOF
Hi What you want to do?
1. Install
2. Rclone Setup
3. Setup django
4. Restart everything
5. Exit
6.1.Nginx
7.1 Redis
8.1 Celery
EOF

}

while :
do 
    hello
    read -p 'Choose: ' choice
    if [[ "$choice" == "1" ]]; then
        echo "1. Install. Wait..."
        init
        python_init
        gunicorn_init
        # check_status_gunicorn
        
        echo "FINISHED"
    elif [[ "$choice" == "6" ]]; then
        nginx_init
    elif [[ "$choice" == "7" ]]; then
        redis_init
    elif [[ "$choice" == "8" ]]; then
        celery_init
    elif [[ "$choice" == "2" ]]; then
        rclone_init
    elif [[ "$choice" == "3" ]]; then
        django_setup
    elif [[ "$choice" == "4" ]]; then
        restart_everything
    elif [[ "$choice" == "5" ]]; then
        echo "Bye."
        break        
    fi
done