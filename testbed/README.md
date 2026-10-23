# Local SIP queue testbed

This optional Docker testbed runs Asterisk `app_queue` and uses SIPp to create background calls. It is a protocol smoke-test harness, not yet a generated copy of every Python IVR tree. It uses no public phone number and is separate from the static Vercel dashboard.

```sh
docker compose up --build -d asterisk
docker compose --profile load run --rm loadgen
docker compose down
```

The host must have Docker with Compose v2. UDP 5060 and RTP 10000–10020 are exposed for local SIP/RTP tests. Keep this testbed behind a firewall; the sample PJSIP endpoint intentionally has no authentication and must not be exposed to the public internet. The current development environment has no Docker/Asterisk/SIPp installation, so this configuration has not been executed here.
