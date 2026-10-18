FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server file binutils coreutils procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash intern \
    && mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config
COPY build/output/ /
COPY malware/ /opt/malware/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
