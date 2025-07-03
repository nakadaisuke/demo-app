
# **Certificate Management Script Documentation**

---

## **Purpose**

This script automates the following tasks:

1. Uses `Certbot` to obtain or renew certificates from an ACME server.
2. Encodes the obtained certificate (`cert.pem`) and private key (`privkey.pem`) in Base64 format.
3. Updates an existing certificate object in the XC API via a `PUT` request.
4. If the certificate object is missing in the XC API (returns 404), creates a new object via a `POST` request.

---

## **Features**

### **Certbot Integration**
- Obtains certificates from a custom ACME server in `certonly` standalone mode.
- Supports custom CA certificates using the `REQUESTS_CA_BUNDLE` environment variable.

### **Base64 Encoding**
- Encodes the `cert.pem` and `privkey.pem` files to Base64 format for secure transmission in API requests.

### **XC API Integration**
- Sends a `PUT` request to update an existing certificate object in the XC API.
- Fallbacks to creating a new certificate object with a `POST` request if the `PUT` request returns a 404.

### **File Management**
- Copies the obtained certificate and private key into a local directory named after the domain (in the current working directory).

---

## **Script Workflow**

1. **Configuration**:
   - The script reads configuration values from a file (`acme-xc.conf`), including the domain, namespace, cert name, tenant name, and ACME server URL.

2. **Certificate Retrieval**:
   - The `run_certbot_renew` function triggers `Certbot` in `certonly` standalone mode to obtain or renew certificates for the specified domain.

3. **Base64 Encoding**:
   - The `cert.pem` and `privkey.pem` files are Base64 encoded for use in the XC API requests.

4. **Certificate Updates**:
   - Makes a `PUT` request to the XC API to update an existing certificate object.
   - If the `PUT` request fails with a **404** (certificate object not found), it performs a fallback `POST` request to create a new certificate object.

5. **File Copying**:
   - Copies the `cert.pem` and `privkey.pem` files from `/etc/letsencrypt/live/{domain}` to a directory named after the domain in the current working directory.

---

## **How to Use**

### **Prerequisites**
1. **Python 3.x**:
   - Install the necessary libraries:
     ```bash
     pip install requests
     ```

2. **Certbot Installed**:
   - Install Certbot as follows:
     ```bash
     sudo apt install certbot
     ```

3. **Valid ACME Server**:
   - Ensure the ACME server is accessible and compatible with Certbot.

4. **API Token**:
   - Set the environment variable `XC_TOKEN` for XC API interactions.

---

### **Configuration File (`acme-xc.conf`)**

Example configuration file:
```plaintext
domain=example.internal
namespace=demo-namespace
cert_name=example-cert
tenant_name=my-tenant
acme_server=https://acme.example.com/acme/directory
```

Fields:
- `domain`: The domain for which the certificate is issued.
- `namespace`: The namespace in the XC API.
- `cert_name`: The name of the certificate object in the XC API.
- `tenant_name`: The tenant name for the XC API.
- `acme_server`: Custom ACME server URL.

---

### **Environment Variable Setup**

Set the `XC_TOKEN` API token required for authentication with the XC API:
```bash
export XC_TOKEN="your-api-token"
```

---

### **Running the Script**

Run the script as follows:
```bash
python3 script_name.py
```

---

## **Code Breakdown**

### **Configuration Loading (`load_config`)**
The script reads configuration values from the `acme-xc.conf` file and returns them as a dictionary.

### **Certificate Management (`run_certbot_renew`)**
The script uses Certbot to obtain or renew certificates in standalone mode, ensuring compatibility with custom ACME servers and CA certificates.

### **Certificate Base64 Encoding (`base64_encode_file`)**
Encodes `.pem` files (e.g., `cert.pem`, `privkey.pem`) to Base64 format for safe transmission to the XC API.

### **File Management (`copy_cert_and_key`)**
Copies `cert.pem` and `privkey.pem` to a directory named after the domain in the current working directory.

### **XC API Updates (`update_xc_lb_certificate`)**
Manages `PUT` and `POST` requests to the XC API to update or create certificate objects.

Flow:
1. Attempts a `PUT` request to update the certificate object.
2. Fallbacks to a `POST` request to create the object if it does not exist (404).
3. Logs and raises exceptions for any errors.

Endpoints:
- **PUT**:
  ```plaintext
  https://{tenant_name}.console.ves.volterra.io/api/config/namespaces/{namespace}/certificates/{cert_name}
  ```
- **POST**:
  ```plaintext
  https://{tenant_name}.console.ves.volterra.io/api/config/namespaces/{namespace}/certificates
  ```

---

## **Log Outputs**

### **Success: PUT**
```plaintext
CertbotLogger: INFO: Successfully obtained certificate with Certbot: example.internal
CertbotLogger: INFO: Copied certificate to: ./example.internal/cert.pem
CertbotLogger: INFO: Copied private key to: ./example.internal/privkey.pem
CertbotLogger: INFO: Sending PUT request to XC API: https://my-tenant.console.ves.volterra.io/api/config/namespaces/demo-namespace/certificates/example-cert
CertbotLogger: INFO: XC LB certificate updated successfully: 200
```

### **Fallback to POST**
If the PUT request fails (404):
```plaintext
CertbotLogger: INFO: Sending PUT request to XC API: https://my-tenant.console.ves.volterra.io/api/config/namespaces/demo-namespace/certificates/test-ca
CertbotLogger: INFO: Certificate object not found; attempting to create a new object using POST
CertbotLogger: INFO: Sending POST request to create a new certificate object: https://my-tenant.console.ves.volterra.io/api/config/namespaces/demo-namespace/certificates
CertbotLogger: INFO: New certificate object created successfully: 201
```

### **Error: POST Fails**
If the POST request fails due to invalid JSON:
```plaintext
CertbotLogger: ERROR: Error creating new certificate object: 400 - {"error":"Invalid JSON structure"}
```

---

## **Error Handling**

The script handles errors in the following areas:
1. **Certbot Errors**:
   - Logs any issues during certificate generation or renewal.

2. **XC API Errors**:
   - Logs response status codes and body for failed PUT or POST requests.

3. **File Errors**:
   - Raises exceptions if required files (`cert.pem`, `privkey.pem`) are missing.

---

## **Considerations**

1. **Network and Port Access**:
   - Ensure port 80 is free when using Certbot standalone mode.
   
2. **CA Certificate Trust**:
   - Confirm the custom ACME server’s CA certificate (`REQUESTS_CA_BUNDLE`) is valid.

3. **API Token Permissions**:
   - Ensure the XC API token provides necessary permissions for `PUT` and `POST` endpoints.

---

## **Script Workflow**

1. Load configuration from `acme-xc.conf`.
2. Obtain or renew a certificate using Certbot (`certonly` mode).
3. Base64 encode the certificate (`cert.pem`) and private key (`privkey.pem`).
4. Copy the files to the `{domain}` directory in the current working directory.
5. Attempt to update the certificate object with a `PUT` request.
6. If object creation is required, send a `POST` request to create a new certificate object.