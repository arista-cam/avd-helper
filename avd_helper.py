import os
import ssl
import sys
import json
import time
import logging
import requests
import subprocess
import threading
import uuid
import datetime
from cvprac.cvp_client import CvpClient
from getpass import getpass
from pathlib import Path

# Disable SSL warnings and verification
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()

# Configure logging
logging.basicConfig(level=logging.CRITICAL, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().handlers = []
cvprac_logger = logging.getLogger('cvprac')
cvprac_logger.handlers = []
cvprac_logger.propagate = False

# Get the directory of the script
script_dir = Path(__file__).parent

class Info:
    def __init__(self, deploy_command, topology_file, destroy_command, build_log, deploy_log):
        self.deploy_command = deploy_command
        self.topology_file = topology_file
        self.destroy_command = destroy_command
        self.build_log = build_log
        self.deploy_log = deploy_log

def load_config(file_path):
    with open(file_path) as file:
        return json.load(file)

def clear_console():
    os.system("clear")

def subprocess_run(command):
    return subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def check_topology_running(topology_file):
    result = subprocess_run(f"clab inspect -t {topology_file}")
    return result.returncode == 0

def read_cvp_credentials():
    # Define the path to the .cvpcreds file
    creds_file = script_dir / '.cvpcreds'

    try:
        # Check if .cvpcreds file exists
        if not creds_file.exists():
            get_cvp_credentials()  # Initialize CVP credentials capture

        # Read the credentials from the file
        with open(creds_file, 'r') as file:
            lines = file.readlines()
        
        # Parse the credentials
        creds = {}
        for line in lines:
            key, value = line.strip().split('=')
            creds[key] = value

        cvp_ip = creds.get('cvp_ip')
        cvp_username = creds.get('cvp_username')
        cvp_password = creds.get('cvp_password')

        return cvp_ip,cvp_username, cvp_password

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None

def get_cvp_credentials():
    try:
        clear_console()
        # Define the file paths
        creds_file = script_dir / '.cvpcreds'

        print("----------------------------------------")
        print("CVP Server Information")
        print("----------------------------------------")
        print("")
        # Prompt the user for an IP address
        cvp_ip = input("Please enter the CVP IP address: ")

        # Prompt the user for the CVP username and password
        cvp_username = input("Please enter the CVP username: ")
        cvp_password = getpass("Please enter the CVP password: ")

        # Save the credentials in the .cvpcreds file
        with open(creds_file, 'w') as file:
            file.write(f"cvp_ip={cvp_ip}\n")
            file.write(f"cvp_username={cvp_username}\n")
            file.write(f"cvp_password={cvp_password}\n")

        # Restart the script from the beginning
        python = sys.executable
        os.execl(python, python, *sys.argv)

    except Exception as e:
        print(f"An error occurred: {e}")
        
def create_inventory(cvp_ip, cvp_username, cvp_password):
    try:

        # Define file paths using Pathlib
        template_inventory_file = script_dir / 'templates' / 'inventory.tpl'
        template_deploy_file = script_dir / 'templates' / 'deploy_dc1_cvp.tpl'
        template_ceos_file = script_dir / 'templates' / 'ceos.tpl'
        template_dc1_vars_file = script_dir / 'templates' / 'dc1.tpl'
        output_inventory_file = script_dir / 'sites' / 'dc1' / 'inventory.yml'
        output_deploy_file = script_dir / 'playbooks' / 'deploy_dc1_cvp.yml'
        output_ceos_file = script_dir / 'ceos.cfg'
        output_dc1_vars_file = script_dir / 'sites' / 'dc1' / 'group_vars' / 'dc1.yml'

        # Function to handle template processing and writing to output file
        def process_template(template_file, output_file, replacements):
            if output_file.exists():
                output_file.unlink()
            with open(template_file, 'r') as file:
                template_contents = file.read()
            for placeholder, value in replacements.items():
                template_contents = template_contents.replace(placeholder, value)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as file:
                file.write(template_contents)

        # Process inventory template
        process_template(template_inventory_file, output_inventory_file, {'{{cvp_ip}}': cvp_ip})

        # Process deploy template
        process_template(template_deploy_file, output_deploy_file, {'{{cvp_ip}}': cvp_ip})

        # Process ceos template
        process_template(template_ceos_file, output_ceos_file, {'{{cvp_username}}': cvp_username, '{{cvp_password}}': cvp_password, '{{cvp_ip}}': cvp_ip})

        # Process dc1_vars template
        process_template(template_dc1_vars_file, output_dc1_vars_file, {'{{cvp_username}}': cvp_username, '{{cvp_password}}': cvp_password})

    except FileNotFoundError as e:
        print(f"The file {e.filename} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")    



    except FileNotFoundError as e:
        print(f"The file {e.filename} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")


def animated_message(stop_event, message="Processing", delay=0.5):
    def animate():
        while not stop_event.is_set():
            for i in range(1, 5):
                if stop_event.is_set():
                    break
                sys.stdout.write(f"\r{message}{'.' * i}    ")
                sys.stdout.flush()
                time.sleep(delay)
        sys.stdout.write(f"\r{message} - Done\n")
    
    animation_thread = threading.Thread(target=animate)
    animation_thread.start()
    return animation_thread

def deploy_clab(info, cvp_ip, cvp_username, cvp_password):
    clear_console()
    cvp_client = CvpClient()
    cvp_client.connect([cvp_ip], cvp_username, cvp_password, 120, 120)
    print("----------------------------------------")
    print("Lab Deployment Information")
    print("----------------------------------------")
    print("")
    
    # Check if topology is already running
    if check_topology_running(info.topology_file):
        user_choice = input("A ContainerLab topology is already running. Do you want to continue and skip deployment? (y/n): ")
        if user_choice.lower() != 'y':
            print("Exiting script.")
            return
    else:
        # Deploying ContainerLab topology
        stop_animation = threading.Event()
        animation_thread = animated_message(stop_animation, "Deploying ContainerLab topology")
        try:
            subprocess_run(info.deploy_command)
        finally:
            stop_animation.set()
            animation_thread.join()
        logging.info("Done")

    lab_dir = script_dir / "clab-avd"
    parent_container = cvp_client.api.get_container_by_name("Undefined")

    # Read management IP list from file
    mgmt_ip_list_file = os.path.join(lab_dir, "topology-data.json")
    json_data = load_config(mgmt_ip_list_file)

    ip_list = [node["mgmt-ipv4-address"] for node in json_data["nodes"].values() if node.get("kind") == "ceos"]

    cvp_list = [{
        "device_ip": dev_ip,
        "parent_name": parent_container["name"],
        "parent_key": parent_container["key"],
    } for dev_ip in ip_list]

    # Add devices to CVP inventory
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Adding devices to CVP inventory")
    try:
        cvp_client.api.add_devices_to_inventory(cvp_list)
        time.sleep(10)  # Simulating a long-running task for demonstration
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")

    # Moving Devices to Lab Container
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Moving Devices to Lab Container")
    try:
        move_devices_to_container(cvp_client, "Tenant", "Tenant", "Undefined")
        time.sleep(60)
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")

    # Assigning Base Configlets in CVP
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Assigning Base Configlets in CVP")
    try:
        assign_configlets(cvp_client, "Tenant")
        time.sleep(2)
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Run the AVD Build Playbook
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Running Ansible Build Playbook")
    try:
        run_ansible_build()
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Run the AVD Deploy Playbook
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Running Ansible Deploy Playbook")
    try:
        run_ansible_deploy()
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Generate Topology Tags
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Generating Topology Tags")
    try:
        generate_topology_tags(cvp_client)
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    print("")
    print("")
    print("----------------------------------------")
    print("Lab Deployed Successfully")
    print("----------------------------------------")
    input("Press any key to return to the Main Menu")
    main()

def move_devices_to_container(cvp_client, parent_container_name, new_container_name, source_container_name):
    parent_container = cvp_client.api.get_container_by_name(parent_container_name)
    try:
        cvp_client.api.add_container(new_container_name, parent_container["name"], parent_container["key"])
    except Exception as e:
        if "jsonData already exists in jsonDatabase" in str(e):
            print("Container already exists, continuing...")

    device_list = [{"deviceName": device["fqdn"]} for device in cvp_client.api.get_devices_in_container(source_container_name)]
    
    for device in device_list:
        device_info = cvp_client.api.get_device_by_name(device["deviceName"])
        new_container = cvp_client.api.get_container_by_name(new_container_name)
        cvp_client.api.move_device_to_container("python", device_info, new_container)

    execute_pending_tasks(cvp_client)

def assign_configlets(cvp_client, container_name):
    cvp_devices = cvp_client.api.get_devices_in_container(container_name)
    device_info = [{"name": device["fqdn"], "macAddress": device["systemMacAddress"]} for device in cvp_devices]

    for info in device_info:
        device_mac = info["macAddress"]
        device_short_name = info["name"]
        dev_mgmt = f"{device_short_name}_management"
        
        get_config = cvp_client.api.get_device_configuration(device_mac)
        cvp_client.api.add_configlet(dev_mgmt, get_config)
        
        device_name = cvp_client.api.get_device_by_name(device_short_name)
        mgmt_configlet = cvp_client.api.get_configlet_by_name(dev_mgmt)
        mgmt_configlet_key = [{"name": mgmt_configlet["name"], "key": mgmt_configlet["key"]}]
        
        cvp_client.api.apply_configlets_to_device("Management Configs", device_name, mgmt_configlet_key)
        
        execute_pending_tasks(cvp_client)

def execute_pending_tasks(cvp_client):
    tasks = cvp_client.api.get_tasks_by_status("Pending")
    for task in tasks:
        cvp_client.api.execute_task(task["workOrderId"])

def run_ansible_build():
    playbook = script_dir / "playbooks/build_dc1.yml"
    inventory = script_dir / "sites/dc1/inventory.yml"
    log_folder = script_dir / 'logs'
    log_file_path = log_folder / "ansible_build_output.log"
    
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    
    with open(log_file_path, 'w') as log_file:
        try:
            subprocess.run(
                ['ansible-playbook', playbook, '-i', inventory],
                cwd=script_dir,
                stdout=log_file,
                stderr=log_file,  # Redirect stderr to the same log file
                check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"An error occurred: {e}")

def run_ansible_deploy():
    playbook = script_dir / "playbooks/deploy_dc1_cvp.yml"
    inventory = script_dir / "sites/dc1/inventory.yml"
    log_folder = script_dir / 'logs'
    log_file_path = log_folder / "ansible_deploy_output.log"
    

    with open(log_file_path, 'w') as log_file:
        try:
            subprocess.run(
                ['ansible-playbook', playbook, '-i', inventory],
                cwd=script_dir,
                stdout=log_file,
                stderr=log_file,  # Redirect stderr to the same log file
                check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"An error occurred: {e}")
            
def generate_topology_tags(cvp_client):
    # Constants
    dc_tag_label = 'topology_hint_datacenter'
    fabric_tag_label = 'topology_hint_fabric'
    pod_tag_label = 'topology_hint_pod'
    rack_tag_label = 'topology_hint_rack'
    type_tag_label = 'topology_hint_type'
    dc_tag_value = 'DC1'
    fabric_tag_value = 'dc1_fabric'
    pod_tag_value = 'Pod1'
    leaf_tag_value = 'leaf'
    spine_tag_value = 'spine'
    pair1_tag_value = 'LeafPair1'
    pair2_tag_value = 'LeafPair2'
    element_type = 'ELEMENT_TYPE_DEVICE'

    # Generate a unique workspace name
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    workspace_id = f'avd-clab-tags-{current_time}'
    display_name = 'AVD Clab Tags'
    description = 'Workspace for tagging devices'

    # Create workspace
    cvp_client.api.workspace_config(
        workspace_id=workspace_id,
        display_name=display_name,
        description=description,
        request='REQUEST_UNSPECIFIED',
        request_id='1'
    )

    # Configure common tags
    common_tags = [
        (dc_tag_label, dc_tag_value),
        (fabric_tag_label, fabric_tag_value),
        (pod_tag_label, pod_tag_value)
    ]

    for tag_label, tag_value in common_tags:
        cvp_client.api.tag_config(
            element_type=element_type,
            workspace_id=workspace_id,
            tag_label=tag_label,
            tag_value=tag_value
        )

    # Get devices
    leaf_devices = cvp_client.api.get_devices_in_container('dc1_leafs')
    spine_devices = cvp_client.api.get_devices_in_container('dc1_spines')
    devices = leaf_devices + spine_devices

    # Retrieve device serial numbers
    device_details = {
        's1-leaf1': None,
        's1-leaf2': None,
        's1-leaf3': None,
        's1-leaf4': None,
        's1-spine1': None,
        's1-spine2': None
    }

    for device in devices:
        fqdn = device['fqdn']
        if fqdn in device_details:
            device_details[fqdn] = device['serialNumber']

    # Assign tags to devices
    for device in devices:
        device_id = device['serialNumber']
        for tag_label, tag_value in common_tags:
            cvp_client.api.tag_assignment_config(
                element_type=element_type,
                workspace_id=workspace_id,
                tag_label=tag_label,
                tag_value=tag_value,
                device_id=device_id,
                interface_id=''
            )
        
        fqdn = device['fqdn']
        if fqdn in device_details:
            specific_tags = {
                's1-leaf1': [(type_tag_label, leaf_tag_value), (rack_tag_label, pair1_tag_value)],
                's1-leaf2': [(type_tag_label, leaf_tag_value), (rack_tag_label, pair1_tag_value)],
                's1-leaf3': [(type_tag_label, leaf_tag_value), (rack_tag_label, pair2_tag_value)],
                's1-leaf4': [(type_tag_label, leaf_tag_value), (rack_tag_label, pair2_tag_value)],
                's1-spine1': [(type_tag_label, spine_tag_value)],
                's1-spine2': [(type_tag_label, spine_tag_value)]
            }
            for tag_label, tag_value in specific_tags[fqdn]:
                cvp_client.api.tag_assignment_config(
                    element_type=element_type,
                    workspace_id=workspace_id,
                    tag_label=tag_label,
                    tag_value=tag_value,
                    device_id=device_id,
                    interface_id=''
                )

    # Build the workspace
    cvp_client.api.workspace_config(
        workspace_id=workspace_id,
        display_name=display_name,
        description=description,
        request='REQUEST_START_BUILD',
        request_id='2'
    )

    time.sleep(5)  # Wait for build to complete

    # Submit the workspace
    cvp_client.api.workspace_config(
        workspace_id=workspace_id,
        display_name=display_name,
        description=description,
        request='REQUEST_SUBMIT',
        request_id='3'
    )

def decommission_devices(cvp_client):
    child_containers = ['dc1_spines', 'dc1_leafs']
    
    for child_container in child_containers:
        try:
            device_list = cvp_client.api.get_devices_in_container(child_container)
            logging.info(f"Devices in container '{child_container}': {device_list}")
            for device in device_list:
                cvp_device = device['serialNumber']
                cvp_request = str(uuid.uuid4())
                try:
                    cvp_client.api.device_decommissioning(cvp_device, cvp_request)
                    logging.info(f"Decommissioned device {cvp_device} from container {child_container}.")
                except Exception as e:
                    logging.error(f"Failed to decommission device {cvp_device} from container {child_container}: {e}")
        except Exception as e:
            logging.error(f"Failed to retrieve devices from container '{child_container}': {e}")
            

def delete_container(cvp_client, container_name, parent_container_name, parent_container_key):
    try:
        container = cvp_client.api.get_container_by_name(container_name)
        if container:
            cvp_client.api.delete_container(container["name"], container["key"], parent_container_name, parent_container_key)
            logging.info(f"Deleted container: {container_name}")
        else:
            logging.warning(f"Container '{container_name}' not found.")
    except Exception as e:
        logging.error(f"Failed to delete container '{container_name}': {e}")

def delete_containers(cvp_client, parent_container_name, child_containers):
    parent_container = cvp_client.api.get_container_by_name(parent_container_name)
    if not parent_container:
        logging.warning(f"Parent container '{parent_container_name}' not found.")
        return

    for container_name in child_containers:
        delete_container(cvp_client, container_name, parent_container["name"], parent_container["key"])

    delete_container(cvp_client, parent_container_name, 'Tenant', 'root')

def delete_configlets(cvp_client, prefixes):
    try:
        all_configlets = cvp_client.api.get_configlets()
        for configlet in all_configlets['data']:
            if any(configlet['name'].startswith(prefix) for prefix in prefixes):
                try:
                    cvp_client.api.delete_configlet(configlet['name'], configlet['key'])
                    logging.info(f"Deleted configlet: {configlet['name']}")
                except Exception as e:
                    logging.error(f"Failed to delete configlet '{configlet['name']}': {e}")
    except Exception as e:
        logging.error(f"Failed to retrieve configlets: {e}")
        
def delete_folders():
    folders_to_delete = ['logs','sites/dc1/documentation','sites/dc1/intended']
    for folder_path in folders_to_delete:
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(folder_path)
    

def cleanup_clab(info, cvp_ip, cvp_username, cvp_password):
    clear_console()
    cvp_client = CvpClient()
    cvp_client.connect([cvp_ip], cvp_username, cvp_password, 120, 120)
    print("----------------------------------------")
    print("Lab Cleanup Information")
    print("----------------------------------------")
    print("")
    
    # Decommission devices from CVP
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Decommissioning devices from CVP")
    try:
        decommission_devices(cvp_client)
        time.sleep(10)  # Simulating a long-running task for demonstration
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Wait for devices to be decommissioned before deleting the containers
    child_containers = ['dc1_spines', 'dc1_leafs']
    while True:
        all_decommissioned = True
        for child_container in child_containers:
            devices = cvp_client.api.get_devices_in_container(child_container)
            if devices:
                all_decommissioned = False
                break
        if all_decommissioned:
            break
        time.sleep(20)
    
    # Delete containers from CVP
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Deleting Containers from CVP")
    try:
        delete_containers(cvp_client, "dc1_fabric", ["dc1_spines", "dc1_leafs"])
        time.sleep(10)  # Simulating a long-running task for demonstration
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Delete configlets from CVP
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Deleting Configlets from CVP")
    try:
        delete_configlets(cvp_client, ['s1', 'AVD-'])
        time.sleep(10)  # Simulating a long-running task for demonstration
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Destroying ContainerLab topology
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Destroying Container Lab")
    try:
        subprocess_run(info.destroy_command)
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    # Deleting Unused Folders
    stop_animation = threading.Event()
    animation_thread = animated_message(stop_animation, "Cleaning Up Folders")
    try:
        delete_folders()
    finally:
        stop_animation.set()
        animation_thread.join()
    logging.info("Done")
    
    print("")
    print("")
    print("----------------------------------------")
    print("Lab Destroyed Successfully")
    print("----------------------------------------")
    input("Press any key to return to the Main Menu")
    main()


def preview_log(file_path):
    clear_console()
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            print(content)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except IOError:
        print(f"Error reading file: {file_path}")
    
    input("Press any key to return to the Main Menu")
    main()

def terminate_script():
    clear_console()
    sys.exit()
            
def main_menu():
    clear_console()
    print("----------------------------------------")
    print("AVD CLAB Helper")
    print("----------------------------------------")
    print("")
    print("1. Deploy Lab")
    print("2. Cleanup Lab")
    print("3. Show Ansible Build Log")
    print("4. Show Ansible Deploy Log")
    print("5. Change CVP Credentials")
    print("6. Quit\n")

def main():
    clear_console()
    if os.getuid() == 0:
        topology_file = script_dir / "topology.yaml"
        deploy_command = f"clab deploy -t {topology_file}"
        destroy_command = f"clab destroy -t {topology_file} --cleanup"
        build_log = script_dir / "logs/ansible_build_output.log"
        deploy_log = script_dir / "logs/ansible_deploy_output.log"
        info = Info(deploy_command, topology_file, destroy_command, build_log, deploy_log)

        # Read CVP credentials
        cvp_ip, cvp_username, cvp_password = read_cvp_credentials()
        create_inventory(cvp_ip, cvp_username, cvp_password)

        # Validate credentials
        if cvp_username is None or cvp_password is None or cvp_ip is None:
            logging.error("Invalid or missing CVP credentials.")
            terminate_script()

        # Display main menu and handle user choice
        while True:
            main_menu()
            choice = input("Enter your choice: ")
            if choice == "1":
                deploy_clab(info, cvp_ip, cvp_username, cvp_password)
            elif choice == "2":
                cleanup_clab(info, cvp_ip, cvp_username, cvp_password)
            elif choice == "3":
                preview_log(info.build_log)
            elif choice == "4":
                preview_log(info.deploy_log)
            elif choice == "5":
                get_cvp_credentials()  # Option to change CVP credentials
                # Restart the script to apply the changes
                python = sys.executable
                os.execl(python, python, *sys.argv)        
            elif choice == "6":
                terminate_script()
            else:
                logging.error("Invalid choice. Please try again.")

    else:
        logging.error("Container lab needs superuser privileges to run. Please restart with 'sudo' or as root.")

if __name__ == "__main__":
    main()