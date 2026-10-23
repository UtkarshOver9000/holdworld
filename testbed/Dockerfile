FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends asterisk sipp ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY asterisk/ /etc/asterisk/
COPY sipp/ /test/
EXPOSE 5060/udp 10000-10020/udp
