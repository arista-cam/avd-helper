#!/bin/bash

# Check the operating system
. /etc/os-release
if [[ "$ID" != "ubuntu" && "$ID" != "debian" && "$ID" != "linuxmint" ]]; then
    echo "Sorry, this script only supports Ubuntu, Debian, and Linux Mint."
    exit 1
fi

install_docker() {
    echo "Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    if [ "$ID" = "debian" ]; then
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    elif [ "$ID" = "ubuntu" ]; then
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    elif [ "$ID" = "linuxmint" ]; then
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $UBUNTU_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null    
    else
        echo "Unsupported OS: $ID"
        exit 1
    fi
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo docker --version
}

install_containerlab() {
    echo "Installing Containerlab..."
    sudo bash -c "$(curl -sL https://get.containerlab.dev)"
    containerlab version
}

install_python() {
    echo "Installing Python..."
    sudo apt-get update
    sudo apt-get install -y python3
}

install_pip() {
    echo "Installing pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    sudo python3 get-pip.py --break-system-packages
    rm get-pip.py
}

install_ansible() {
    echo "Installing Ansible..."
    sudo python3 -m pip install ansible-core --break-system-packages
}

install_avd_collection() {
    echo "Installing Arista AVD Collection..."
    sudo ansible-galaxy collection install arista.avd
}

install_pyavd() {
    echo "Installing Arista PyAVD Collection..."
    sudo python3 -m pip install pyavd --break-system-packages
}

install_cvprac() {
    echo "Installing CVPRAC..."
    sudo python3 -m pip install cvprac --break-system-packages
}

install_requests() {
    echo "Installing Requests..."
    sudo python3 -m pip install requests --break-system-packages
}

install_docker_py() {
    echo "Installing Docker-Py..."
    sudo python3 -m pip install docker --break-system-packages
}

install_paramiko() {
    echo "Installing Paramiko..."
    sudo python3 -m pip install paramiko --break-system-packages
}


[ "$DOCKER_REQUIRED" == "true" ] && install_docker
[ "$CONTAINERLAB_REQUIRED" == "true" ] && install_containerlab
[ "$PYTHON_REQUIRED" == "true" ] && install_python
[ "$PIP_REQUIRED" == "true" ] && install_pip
[ "$ANSIBLE_REQUIRED" == "true" ] && install_ansible
[ "$AVD_COLLECTION_REQUIRED" == "true" ] && install_avd_collection
[ "$PYAVD_REQUIRED" == "true" ] && install_pyavd
[ "$CVPRAC_REQUIRED" == "true" ] && install_cvprac
[ "$REQUESTS_REQUIRED" == "true" ] && install_requests
[ "$DOCKER_PY_REQUIRED" == "true" ] && install_docker_py
[ "$PARAMIKO_REQUIRED" == "true" ] && install_paramiko

if [ "$RESTART_SCRIPT" == "true" ]; then
    export INSTALL_SCRIPT_RUN=1
    echo "Restarting the Python script..."
    exec python3 avd_helper.py
else
    echo "Installation script completed."
    echo "You can now run the avd_helper.py script"
fi