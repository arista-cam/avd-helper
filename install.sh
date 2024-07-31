#!/bin/bash

# Check the operating system
. /etc/os-release
if [[ "$ID" != "ubuntu" && "$ID" != "debian" && "$ID" != "linuxmint" ]]; then
    echo "Sorry, this script only supports Ubuntu, Debian, and Linux Mint."
    exit 1
fi

install_docker() {
    echo "Installing Docker..."
    # Update the package index
    sudo apt-get update

    # Install required packages
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker’s official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Check if OS is Debian or Ubuntu and add the appropriate repository
    . /etc/os-release
    if [ "$ID" = "debian" ]; then
        echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
        $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    elif [ "$ID" = "ubuntu" ]; then
        echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $VERSION_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    elif [ "$ID" = "linuxmint" ]; then
        echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $UBUNTU_CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null    
    else
        echo "Unsupported OS: $ID"
        exit 1
    fi

    # Update the package index again
    sudo apt-get update

    # Install Docker Engine
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io

    # Verify the Docker installation
    sudo docker --version
}

install_containerlab() {
    echo "Installing Containerlab..."
    # Install Containerlab
    sudo bash -c "$(curl -sL https://get.containerlab.dev)"
    
    # Verify the Containerlab installation
    containerlab version
}

install_python() {
    echo "Installing Python..."
    # Install Python
    sudo apt-get update
    sudo apt-get install -y python3
}

install_pip() {
    echo "Installing pip..."
    # Install pip using get-pip.py with --break-system-packages switch
    curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    sudo python3 get-pip.py --break-system-packages
    rm get-pip.py
}

install_ansible() {
    echo "Installing Ansible..."
    # Install Ansible using pip with --break-system-packages switch
    sudo python3 -m pip install ansible-core --break-system-packages
}

install_avd_collection() {
    echo "Installing Arista AVD Collection..."
    # Install Arista AVD Collection
    sudo ansible-galaxy collection install arista.avd
}

install_pyavd() {
    echo "Installing Arista PyAVD Collection..."
    sudo python3 -m pip install pyavd --break-system-packages
}

install_other_dependencies() {
    echo "Installing other dependencies..."
    sudo apt install -y python3-netaddr

    # Install dependencies from requirements.txt
    if [ -f requirements.txt ]; then
        sudo pip3 install -r requirements.txt --break-system-packages
    else
        echo "requirements.txt not found. Skipping dependency installation."
    fi
}

if [ "$DOCKER_REQUIRED" == "true" ]; then
    install_docker
fi

if [ "$CONTAINERLAB_REQUIRED" == "true" ]; then
    install_containerlab
fi

if [ "$PYTHON_REQUIRED" == "true" ]; then
    install_python
fi

if [ "$PIP_REQUIRED" == "true" ]; then
    install_pip
fi

if [ "$ANSIBLE_REQUIRED" == "true" ]; then
    install_ansible
fi

if [ "$AVD_COLLECTION_REQUIRED" == "true" ]; then
    install_avd_collection
fi

if [ "$PYAVD_REQUIRED" == "true" ]; then
    install_pyavd
fi

if [ "$CVPRAC_REQUIRED" == "true" ] || [ "$REQUESTS_REQUIRED" == "true" ] || [ "$DOCKER_PY_REQUIRED" == "true" ] || [ "$PARAMIKO_REQUIRED" == "true" ]; then
    install_other_dependencies
fi

if [ "$RESTART_SCRIPT" == "true" ]; then
    export INSTALL_SCRIPT_RUN=1
    # Restart the Python script
    exec sudo python3 avd_helper.py
else
    echo "Installation script completed."
    echo "You can now run the avd_helper.py script"
fi