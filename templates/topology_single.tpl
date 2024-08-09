name: avd

topology:
  kinds:
    ceos:
      startup-config: ./ceos.cfg
      image: {{ceos_image}}
      exec:
        - sleep 60
        - FastCli -p 15 -c 'security pki key generate rsa 4096 eAPI.key'
        - FastCli -p 15 -c 'security pki certificate generate self-signed eAPI.crt key eAPI.key generate rsa 4096 validity 30000 parameters common-name eAPI'
    linux:
      image: alpine-host
  nodes:
    dc1-spine1:
      kind: ceos
      mgmt-ipv4: 172.16.1.11
    dc1-spine2:
      kind: ceos
      mgmt-ipv4: 172.16.1.12
    dc1-leaf1a:
      kind: ceos
      mgmt-ipv4: 172.16.1.101
    dc1-leaf1b:
      kind: ceos
      mgmt-ipv4: 172.16.1.102
    dc1-leaf2a:
      kind: ceos
      mgmt-ipv4: 172.16.1.103
    dc1-leaf2b:
      kind: ceos
      mgmt-ipv4: 172.16.1.104
    dc1-client1:
      kind: linux
      mgmt-ipv4: 172.16.1.150
      env:
        TMODE: lacp
    dc1-client2:
      kind: linux
      mgmt-ipv4: 172.16.1.151
      env:
        TMODE: lacp

  links:
    - endpoints: ["dc1-leaf1a:eth1", "dc1-spine1:eth1"]
    - endpoints: ["dc1-leaf1b:eth1", "dc1-spine1:eth2"]
    - endpoints: ["dc1-leaf2a:eth1", "dc1-spine1:eth3"]
    - endpoints: ["dc1-leaf2b:eth1", "dc1-spine1:eth4"]
    - endpoints: ["dc1-leaf1a:eth2", "dc1-spine2:eth1"]
    - endpoints: ["dc1-leaf1b:eth2", "dc1-spine2:eth2"]
    - endpoints: ["dc1-leaf2a:eth2", "dc1-spine2:eth3"]
    - endpoints: ["dc1-leaf2b:eth2", "dc1-spine2:eth4"]
    - endpoints: ["dc1-leaf1a:eth3", "dc1-leaf1b:eth3"]
    - endpoints: ["dc1-leaf1a:eth4", "dc1-leaf1b:eth4"]
    - endpoints: ["dc1-leaf2a:eth3", "dc1-leaf2b:eth3"]
    - endpoints: ["dc1-leaf2a:eth4", "dc1-leaf2b:eth4"]
    - endpoints: ["dc1-leaf1a:eth5", "dc1-client1:eth1"]
    - endpoints: ["dc1-leaf1b:eth5", "dc1-client1:eth2"]
    - endpoints: ["dc1-leaf2a:eth5", "dc1-client2:eth1"]
    - endpoints: ["dc1-leaf2b:eth5", "dc1-client2:eth2"]

mgmt:
  network: ceos_clab                
  ipv4-subnet: 172.16.1.0/24