---
dc1:
  children:
    CVP:
      hosts:
        {{cvp_ip}}:
    dc1_fabric:
      children:
        dc1_spines:
          hosts:
            s1-spine1:
              ansible_host: 172.16.100.2
            s1-spine2:
              ansible_host: 172.16.100.3
        dc1_leafs:
          hosts:
            s1-leaf1:
              ansible_host: 172.16.100.4
            s1-leaf2:
              ansible_host: 172.16.100.5
            s1-leaf3:
              ansible_host: 172.16.100.6
            s1-leaf4:
              ansible_host: 172.16.100.7
    dc1_fabric_services:
      children:
        dc1_spines:
        dc1_leafs:
    dc1_fabric_ports:
      children:
        dc1_spines:
        dc1_leafs:


