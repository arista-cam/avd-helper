import os
import logging
import subprocess
import yaml
import time
import ssl
import uuid
import sys
import re
import shutil
import threading
import socket
from pathlib import Path


def check_software():
    os.system("clear")

    software_list = [
        ("docker", "docker --version", "DOCKER_REQUIRED", r"Docker version (\S+)"),
        (
            "containerlab",
            "containerlab version",
            "CONTAINERLAB_REQUIRED",
            r"version: (\S+)",
        ),
        ("pip3", "pip3 --version", "PIP_REQUIRED", r"pip (\S+)"),
        ("ansible", "ansible --version", "ANSIBLE_REQUIRED", r"ansible \[core (\S+)\]"),
        (
            "arista.avd",
            "ansible-galaxy collection list arista.avd",
            "AVD_COLLECTION_REQUIRED",
            r"arista.avd (\S+)",
        ),
        (
            "pyavd",
            "pip3 show pyavd",
            "PYAVD_REQUIRED",
            r"Version: (\S+)",
        ),
        ("cvprac", "pip3 show cvprac", "CVPRAC_REQUIRED", r"Version: (\S+)"),
        ("requests", "pip3 show requests", "REQUESTS_REQUIRED", r"Version: (\S+)"),
        ("docker-py", "pip3 show docker", "DOCKER_PY_REQUIRED", r"Version: (\S+)"),
        ("paramiko", "pip3 show paramiko", "PARAMIKO_REQUIRED", r"Version: (\S+)"),
    ]

    print("----------------------------------------")
    print("Checking Software Requirements")
    print("----------------------------------------")
    print("")

    all_installed = True

    for name, command, env_var, version_pattern in software_list:
        try:
            # Animated message
            for i in range(5):
                sys.stdout.write(f"\rChecking {name}{'.' * (i % 4)}   ")
                sys.stdout.flush()
                time.sleep(0.1)
            sys.stdout.write("\r" + " " * (len(f"Checking {name}{'.' * 4}")) + "\r")

            output = (
                subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                .decode("utf-8")
                .strip()
            )
            match = re.search(version_pattern, output)
            version = match.group(1) if match else "Unknown"
            print(f"{name} - Installed - Version: {version}")

        except subprocess.CalledProcessError:
            print(f"{name} - Not Installed")
            all_installed = False
            os.environ[env_var] = "true"

    if all_installed:
        print("\nAll software requirements met!")
        time.sleep(2)
        return True
    else:
        os.system("clear")
        print("----------------------------------------")
        print("Installing Missing Software")
        print("----------------------------------------")
        print("")
        os.environ["RESTART_SCRIPT"] = "true"
        subprocess.run("chmod +x ./install.sh", shell=True)
        subprocess.run(["./install.sh"], check=True)
        return False


if not check_software():
    sys.exit(1)


def check_and_update_repo():
    # Fetch the latest changes from the remote
    fetch_result = subprocess.run(["git", "fetch"], capture_output=True, text=True)
    if fetch_result.returncode != 0:
        print(f"Error fetching repository: {fetch_result.stderr}")
        return

    # Get the hashes for local, remote, and base commits
    local_hash = subprocess.run(
        ["git", "rev-parse", "@"], capture_output=True, text=True
    ).stdout.strip()
    remote_hash = subprocess.run(
        ["git", "rev-parse", "@{u}"], capture_output=True, text=True
    ).stdout.strip()
    base_hash = subprocess.run(
        ["git", "merge-base", "@", "@{u}"], capture_output=True, text=True
    ).stdout.strip()

    # Check if the local repository is up-to-date with the remote
    if local_hash == remote_hash:
        return True
    elif local_hash == base_hash:
        print("----------------------------------------")
        print("Updating Repository")
        print("----------------------------------------")
        print("")
        print("Your repository is behind the remote. Updating...")
        subprocess.run("chmod +x ./update.sh", shell=True)
        subprocess.run(["./update.sh"], check=True)
        return False
    else:
        print("Unexpected state. Manual intervention might be needed.")


# Importing software that is not available from the system by default
import paramiko
import requests
import docker
from cvprac.cvp_client import CvpClient

ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()


class ClabHelper:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.topology_file = self.script_dir / "topology.yaml"
        self.token_file = self.script_dir / "token.tok"
        self.cvp_file = self.script_dir / "cvp_info.txt"
        self.network_file = self.script_dir / "network_info.txt"
        self.template_ceos_file = self.script_dir / "templates" / "ceos.tpl"
        self.output_ceos_file = self.script_dir / "ceos.cfg"
        self.template_inventory_file = self.script_dir / "templates" / "inventory.tpl"
        self.output_inventory_file = self.script_dir / "sites" / "dc1" / "inventory.yml"
        self.template_cvaas_auth_file = self.script_dir / "templates" / "cvaas_auth.tpl"
        self.output_cvaas_auth_file = (
            self.script_dir
            / "sites"
            / "dc1"
            / "group_vars"
            / "CVAAS"
            / "cvaas_auth.yml"
        )
        self.template_deploy_file = self.script_dir / "templates" / "cv_deploy.tpl"
        self.output_deploy_file = self.script_dir / "playbooks" / "cv_deploy.yml"
        self.template_httpd_file = self.script_dir / "templates" / "httpd.tpl"
        self.output_httpd_file = self.script_dir / "httpd.conf"
        self.doc_dir = self.script_dir / "sites" / "dc1" / "documentation"
        self.intend_dir = self.script_dir / "sites" / "dc1" / "intended"
        self.cvaas_dir = self.script_dir / "sites" / "dc1" / "group_vars" / "CVAAS"
        self.creds = {}
        self.tokens = {}
        self.cvp_token = None
        self.device_token = None
        self.cvp_ip = None
        self.api_server = None
        self.cvp_type = None
        self.is_cvaas = None
        self.dns_server = None
        self.ntp_server = None
        self.device_addr = []
        self.cvp_client = CvpClient()
        self.inventory = self.script_dir / "sites/dc1/inventory.yml"
        self.log_folder = self.script_dir / "logs"
        self.clab_log = self.log_folder / "clab.log"
        self.clab_logger = self.setup_logger("clab_logger", self.clab_log)
        self.ssh_log = self.log_folder / "ssh.log"
        self.ssh_logger = self.setup_logger("ssh_logger", self.ssh_log)
        self.cvp_log = self.log_folder / "cvp.log"
        self.cvp_logger = self.setup_logger("cvp_logger", self.cvp_log)
        self.ansible_error_log = self.log_folder / "ansible_error_log.log"
        self.ansible_error_logger = self.setup_logger(
            "ansible_error_logger", self.ansible_error_log
        )
        self.ansible_build_log = self.log_folder / "ansible_build_output.log"
        self.ansible_deploy_log = self.log_folder / "ansible_deploy_output.log"
        self.log_location = None
        self.stop_event = threading.Event()
        self.animation_threads = []
        self.host_ip = None

    @staticmethod
    def superuser_required(func):
        def wrapper(self, *args, **kwargs):
            if os.getuid() != 0:
                logging.error(
                    "Container lab needs superuser privileges to run. Please restart with 'sudo' or as root."
                )
                return
            return func(self, *args, **kwargs)

        return wrapper

    def clear_console(self):
        os.system("clear")

    def restart_script(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def setup_logger(self, name, log_file, level=logging.INFO):

        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)

        return logger

    def error_message(self, error_info):
        self.stop_event.set()  # Stop all animations
        # Wait for all animation threads to finish
        for thread in self.animation_threads:
            thread.join()

        # Define the border and message lines
        border_char = "*"
        border_length = 68
        error_lines = [
            "An Error has occurred",
            f"Please check the {self.log_location} for more information",
        ]

        # Calculate the length of the border based on the longest line
        max_length = max(len(line) for line in error_lines)
        border_length = max_length + 4  # Add padding for borders

        # Print the error message
        self.clear_console()
        print(border_char * border_length)
        for line in error_lines:
            print(f"! {line.ljust(max_length)} !")
        print(border_char * border_length)
        print("")
        input("Please press Enter to return to the Main Menu")
        self.main()

    def subprocess_run(self, command):
        result = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            self.clab_logger.error(
                f"Command failed with error: {result.stderr.decode()}"
            )
            self.log_location = "Container Lab Log file"
            self.error_message()
        else:
            self.clab_logger.info(f"Command output: {result.stdout.decode()}")
        return result

    def check_ceosimage(self):

        client = docker.from_env()
        images = client.images.list()
        threshold_version = "4.32.0F"
        found_ceosimage = False

        for image in images:
            ceosimage_tags = [tag for tag in image.tags if tag.startswith("ceosimage")]
            if ceosimage_tags:
                found_ceosimage = True
                for tag in ceosimage_tags:
                    _, version = tag.split(":")

                    # Parsing the version
                    version_match = re.match(r"(\d+)\.(\d+)\.(\d+)([A-Za-z]*)", version)
                    threshold_match = re.match(
                        r"(\d+)\.(\d+)\.(\d+)([A-Za-z]*)", threshold_version
                    )

                    if version_match and threshold_match:
                        version_parts = [
                            int(part) for part in version_match.groups()[:3]
                        ] + [version_match.group(4)]
                        threshold_parts = [
                            int(part) for part in threshold_match.groups()[:3]
                        ] + [threshold_match.group(4)]

                        if version_parts < threshold_parts:
                            self.clear_console()
                            print("-" * 60)
                            print(
                                f"WARNING: {tag} is below the supported version. In versions prior to {threshold_version} the ceos-lab image requires a cgroups v1 environment"
                            )
                            print(
                                f"Some linux distributions might be configured to use cgroups v2 out of the box which will stop the devices from booting"
                            )
                            print(
                                f"If this issue occurs, either upgrade to {threshold_version} or visit https://containerlab.dev/manual/kinds/ceos/#cgroups-v1 "
                            )
                            print("-" * 60)
                            input("Press any key to continue...")

        if not found_ceosimage:
            self.clear_console()
            self.docker_functions()

    def docker_functions(self):
        self.clear_console()
        print("----------------------------------------")
        print("Importing Docker Images")
        print("----------------------------------------")
        print("")

        # Finding tar files
        tar_file_paths = []
        for file in os.listdir("./EOS"):
            if file.startswith("cEOS-lab") and file.endswith(".tar"):
                tar_file_paths.append(os.path.join("./EOS", file))

        if tar_file_paths:
            for tar_file_path in tar_file_paths:
                repository = "ceosimage"
                filename = os.path.basename(tar_file_path)
                tag = None
                if filename.startswith("cEOS-lab") and filename.endswith(".tar"):
                    tag = filename[len("cEOS-lab") + 1 : -4]

                if repository and tag:
                    docker_command = [
                        "docker",
                        "import",
                        tar_file_path,
                        f"{repository}:{tag}",
                    ]
                    result = subprocess.run(
                        docker_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    if result.returncode != 0:
                        print("Error importing Docker image:", result.stderr.decode())
                        print("-" * 60)
                        print(
                            "The cEOS image has failed to import, please use the manual 'docker import' command instead"
                        )
                        print("-" * 60)
                        input("Press any key to exit")
                        sys.exit(0)
                else:
                    print("Failed to import Docker image")
                    print("-" * 60)
                    print(
                        "The cEOS image has failed to import, please use the manual 'docker import' command instead"
                    )
                    print("-" * 60)
                    input("Press any key to exit")
                    sys.exit(0)
        else:
            print("-" * 60)
            print("ERROR: There are no docker images with the 'ceosimage' tag")
            print(
                "Please place the cEOS-lab.tar file in the EOS directory or manually import the image into docker using the 'docker import' command."
            )
            print("-" * 60)
            while True:
                user_input = (
                    input(
                        "Press 'y' if you have added the file to the EOS directory or 'n' to exit: "
                    )
                    .strip()
                    .lower()
                )

                if user_input == "y":
                    self.restart_script()
                    break
                elif user_input == "n":
                    self.clear_console()
                    sys.exit(0)
                    break
                else:
                    print("Invalid input. Please enter 'y' to restart or 'n' to exit.")

    def check_files(self):
        files = {
            "token": self.token_file,
            "network": self.network_file,
            "cvp": self.cvp_file,
        }

        if (
            not files["token"].exists()
            and not files["network"].exists()
            and files["cvp"].exists()
        ):
            files["cvp"].unlink()
        elif (
            not files["token"].exists()
            and not files["cvp"].exists()
            and files["network"].exists()
        ):
            files["network"].unlink()
        elif (
            not files["token"].exists()
            and files["cvp"].exists()
            and files["network"].exists()
        ):
            files["token"].unlink()

        if (
            not files["token"].exists()
            or not files["cvp"].exists()
            or not files["network"].exists()
        ):
            self.get_cvp_credentials()
            self.get_network_info()

    def read_cvp_credentials(self):
        with open(self.cvp_file, "r") as file:
            lines = file.readlines()
        self.creds = {
            line.strip().split("=")[0]: line.strip().split("=")[1] for line in lines
        }
        self.cvp_ip = self.creds.get("cvp_ip", None)
        self.cvp_type = self.creds.get("cvp_type", None)

        with open(self.token_file, "r") as file:
            lines = file.readlines()
        self.tokens = {
            line.strip().split("=")[0]: line.strip().split("=")[1] for line in lines
        }
        self.cvp_token = self.tokens.get("cvp_token", None)
        self.device_token = self.tokens.get("device_token", None)

        if self.cvp_type == "cvaas":
            self.is_cvaas = True
            self.api_server = self.creds.get("api_server", None)
        else:
            self.is_cvaas = False

    def get_cvp_version(self):
        self.clear_console()
        print("----------------------------------------")
        print("Which version of CVP are you using?")
        print("----------------------------------------")
        print("1. CloudVision VM")
        print("2. CVaaS\n")

        while True:
            cvp_choice = input("Enter your choice: ")
            if cvp_choice in ["1", "2"]:
                return "cvp_vm" if cvp_choice == "1" else "cvaas"
            else:
                logging.error("Invalid choice for CVP type. Please try again.")

    def get_cvaas_instance(self):
        self.clear_console()
        print("----------------------------------------")
        print("CVP Server Information")
        print("----------------------------------------")
        print("1. United States 1a")
        print("2. United States 1c")
        print("3. Japan")
        print("4. Germany")
        print("5. Australia")
        print("6. Canada")
        print("7. United Kingdom")
        print("8. Dev")
        print("9. Staging (Most Likely This One)\n")

        instance_mapping = {
            "1": "www.cv-prod-us-central1-a.arista.io",
            "2": "www.cv-prod-us-central1-c.arista.io",
            "3": "www.cv-prod-apnortheast-1.arista.io",
            "4": "www.cv-prod-euwest-2.arista.io",
            "5": "www.cv-prod-ausoutheast-1.arista.io",
            "6": "www.cv-prod-na-northeast1-b.arista.io",
            "7": "www.cv-prod-cv-prod-uk-1.arista.io",
            "8": "www.cv-staging.corp.arista.io",
            "9": "www.cv-staging.corp.arista.io",
            "": "www.cv-staging.corp.arista.io",
        }

        while True:
            cvp_instance = input("Please select the CVaaS instance [9]: ")
            if cvp_instance in instance_mapping:
                return instance_mapping[cvp_instance]
            else:
                logging.error("Invalid choice. Please try again.")

    def get_cvp_credentials(self):
        cvp_version = self.get_cvp_version()
        self.clear_console()

        if cvp_version == "cvaas":
            cvp_ip = self.get_cvaas_instance()
        else:
            print("----------------------------------------")
            print("CVP Server Information")
            print("----------------------------------------")
            cvp_ip = input("Please enter the CVP IP address: ")
            print("")

        api_server_mapping = {
            "cv-prod-us-central1-a.arista.io": "apiserver.cv-prod-us-central1-a.arista.io:443",
            "cv-prod-us-central1-c.arista.io": "apiserver.cv-prod-us-central1-c.arista.io:443",
            "cv-prod-apnortheast-1.arista.io": "apiserver.cv-prod-apnortheast-1.arista.io:443",
            "cv-prod-euwest-2.arista.io": "apiserver.cv-prod-euwest-2.arista.io:443",
            "cv-prod-ausoutheast-1.arista.io": "apiserver.cv-prod-ausoutheast-1.arista.io:443",
            "cv-prod-na-northeast1-b.arista.io": "apiserver.cv-prod-na-northeast1-b.arista.io:443",
            "cv-prod-cv-prod-uk-1.arista.io": "apiserver.cv-prod-cv-prod-uk-1.arista.io:443",
            "cv-staging.corp.arista.io": "apiserver.cv-staging.corp.arista.io:443",
        }

        api_server = api_server_mapping.get(
            cvp_ip, "apiserver.cv-staging.corp.arista.io:443"
        )

        with open(self.cvp_file, "w") as file:
            file.write(f"cvp_type={cvp_version}\n")
            file.write(f"cvp_ip={cvp_ip}\n")
            if cvp_version == "cvaas":
                file.write(f"api_server={api_server}\n")

        self.clear_console()
        print("**************************************************")
        print("\033[1mCVP Service Account Token\033[0m")
        print("**************************************************")
        print(
            f"\nTo generate a service account token, navigate to: \n\033[4mhttps://{cvp_ip}/cv/settings/aaa-service-accounts\033[0m"
        )
        print("Hint: You can use CTRL + Click to open the link in a new window\n")
        print("**************************************************")
        print("\033[1mSteps:\033[0m")
        print("**************************************************")
        print(
            "1. Click the blue \033[1m+New Server Account\033[0m button and fill in the details:\n"
        )
        print("   \033[1mService Account Name:\033[0m Ansible")
        print("   \033[1mDescription:\033[0m Ansible Service Account")
        print("   \033[1mStatus:\033[0m Enabled")
        print("   \033[1mRole:\033[0m network-admin\n")
        print(
            "2. Click \033[1mCreate\033[0m and then select the \033[1mansible\033[0m service account from the list below."
        )
        print(
            "3. Under the \033[1mGenerate Service Account Token\033[0m section, fill in the Description field."
        )
        print(
            "4. Select a \033[1mValid Until\033[0m date and click the \033[1mGenerate\033[0m button.\n"
        )

        cvp_token = input("Please paste the CVP service account token here: ")
        self.clear_console()
        print("**************************************************")
        print("\033[1mCVP Device Token\033[0m")
        print("**************************************************")
        print(
            f"\nTo generate a Device Onboarding Token, navigate to: \n\033[4mhttps://{cvp_ip}/cv/devices/device-onboarding\033[0m"
        )
        print("Hint: You can use CTRL + Click to open the link in a new window\n")
        print("**************************************************")
        print("\033[1mSteps:\033[0m")
        print("**************************************************")
        print("1. Click the \033[1mOnboard with Certificates\033[0m option")
        print(
            "2. Click the dropdown under \033[1mGenerate the Token\033[0m and select a timeframe for token expiration"
        )
        print("3. Click the blue \033[1mGenerate\033[0m button \n")

        device_token = input("Please paste the device token: ")

        with open(self.token_file, "w") as file:
            file.write(f"cvp_token={cvp_token}\n")
            file.write(f"device_token={device_token}")

    def read_network_info(self):
        with open(self.network_file, "r") as file:
            lines = file.readlines()
        self.creds = {
            line.strip().split("=")[0]: line.strip().split("=")[1] for line in lines
        }
        self.dns_server = self.creds.get("dns_server", None)
        self.ntp_server = self.creds.get("ntp_server", None)

    def get_network_info(self):
        self.clear_console()
        print("----------------------------------------")
        print("Network Information")
        print("----------------------------------------")
        print("")

        # Function to get non-blank input from the user
        def get_non_blank_input(prompt):
            while True:
                user_input = input(prompt).strip()
                if user_input:
                    return user_input
                print("Input cannot be blank. Please try again.")

        # Get DNS server IP address
        dns_server = get_non_blank_input(
            "Please enter the IP address of your DNS server: "
        )

        # Get NTP server IP address
        ntp_server = get_non_blank_input(
            "Please enter the IP address of your NTP server: "
        )

        # Write to the file
        with open(self.network_file, "w") as file:
            file.write(f"dns_server={dns_server}\n")
            file.write(f"ntp_server={ntp_server}")

    def create_inventory(self):

        # Function to handle template processing and writing to output file
        def process_template(template_file, output_file, replacements):
            if output_file.exists():
                output_file.unlink()
            with open(template_file, "r") as file:
                template_contents = file.read()
            for placeholder, value in replacements.items():
                template_contents = template_contents.replace(placeholder, value)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as file:
                file.write(template_contents)

        # Process ceos template
        process_template(
            self.template_ceos_file,
            self.output_ceos_file,
            {"{{dns_server}}": self.dns_server, "{{ntp_server}}": self.ntp_server},
        )

        # Process inventory template
        process_template(
            self.template_inventory_file,
            self.output_inventory_file,
            {"{{cvp_group}}": "CVAAS", "{{cvp_host}}": "cvaas"},
        )
        cvaas_folder = self.script_dir / "sites" / "dc1" / "group_vars" / "CVAAS"
        if not os.path.exists(cvaas_folder):
            os.makedirs(cvaas_folder)
        cvp_certs = "True" if self.cvp_type == "cvaas" else "False"

        process_template(
            self.template_cvaas_auth_file,
            self.output_cvaas_auth_file,
            {
                "{{cvp_ip}}": self.cvp_ip,
                "{{cvp_token}}": self.cvp_token,
                "{{cvp_certs}}": cvp_certs,
            },
        )

        process_template(
            self.template_deploy_file,
            self.output_deploy_file,
            {
                "{{cvp_ip}}": self.cvp_ip,
                "{{cvp_token}}": self.cvp_token,
                "{{cvp_certs}}": cvp_certs,
            },
        )

        shutil.copy(self.template_httpd_file, self.output_httpd_file)

    def deploy_clab(self):
        self.subprocess_run(f"clab deploy -t {self.topology_file}")

    def create_commands(self):
        self.commands = [
            "enable",
            "copy terminal: file:/tmp/cv-onboarding-token",
            f"{self.device_token}",
            "\x04",
            "configure",
            "daemon TerminAttr",
            f"exec /usr/bin/TerminAttr "
            + (
                f"-smashexcludes=ale,flexCounter,hardware,kni,pulse,strata -cvaddr={self.api_server} -cvauth=token-secure,/tmp/cv-onboarding-token -cvvrf=MGMT -taillogs"
                if self.is_cvaas
                else f"-ingestgrpcurl={self.cvp_ip}:9910 -ingestauth=token,/tmp/cv-onboarding-token -smashexcludes=ale,flexCounter,hardware,kni,pulse,strata -ingestexclude=/Sysdb/cell/1/agent,/Sysdb/cell/2/agent -ingestvrf=MGMT -taillogs"
            ),
            "shutdown",
            "no shutdown",
        ]

    def cvp_connection(self):
        self.cvp_client.connect(
            nodes=[self.cvp_ip],
            username="",
            password="",
            is_cvaas=self.is_cvaas,
            api_token=self.cvp_token,
        )

    def cvp_register_devices(self):
        try:
            with open(self.topology_file, "r") as file:
                lines = yaml.safe_load(file)
        except Exception as e:
            self.ssh_logger.error(f"Failed to read or parse topology file: {e}")
            self.log_location = "SSH Log file"
            self.error_message()
            return

        self.device_addr = []
        if "topology" in lines and "nodes" in lines["topology"]:
            for node_name, node_info in lines["topology"]["nodes"].items():
                if node_info.get("kind") == "ceos":
                    self.device_addr.append(node_info.get("mgmt-ipv4"))

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        for ip in self.device_addr:
            try:
                self.ssh_logger.info(f"Connecting to device at {ip}")
                client.connect(ip, port=22, username="arista", password="arista")
            except Exception as e:
                self.ssh_logger.error(f"Failed to connect to device at {ip}: {e}")
                continue

            try:
                ssh_session = client.invoke_shell()
                time.sleep(1)
                for command in self.commands:
                    ssh_session.send(command + "\n")
                    time.sleep(1)
                ssh_session.send("\x04")
                time.sleep(1)
                self.ssh_logger.info(f"Completed commands on device {ip}")
            except Exception as e:
                self.ssh_logger.error(f"Error during SSH session on device {ip}: {e}")
                self.log_location = "SSH Log file"
                self.error_message()
        time.sleep(60)

    def cvp_move_devices(self):
        try:
            self.cvp_logger.info("Starting device move process.")
            self.cvp_connection()

            device_list = [
                {"deviceName": device["fqdn"]}
                for device in self.cvp_client.api.get_devices_in_container("Undefined")
            ]
            self.cvp_logger.info(
                f"Found devices in 'Undefined' container: {device_list}"
            )

            for device in device_list:
                try:
                    device_info = self.cvp_client.api.get_device_by_name(
                        device["deviceName"]
                    )
                    new_container = self.cvp_client.api.get_container_by_name("Tenant")
                    self.cvp_client.api.move_device_to_container(
                        "python", device_info, new_container
                    )
                    self.cvp_logger.info(
                        f"Moved device {device['deviceName']} to 'Tenant' container."
                    )
                except Exception as e:
                    self.cvp_logger.error(
                        f"Error moving device {device['deviceName']}: {e}"
                    )

            self.cvp_execute_pending_tasks()
            self.cvp_logger.info("Executed pending tasks.")

            time.sleep(10)
            self.cvp_logger.info("Device move process completed.")
        except Exception as e:
            self.cvp_logger.error(f"Error in cvp_move_devices: {e}")
            self.log_location = "CVP Log file"
            self.error_message()

    def cvp_create_configlets(self):
        try:
            self.cvp_logger.info("Starting configlet creation process.")
            self.cvp_connection()

            device_list = self.cvp_client.api.get_devices_in_container("Tenant")
            device_info = [
                {"name": device["fqdn"], "macAddress": device["systemMacAddress"]}
                for device in device_list
            ]
            self.cvp_logger.info(f"Found devices in 'Tenant' container: {device_info}")

            for info in device_info:
                try:
                    device_mac = info["macAddress"]
                    device_short_name = info["name"]
                    dev_mgmt = f"{device_short_name}_management"

                    get_config = self.cvp_client.api.get_device_configuration(
                        device_mac
                    )
                    self.cvp_client.api.add_configlet(dev_mgmt, get_config)
                    self.cvp_logger.info(
                        f"Created configlet {dev_mgmt} for device {device_short_name}."
                    )

                    device_name = self.cvp_client.api.get_device_by_name(
                        device_short_name
                    )
                    mgmt_configlet = self.cvp_client.api.get_configlet_by_name(dev_mgmt)
                    mgmt_configlet_key = [
                        {"name": mgmt_configlet["name"], "key": mgmt_configlet["key"]}
                    ]

                    self.cvp_client.api.apply_configlets_to_device(
                        "Management Configs", device_name, mgmt_configlet_key
                    )
                    self.cvp_logger.info(
                        f"Applied configlet {dev_mgmt} to device {device_short_name}."
                    )
                except Exception as e:
                    self.cvp_logger.error(
                        f"Error creating or applying configlet for device {info['name']}: {e}"
                    )
                    self.log_location = "CVP Log file"
                    self.error_message()

            self.cvp_execute_pending_tasks()
            self.cvp_logger.info("Executed pending tasks.")

            time.sleep(10)
            self.cvp_logger.info("Configlet creation process completed.")
        except Exception as e:
            self.cvp_logger.error(f"Error in cvp_create_configlets: {e}")
            self.log_location = "CVP Log file"
            self.error_message()

    def cvp_execute_pending_tasks(self):
        tasks = self.cvp_client.api.get_tasks_by_status("Pending")
        for task in tasks:
            self.cvp_client.api.execute_task(task["workOrderId"])

    def ansible_build(self):
        playbook = self.script_dir / "playbooks/build_dc1.yml"

        try:
            with open(self.ansible_build_log, "w") as log_file:
                subprocess.run(
                    ["ansible-playbook", playbook, "-i", self.inventory],
                    cwd=self.script_dir,
                    stdout=log_file,
                    stderr=log_file,
                    check=True,
                )
        except subprocess.CalledProcessError as e:
            # This exception is raised if subprocess.run() fails with check=True
            self.ansible_error_logger.error(
                f"Error running Ansible Build playbook: {e}"
            )
            self.log_location = (
                self.ansible_build_log
            )  # Set log file location for the error message
            self.error_message(
                "Ansible Build Playbook failed"
            )  # Provide a custom error message
        except Exception as e:
            # Catch any other exceptions
            self.ansible_error_logger.error(f"Unexpected error: {e}")
            self.log_location = (
                self.ansible_build_log
            )  # Set log file location for the error message
            self.error_message("An unexpected error occurred during the Ansible Build")

    def ansible_deploy(self):
        playbook = self.script_dir / "playbooks/cv_deploy.yml"

        try:
            with open(self.ansible_deploy_log, "w") as log_file:
                subprocess.run(
                    ["ansible-playbook", playbook, "-i", self.inventory],
                    cwd=self.script_dir,
                    stdout=log_file,
                    stderr=log_file,
                    check=True,
                )
        except subprocess.CalledProcessError as e:
            # This exception is raised if subprocess.run() fails with check=True
            self.ansible_error_logger.error(
                f"Error running Ansible Deploy playbook: {e}"
            )
            self.log_location = (
                self.ansible_deploy_log
            )  # Set log file location for the error message
            self.error_message(
                "Ansible Deploy Playbook failed"
            )  # Provide a custom error message
        except Exception as e:
            # Catch any other exceptions
            self.ansible_error_logger.error(f"Unexpected error: {e}")
            self.log_location = (
                self.ansible_deploy_log
            )  # Set log file location for the error message
            self.error_message("An unexpected error occurred during the Ansible Deploy")

    def setup_apache_container(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((self.cvp_ip, 80))
        self.host_ip = s.getsockname()[0]
        s.close()

        container_name = "avd_apache_server"
        client = docker.from_env()

        Path(self.doc_dir).mkdir(parents=True, exist_ok=True)

        existing_containers = client.containers.list(
            all=True, filters={"name": container_name}
        )
        for container in existing_containers:
            container.stop()
            container.remove()

        try:
            container = client.containers.run(
                "httpd:latest",
                name=container_name,
                volumes={
                    os.path.abspath(self.doc_dir): {
                        "bind": "/usr/local/apache2/htdocs/",
                        "mode": "rw",
                    },
                    os.path.abspath(self.output_httpd_file): {
                        "bind": "/usr/local/apache2/conf/httpd.conf",
                        "mode": "ro",
                    },
                },
                ports={"80/tcp": 8080},
                detach=True,
            )
            time.sleep(3)
        except Exception as e:
            print(f"Error: {e}")
            return

    def documentation_info(self):
        self.clear_console()
        print("**************************************************")
        print("\033[1mAutomatically Generated Documentation\033[0m")
        print("**************************************************")
        print(
            f"\nTo view the automatically generated fabric and device documentation, navigate to: \n\033[4mhttp://{self.host_ip}:8080\033[0m"
        )
        print("Hint: You can use CTRL + Click to open the link in a new window\n")
        input("Please press any key to return to the Main Menu")
        self.main()

    def destroy_clab(self):
        self.subprocess_run(f"clab destroy -t {self.topology_file} --cleanup")

    def cvp_decommission_devices(self):
        cvp_container = "Tenant"
        prefix = "s1-"
        self.cvp_connection()

        try:
            self.cvp_logger.info(
                f"Starting decommission process for devices in '{cvp_container}' container."
            )

            device_list = self.cvp_client.api.get_devices_in_container(cvp_container)
            self.cvp_logger.info(
                f"Found devices in '{cvp_container}' container: {device_list}"
            )

            for device in device_list:
                cvp_device = device["serialNumber"]
                cvp_request = str(uuid.uuid4())
                device_name = device.get("fqdn", "Unknown device")

                try:
                    self.cvp_client.api.device_decommissioning(cvp_device, cvp_request)
                    self.cvp_logger.info(
                        f"Decommissioned device {device_name} with serial number {cvp_device}."
                    )
                except Exception as e:
                    self.cvp_logger.error(
                        f"Error decommissioning device {device_name} with serial number {cvp_device}: {e}"
                    )
                    self.log_location = "CVP Log File"
                    self.error_message()

            # Wait for all devices to be fully decommissioned
            self.cvp_logger.info("Starting configlet deletion process.")
            while True:
                devices = self.cvp_client.api.get_devices_in_container(cvp_container)
                self.cvp_logger.info(f"Retrieved devices: {devices}")

                s1_devices = [
                    device
                    for device in devices
                    if device["hostname"].startswith(prefix)
                ]

                if not s1_devices:
                    break

                self.cvp_logger.info(
                    f"Devices with prefix '{prefix}' still exist: {s1_devices}"
                )
                self.cvp_logger.info("Waiting for 30 seconds before checking again.")
                time.sleep(30)

            self.cvp_logger.info(
                "No devices with prefix 's1-' found, proceeding with configlet deletion."
            )

            self.cvp_logger.info("Decommission process completed.")
        except Exception as e:
            self.cvp_logger.error(f"Error in cvp_decommission_devices: {e}")
            self.log_location = "CVP Log file"
            self.error_message()

    def cvp_delete_configlets(self):
        prefix = "s1-"
        self.cvp_connection()
        try:
            all_configlets = self.cvp_client.api.get_configlets()
            self.cvp_logger.info(f"Retrieved all configlets: {all_configlets['data']}")

            for configlet in all_configlets["data"]:
                if configlet["name"].startswith(prefix):
                    try:
                        self.cvp_client.api.delete_configlet(
                            configlet["name"], configlet["key"]
                        )
                        self.cvp_logger.info(f"Deleted configlet: {configlet['name']}")
                    except Exception as e:
                        self.cvp_logger.error(
                            f"Failed to delete configlet '{configlet['name']}': {e}"
                        )
                        self.log_location = "CVP Log file"
                        self.error_message()

            self.cvp_logger.info("Configlet deletion process completed.")
        except Exception as e:
            self.cvp_logger.error(f"Failed to retrieve configlets: {e}")
            self.log_location = "CVP Log file"
            self.error_message()

    def cleanup_docker(self):
        container_name = "avd_apache_server"
        client = docker.from_env()
        existing_containers = client.containers.list(
            all=True, filters={"name": container_name}
        )
        for container in existing_containers:
            container.stop()
            container.remove()

        if self.output_httpd_file.exists():
            self.output_httpd_file.unlink()

        time.sleep(3)

    def show_logs(self, log_file, log_name):
        self.clear_console()
        try:
            with open(log_file, "r") as file:
                content = file.read()
                print(content)
        except FileNotFoundError:
            print(f"{log_name} file not found: {log_file}")
        except IOError:
            print(f"Error reading {log_name} file: {log_file}")
        input("Press enter to continue...")
        self.show_logs_menu()

    def clear_logs(self):
        if self.clab_log.exists():
            self.clab_log.unlink()
        if self.ssh_log.exists():
            self.ssh_log.unlink()
        if self.cvp_log.exists():
            self.cvp_log.unlink()
        if self.ansible_error_log.exists():
            self.ansible_error_log.unlink()
        if self.ansible_build_log.exists():
            self.ansible_build_log.unlink()
        if self.ansible_deploy_log.exists():
            self.ansible_deploy_log.unlink()
        self.clear_console()
        print(32 * "*")
        print("!  All Logs have been cleared  !")
        print(32 * "*")
        print("")
        input("Please press any key to return to the Main Menu")
        self.main()

    def list_docker_images(self):
        client = docker.from_env()
        images = client.images.list()
        self.clear_console()
        print("Current Docker Images:")
        for image in images:
            tags = image.tags
            if tags:
                for tag in tags:
                    print(f"- {tag}")
            else:
                print(f"- <none>: {image.id}")
        input("Please press any key to return to the Main Menu")
        self.main()

    def factory_reset(self):
        self.clear_console()
        print(68 * "*")
        print(f"! WARNING: THIS WILL RESET THE SCRIPT BACK TO DEFAULT !")
        print(68 * "*")
        print(f"The following Files/Folders will be deleted:")
        print(f"- {self.doc_dir}")
        print(f"- {self.intend_dir}")
        print(f"- {self.cvaas_dir}")
        print(f"- {self.output_inventory_file}")
        print(f"- {self.token_file}")
        print(f"- {self.cvp_file}")
        print(f"- {self.network_file}")
        print(f"- {self.output_deploy_file}")
        print(f"- {self.output_ceos_file}")
        print(68 * "*")
        print("")
        delete = input(
            "Please confirm that you would like to delete these files/folders [y/n]: "
        )
        if delete == "y":
            if self.doc_dir.exists():
                shutil.rmtree(self.doc_dir)
            if self.intend_dir.exists():
                shutil.rmtree(self.intend_dir)
            if self.cvaas_dir.exists():
                shutil.rmtree(self.cvaas_dir)
            if self.output_inventory_file.exists():
                self.output_inventory_file.unlink()
            if self.token_file.exists():
                self.token_file.unlink()
            if self.cvp_file.exists():
                self.cvp_file.unlink()
            if self.network_file.exists():
                self.network_file.unlink()
            if self.output_deploy_file.exists():
                self.output_deploy_file.unlink()
            if self.output_ceos_file.exists():
                self.output_ceos_file.unlink()
            if self.output_httpd_file.exists():
                self.output_httpd_file.unlink()
            self.clear_console()
            print("Factory Reset completed.")
            input("Please press any key to return to the Main Menu")
            self.main()
        else:
            self.main()

    def show_logs_menu(self):
        self.clear_console()
        print("----------------------------------------")
        print("Show Logs")
        print("----------------------------------------")
        print("1. Container Lab Log")
        print("2. SSH Connectivity Logs")
        print("3. Show CVP Log")
        print("4. Show Ansible Error Log")
        print("5. Show Ansible Build Log")
        print("6. Show Ansible Deploy Log")
        print("8. Clear Logs")
        print("9. Back\n")
        menu_choice = input("Enter your choice: ")
        if menu_choice == "1":
            self.show_logs(self.clab_log, "Container Lab")
        elif menu_choice == "2":
            self.show_logs(self.ssh_log, "SSH Connectivity")
        elif menu_choice == "3":
            self.show_logs(self.cvp_log, "CVP")
        elif menu_choice == "4":
            self.show_logs(self.ansible_error_log, "Ansible Error")
        elif menu_choice == "5":
            self.show_logs(self.ansible_build_log, "Ansible Build")
        elif menu_choice == "6":
            self.show_logs(self.ansible_deploy_log, "Ansible Deploy")
        elif menu_choice == "8":
            self.clear_logs()
        elif menu_choice == "9":
            self.main()
        else:
            print("Invalid choice, please try again.")
            self.show_logs_menu()

    def animated_message(self, stop_event, message="Processing", delay=0.5):
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

    def run_task_with_animation(self, task_function, message):
        local_stop_event = threading.Event()
        animation_thread = self.animated_message(local_stop_event, message)
        self.animation_threads.append(animation_thread)
        try:
            task_function()
        except Exception as e:
            local_stop_event.set()
            animation_thread.join()
            self.error_message(str(e))
        else:
            local_stop_event.set()
            animation_thread.join()

    def main_menu(self):
        self.clear_console()
        print("----------------------------------------")
        print("AVD CLAB Helper")
        print("----------------------------------------")
        print("1. Deploy Lab")
        print("2. Cleanup Lab")
        print("3. Open Topology Documentation")
        print("4. Show Logs")
        print("5. Show Docker Images")
        print("6. Reset All Files (Including Tokens)")
        print("7. Exit\n")

        while True:
            menu_choice = input("Enter your choice: ")
            if menu_choice in ["1", "2", "3", "4", "5", "6", "7"]:
                return menu_choice
            else:
                print("Invalid choice. Please try again.")

    @superuser_required
    def main(self):
        self.check_ceosimage()
        self.check_files()
        self.read_cvp_credentials()
        self.read_network_info()
        self.create_inventory()
        choice = self.main_menu()
        if choice == "1":
            self.clear_console()
            print("========================================")
            print("Lab Deployment Information")
            print("========================================")
            self.run_task_with_animation(self.deploy_clab, "Deploying AVD CLAB")
            self.create_commands()
            self.run_task_with_animation(
                self.cvp_register_devices, "Registering Devices with CVP"
            )
            self.run_task_with_animation(
                self.cvp_move_devices, "Moving Device Containers"
            )
            self.run_task_with_animation(
                self.cvp_create_configlets, "Creating Configlets"
            )
            self.run_task_with_animation(
                self.ansible_build, "Building L3LS Configurations"
            )
            self.run_task_with_animation(self.ansible_deploy, "Deploying L3LS")

            print("\nDeployment Complete!")
            input("Press Enter to return to the Main Menu")

            self.main()
        elif choice == "2":
            self.clear_console()
            print("========================================")
            print("Lab Cleanup Information")
            print("========================================")
            self.run_task_with_animation(self.destroy_clab, "Destroying AVD CLAB")
            self.run_task_with_animation(
                self.cvp_decommission_devices, "Decommissioning Devices from CVP"
            )
            self.run_task_with_animation(
                self.cvp_delete_configlets, "Deleting Configlets from CVP"
            )
            self.run_task_with_animation(
                self.cleanup_docker, "Removing Apache Docker Container"
            )

            print("\nCleanup Complete!")
            input("Press Enter to return to the Main Menu")
            self.main()
        elif choice == "3":
            self.clear_console()
            print("========================================")
            print("Documentation Information")
            print("========================================")
            self.run_task_with_animation(
                self.setup_apache_container, "Starting Docker Container"
            )
            self.documentation_info()
        elif choice == "4":
            self.show_logs_menu()
        elif choice == "5":
            self.list_docker_images()
        elif choice == "6":
            self.factory_reset()
        elif choice == "7":
            self.clear_console()
            sys.exit(0)


if __name__ == "__main__":
    helper = ClabHelper()
    helper.main()
