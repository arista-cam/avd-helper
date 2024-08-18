# Arista ContainerLab AVD Deployment

## Disclaimer!
I'll start by saying that I am not a developer, nor do I resemble anything close to a developer.
The code you will find in this repository is most likely offensive to developers everywhere and for that I apologise.

# Exec Summary
This 'code' is designed to use AVD to deploy a Spine/Leaf topology via CVP using ContainerLab devices.
Features include:
- Automatically install all dependencies (docker, containerlab, pip, avd, etc...)
- Automatically deploy containerlab toplogies
- Automatic provisioning into On-Prem CVP or CVaaS
- Automatic creation of management configlets
- Automatically runs both Build and Deploy playbooks
- View Ansible output from Build and Deploy playbooks after they have run
- Host AVD generated documentation with apache container
- Client 'servers' attached to topology for testing (iPerf3/tcpdump/scapy)

# Requirements
In order for arista-avd-clab to work, it requires the following:
 - A Supported OS (Debian, Ubuntu or Linux Mint)
 - [Docker](https://docker.com)
 - [ContainerLab](https://containerlab.dev/)
 - [Python 3.10.0+](https://www.python.org/)
 - [Python-pip](https://pypi.org/project/pip/)
 - [Ansible](https://ansible.com)
 - [AVD](https;//avd.sh)
 - A supported cEOS image (cEOS-4.28.0F and above)

The script will automatically install any missing dependencies
All thats require to get started is git and python

## Python Modules Used
I have utilised three external python modules in this script:
- [cvPrac](https://github.com/aristanetworks/cvprac) - Which is a RESTful API client for Cloudvision® Portal (CVP) which can be used for building applications that work with Arista CVP
- [requests](https://pypi.org/project/requests/) - The python HTTP library
- [docker](https://pypi.org/project/docker/) - The Python Docker library
- [paramiko](https://www.paramiko.org/) - The Python SSH library

# On-Prem CloudVision Setup
In order to use CVP with ContainerLab, the CVP host needs a static route configured back to the management range you have configured.
When configuring CVP, I used the same interface for both the Cluster Interface and the Device Interface.
After CVP is up and running, add a static route using the `ip route add 172.16.1.0 via {DOCKER HOST IP} dev eth0` command.
The default range used for this deployment is 172.16.1.0/24

### CloudVision Setup Diagram
[![cvp_route_configuration](https://github.com/user-attachments/assets/ddb68966-bc01-4fa2-b3c3-e443622bc7d3)](https://github.com/user-attachments/assets/ddb68966-bc01-4fa2-b3c3-e443622bc7d3)


## User Guide
For more infomation see the [Wiki](https://github.com/CameronPrior/avd-helper/wiki)
