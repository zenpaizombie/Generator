#!/bin/bash

echo ".____    .__       .__     __   
|    |   |__| ____ |  |___/  |_ 
|    |   |  |/ ___\|  |  \   __\
|    |___|  / /_/  >   Y  \  |  
|_______ \__\___  /|___|  /__|  
        \/ /_____/      \/      "

echo Make your own VPS Hosting, Dont Allow Mining!!

read -p "Are you sure you want to proceed? Agree to not allow mining (y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation aborted."
    exit 1
fi

cd ~

echo "Installing python3, pip and docker."
sudo apt update
sudo apt install python3 pip docker docker-compose -y
echo Installed successfully

echo "Writing Dockerfile..."
cat <<EOF > Dockerfile
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y tmate curl sudo neofetch openssh-server openssh-client && \
    sed -i 's/^#\?\s*PermitRootLogin\s\+.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    echo 'root:root' | chpasswd && \
    printf '#!/bin/sh\nexit 0' > /usr/sbin/policy-rc.d && \
    apt-get install -y systemd systemd-sysv dbus dbus-user-session && \
    printf "systemctl start systemd-logind" >> /etc/profile 

CMD ["bash"]
ENTRYPOINT ["/sbin/init"]
EOF

echo Made successfully - Building Docker image.
echo "Building Docker Image"
sudo docker build -t ubuntu-22.04-with-tmate -f Dockerfile .
echo Built successfully
echo "Downloading main.py from the GitHub repository..."
wget -O main.py https://raw.githubusercontent.com/zenpaizombie/Generator/refs/heads/main/main.py
wget https://raw.githubusercontent.com/zenpaizombie/Generator/refs/heads/main/servers.txt
echo Downloaded successfully
echo "Installing Python packages: discord and docker..."
pip install discord.py docker
echo "Bot Token:"
read -r TOKEN
echo "Updating main.py with the provided token..."
sed -i "s/TOKEN = ''/TOKEN = 'TOKEN'/" main.py
echo "Starting the Discord bot..."
echo "To start the bot in the future, run: python3 main.py"
python3 main.py
