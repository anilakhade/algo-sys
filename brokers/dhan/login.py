import os
import logging
import time
import urllib.request
import socket
from dhanhq import DhanLogin, DhanContext, dhanhq

_original_getaddrinfo = socket.getaddrinfo
def _forced_ipv4_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = _forced_ipv4_getaddrinfo

logger = logging.getLogger(__name__)

class DhanAuth:
    def __init__(self, client_id: str, pin: str, totp_secret: str):
        self.client_id = client_id
        self.pin = pin
        self.totp_secret = totp_secret
        self.logger = logger
        self.login_client = DhanLogin(self.client_id)
        self.client = None
        self.access_token = None

    def execute(self) -> str:
        import hmac
        import hashlib
        import struct

        for attempt in range(1, 4):
            try:
                secret = self.totp_secret.replace(" ", "").upper()
                key = __import__('base64').b32decode(secret, casefold=True)
                msg = struct.pack(">Q", int(time.time()) // 30)
                hn = hmac.new(key, msg, hashlib.sha1).digest()
                o = hn[19] & 15
                token = str((struct.unpack(">I", hn[o:o+4])[0] & 2147483647) % 1000000).zfill(6)

                self.logger.info(f"Generating security token (Attempt {attempt}/3)...")
                auth_data = self.login_client.generate_token(self.pin, token)

                if auth_data and isinstance(auth_data, dict) and "accessToken" in auth_data:
                    self.access_token = auth_data["accessToken"]
                    context = DhanContext(self.client_id, self.access_token)
                    self.client = dhanhq(context)
                    self.logger.info(f"Login successful | Client: {self.client_id}")
                    return self.access_token
                
                self.logger.warning(f"Login attempt {attempt} failed: {auth_data}")
                time.sleep(30)

            except Exception as e:
                self.logger.error(f"Handshake exception on attempt {attempt}: {e}")
                time.sleep(5)

        return None

    def get_client(self):
        return self.client

    def get_ip_list(self) -> dict:
        if not self.access_token:
            return {}
        try:
            response = self.login_client.get_ip(self.access_token)
            return response if isinstance(response, dict) else {}
        except Exception:
            return {}

    def sync_current_ip(self) -> bool:
        if not self.access_token:
            return False
        try:
            current_ip = urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf8').strip()
            self.logger.info(f"Detected local public system IP: {current_ip}")
            
            server_registry = self.get_ip_list()
            data_block = server_registry.get("data", {}) if isinstance(server_registry, dict) else {}
            
            primary_ip = data_block.get("primaryIP", "")
            orders_allowed = data_block.get("ordersAllowed", False)

            # Fixed: Explicitly compare against the locked primary IP slot rather than the whole string
            if current_ip == primary_ip and orders_allowed:
                self.logger.info("System IP matches authorized primary slot cleanly. Ready.")
                return True

            self.logger.info(f"IP Mismatch confirmed. Updating server registry slot from '{primary_ip}' to '{current_ip}'...")
            
            # Fire the explicit modification request to change the server configuration
            response = self.login_client.modify_ip(self.access_token, current_ip, "PRIMARY")
            self.logger.info(f"Server Update Response: {response}")
            return True
            
        except Exception as e:
            self.logger.error(f"IP synchronization protocol failed: {e}")
            return False

    def logout(self) -> bool:
        self.client = None
        self.access_token = None
        self.logger.info("Dhan session cleared")
        return True