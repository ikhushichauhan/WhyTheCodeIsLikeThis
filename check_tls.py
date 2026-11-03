import os
import ssl
import socket
import sys
import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

host = urlparse(os.getenv("NEO4J_URI")).hostname

print("Python:", sys.version)
print("OpenSSL:", ssl.OPENSSL_VERSION)
print("Host loaded:", bool(host))
print("Local UTC time:", datetime.datetime.now(datetime.timezone.utc))

ctx = ssl.create_default_context()

try:
    with socket.create_connection((host, 7687), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            print("TLS OK:", tls.version())
            print("Issuer:", tls.getpeercert().get("issuer"))

except ssl.SSLCertVerificationError as e:
    print("Verification code:", e.verify_code)
    print("Verification message:", e.verify_message)

except Exception as e:
    print(type(e).__name__, e)