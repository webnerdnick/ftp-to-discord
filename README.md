# Python FTP server with Discord webhook

I wanted a simple way of getting snapshots from my Amcrest POE camera motion alerts into a discord channel I use for alerting. This container runs a simple Python FTP server and posts any uploaded image to a Discord channel via webhook. Once the image is posted, it is deleted from the FTP server to keep space at a minimum.

## Quick start

1. Create a webhook in Discord and copy the URL.
2. Create a `.env` file (example below).
3. Run the container.

```bash
docker compose up --build
```

## .env example

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/XXX/YYY
FTP_USER=ftp
FTP_PASS=ftp
FTP_PUBLIC_HOST=your.public.ip.or.host
DISCORD_MESSAGE=New image upload
```

## FTP client

Connect to port 21 with the user/password above. Uploaded images (jpg/png/gif/webp, etc) will be posted to Discord.

## Notes

- Passive ports default to 30000-30010; expose them in your firewall.
- Set `FTP_PUBLIC_HOST` when the server is behind NAT so passive mode returns the correct address.
