- name: Configuration deployment
  hosts: FABRIC
  connection: local
  gather_facts: false
  tasks:
    - name: Deploy configurations and tags to CloudVision
      ansible.builtin.import_role:
        name: arista.avd.cv_deploy
      vars:
        cv_server: {{cvp_ip}}
        cv_token: {{cvp_token}}
        cv_submit_workspace: true
        cv_run_change_control: true
        cv_verify_certs: {{cvp_certs}}