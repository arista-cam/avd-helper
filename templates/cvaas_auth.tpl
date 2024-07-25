ansible_host: {{cvp_ip}}
ansible_user: cvaas

ansible_password: {{cvp_token}}
ansible_connection: httpapi
ansible_network_os: eos
ansible_httpapi_use_ssl: True
ansible_httpapi_validate_certs: {{cvp_certs}}
ansible_httpapi_port: 443