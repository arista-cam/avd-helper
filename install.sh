#!/bin/bash

# Function to check if Docker is installed
check_docker_installed() {
    if command -v docker &> /dev/null
    then
        echo "Docker is already installed. Version: $(docker --version)"
        return 0
    else
        return 1
    fi
}

# Function to check if Containerlab is installed
check_containerlab_installed() {
    if command -v containerlab &> /dev/null
    then
        echo "Containerlab is already installed. Version: $(containerlab version | grep -oP 'containerlab version \K.*')"
        return 0
    else
        return 1
    fi
}

# Function to check if Python is installed
check_python_installed() {
    if command -v python3 &> /dev/null
    then
        echo "Python is already installed. Version: $(python3 --version)"
        return 0
    else
        return 1
    fi
}

# Function to check if pip is installed
check_pip_installed() {
    if command -v pip3 &> /dev/null
    then
        echo "pip is already installed. Version: $(pip3 --version)"
        return 0
    else
        return 1
    fi
}

# Function to check if Ansible is installed
check_ansible_installed() {
    if command -v ansible &> /dev/null
    then
        echo "Ansible is already installed. Version: $(ansible --version | head -n 1)"
        return 0
    else
        return 1
    fi
}
# Function to check if Ansible AVD collection is installed
check_avd_installed() {
    if sudo ansible-galaxy collection list | grep 'arista.avd'; then
        echo "Arista AVD Collection is already installed."
        return 0
    else
        return 1
    fi
}

# Check if Docker is already installed
if check_docker_installed; then
    echo "Skipping Docker installation."
else
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
fi

# Check if Containerlab is already installed
if check_containerlab_installed; then
    echo "Skipping Containerlab installation."
else
    # Install Containerlab
    sudo bash -c "$(curl -sL https://get.containerlab.dev)"
    
    # Verify the Containerlab installation
    containerlab version
fi

# Check if Python is already installed
if check_python_installed; then
    echo "Skipping Python installation."
else
    # Install Python
    sudo apt-get update
    sudo apt-get install -y python3
fi

# Check if pip is already installed
if check_pip_installed; then
    echo "Skipping pip installation."
else
    # Install pip using get-pip.py with --break-system-packages switch
    curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    sudo python3 get-pip.py --break-system-packages
    rm get-pip.py
fi

# Check if Ansible is already installed
if check_ansible_installed; then
    echo "Skipping Ansible installation."
else
    # Install Ansible using pip with --break-system-packages switch
    sudo python3 -m pip install ansible-core --break-system-packages

fi

# Check if Arista AVD Collection is already installed
if check_avd_installed; then
    echo "Skipping Arista AVD Collection installation."
else
    # Install Arista AVD Collection
    sudo ansible-galaxy collection install arista.avd
fi

sudo python3 -m pip install pyavd --break-system-packages
sudo apt install -y python3-netaddr

# Install dependencies from requirements.txt
if [ -f requirements.txt ]; then
    sudo pip3 install -r requirements.txt --break-system-packages
else
    echo "requirements.txt not found. Skipping dependency installation."
fi


echo "Installation script completed."