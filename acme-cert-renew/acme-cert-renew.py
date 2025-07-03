import os
import base64
import logging
import shutil
import subprocess
import requests
from logging.handlers import SysLogHandler

CONFIG_FILE = "acme-xc.conf"

# Logging configuration
logger = logging.getLogger("CertbotLogger")
logger.setLevel(logging.INFO)

syslog_handler = SysLogHandler(address='/dev/log')  # For Linux syslog
formatter = logging.Formatter('%(name)s: %(levelname)s: %(message)s')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)


def load_config():
    """Load configuration file"""
    config = {}
    with open(CONFIG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                try:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
                except ValueError:
                    logger.error(f"Invalid format in configuration file: {line}")
                    raise ValueError("Configuration file format error")
    return config


def run_certbot_renew(domain, acme_server, ca_cert_path="/usr/local/share/ca-certificates/acme.crt"):
    """
    Use Certbot to obtain a certificate (with custom CA certificates)
    """
    certbot_env = os.environ.copy()  # Copy the original environment variables
    certbot_env["REQUESTS_CA_BUNDLE"] = ca_cert_path  # Set CA certificate path

    certbot_cmd = [
        "certbot", "certonly",
        "--standalone",  # Use standalone mode
        "--non-interactive",  # Non-interactive mode
        "--agree-tos",  # Agree to terms of service
        "-m", "test@example.com",  # Email for notifications
        "--server", acme_server,  # ACME server URL
        "-d", domain  # Target domain
    ]

    try:
        subprocess.run(certbot_cmd, env=certbot_env, check=True)
        logger.info(f"Successfully obtained certificate with Certbot: {domain}")
    except subprocess.CalledProcessError as exc:
        logger.error(f"Error occurred while executing Certbot: {str(exc)}")
        raise


def base64_encode_file(file_path):
    """Base64 encode a file"""
    try:
        with open(file_path, "rb") as file:
            encoded_data = base64.b64encode(file.read()).decode('utf-8')
        logger.info(f"Successfully Base64 encoded file: {file_path}")
        return encoded_data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise


def copy_cert_and_key(cert_file_path, key_file_path, target_dir):
    """Copy the certificate and private key to the domain directory in the current working directory"""
    try:
        # Create the target directory if it doesn’t already exist
        os.makedirs(target_dir, exist_ok=True)  
        
        cert_target_path = os.path.join(target_dir, "cert.pem")
        key_target_path = os.path.join(target_dir, "privkey.pem")

        # Copy cert.pem to the target directory
        shutil.copy2(cert_file_path, cert_target_path)
        logger.info(f"Copied certificate to: {cert_target_path}")

        # Copy privkey.pem to the target directory
        shutil.copy2(key_file_path, key_target_path)
        logger.info(f"Copied private key to: {key_target_path}")
    except Exception as e:
        logger.error(f"Error while copying files to {target_dir}: {str(e)}")
        raise


def update_xc_lb_certificate(domain, namespace, cert_name, tenant_name, base64_cert, base64_key):
    """Send PUT request to XC API; if 404 occurs, create a new object via POST"""
    token = os.getenv("XC_TOKEN")
    if not token:
        logger.error("Environment variable 'XC_TOKEN' is not set")
        raise ValueError("Environment variable XC_TOKEN is not set")

    url = f"https://{tenant_name}.console.ves.volterra.io/api/config/namespaces/{namespace}/certificates/{cert_name}"
    
    json_data = {
        "metadata": {
            "name": cert_name,
            "namespace": namespace
        },
        "spec": {
            "certificate_url": f"string:///{base64_cert}",
            "private_key": {
                "clear_secret_info": {
                    "url": f"string:///{base64_key}"
                }
            },
            "disable_ocsp_stapling": {}  # Empty object
        }
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Authorization": f"APIToken {token}",
        "x-volterra-apigw-tenant": tenant_name
    }
    
    try:
        # Attempt PUT request
        logger.info(f"Sending PUT request to XC API: {url}")
        response = requests.put(url, headers=headers, json=json_data)

        if response.status_code == 200:
            logger.info(f"XC LB certificate updated successfully: {response.status_code}")
        elif response.status_code == 404:
            logger.info(f"Certificate object not found; attempting to create a new object using POST")
            
            # Change the URL for POST request
            post_url = f"https://{tenant_name}.console.ves.volterra.io/api/config/namespaces/{namespace}/certificates"
            
            # POST request to create a new certificate object
            post_json_data = {
                "metadata": {
                    "name": cert_name  # Same certificate name for new object creation
                },
                "spec": {
                    "certificate_url": f"string:///{base64_cert}",
                    "private_key": {
                        "clear_secret_info": {
                            "url": f"string:///{base64_key}"
                        }
                    },
                    "disable_ocsp_stapling": {}  # Empty object
                }
            }
            
            logger.info(f"Sending POST request to create a new certificate object: {post_url}")
            post_response = requests.post(post_url, headers=headers, json=post_json_data)
            if post_response.status_code == 201:
                logger.info(f"New certificate object created successfully: {post_response.status_code}")
            else:
                logger.error(f"Error creating new certificate object: {post_response.status_code} - {post_response.text}")
                raise Exception(f"Error creating new certificate: {post_response.status_code} - {post_response.text}")
        else:
            # Other unexpected errors during PUT
            logger.error(f"Error updating XC LB certificate: {response.status_code} - {response.text}")
            raise Exception(f"Error updating certificate: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        raise


def main():
    """Main function"""
    config = load_config()
    domain = config["domain"]
    namespace = config["namespace"]
    cert_name = config["cert_name"]
    tenant_name = config["tenant_name"]
    acme_server = config["acme_server"]
    cert_dir = f"/etc/letsencrypt/live/{domain}"

    # Obtain certificate with Certbot (using custom CA certificates)
    run_certbot_renew(domain, acme_server)

    # Paths for certificate and private key
    cert_file_path = os.path.join(cert_dir, "cert.pem")
    key_file_path = os.path.join(cert_dir, "privkey.pem")

    # Base64 encode certificate and private key files
    base64_cert = base64_encode_file(cert_file_path)
    base64_key = base64_encode_file(key_file_path)

    # Copy certificate and private key to the domain directory in the current directory
    domain_dir = os.path.join(os.getcwd(), domain)  # Directory named after the domain in the current working directory
    copy_cert_and_key(cert_file_path, key_file_path, domain_dir)

    # Send certificate data to XC API
    update_xc_lb_certificate(domain, namespace, cert_name, tenant_name, base64_cert, base64_key)


if __name__ == "__main__":
    main()