import imghdr
import json
import mimetypes
import os
import threading
import time
from pathlib import Path

import requests
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tiff",
    ".webp",
}


def parse_pasv_ports(value: str | None) -> range | None:
    if not value:
        return None
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("PASV_PORTS must be in the form START-END")
    start, end = (int(part) for part in parts)
    if start > end:
        raise ValueError("PASV_PORTS start must be <= end")
    return range(start, end + 1)


def is_image(path: str) -> bool:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return True
    return imghdr.what(path) is not None


def post_to_discord(path: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("DISCORD_WEBHOOK_URL not set; skipping Discord upload")
        return

    filename = Path(path).name
    content = os.getenv("DISCORD_MESSAGE", "New image upload")
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    with open(path, "rb") as handle:
        files = {"files[0]": (filename, handle, mime_type)}
        data = {"payload_json": json.dumps({"content": content})}
        response = requests.post(webhook, data=data, files=files, timeout=15)

    if response.status_code >= 300:
        print(f"Discord webhook failed ({response.status_code}): {response.text}")
        return

    try:
        os.remove(path)
    except OSError as exc:
        print(f"Failed to delete uploaded file {path}: {exc}")


processed_lock = threading.Lock()
processed_images: set[str] = set()


def mark_processed(path: str) -> bool:
    with processed_lock:
        if path in processed_images:
            return False
        processed_images.add(path)
    return True


def scan_for_images(root: str, interval: float) -> None:
    while True:
        for base, _, files in os.walk(root):
            for name in files:
                path = os.path.join(base, name)
                if not is_image(path):
                    continue
                if not mark_processed(path):
                    continue
                thread = threading.Thread(target=post_to_discord, args=(path,), daemon=True)
                thread.start()
        time.sleep(interval)


class ImageUploadHandler(FTPHandler):
    def on_file_received(self, file: str) -> None:
        if is_image(file):
            if mark_processed(file):
                thread = threading.Thread(target=post_to_discord, args=(file,), daemon=True)
                thread.start()
        else:
            print(f"Non-image upload received: {file}")


if __name__ == "__main__":
    ftp_user = os.getenv("FTP_USER", "ftp")
    ftp_pass = os.getenv("FTP_PASS", "ftp")
    ftp_home = os.getenv("FTP_HOME", "/data")
    ftp_port = int(os.getenv("FTP_PORT", "21"))
    pasv_ports = parse_pasv_ports(os.getenv("PASV_PORTS", "30000-30010"))
    public_host = os.getenv("FTP_PUBLIC_HOST")
    scan_interval = float(os.getenv("SCAN_INTERVAL", "5"))

    os.makedirs(ftp_home, exist_ok=True)

    authorizer = DummyAuthorizer()
    authorizer.add_user(ftp_user, ftp_pass, ftp_home, perm="elradfmwMT")

    handler = ImageUploadHandler
    handler.authorizer = authorizer
    handler.banner = "Python FTP server with Discord webhook"

    if pasv_ports:
        handler.passive_ports = pasv_ports
    if public_host:
        handler.masquerade_address = public_host

    server = FTPServer(("0.0.0.0", ftp_port), handler)
    print(f"FTP server listening on 0.0.0.0:{ftp_port}")
    if pasv_ports:
        print(f"Passive ports: {pasv_ports.start}-{pasv_ports.stop - 1}")

    scanner = threading.Thread(target=scan_for_images, args=(ftp_home, scan_interval), daemon=True)
    scanner.start()

    server.serve_forever()
