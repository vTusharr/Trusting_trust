FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git ca-certificates python3 \
      libpam0g-dev libpam-modules bison byacc \
      && rm -rf /var/lib/apt/lists/*

WORKDIR /work
