# Trusting_Trust POC

Ken Thompson's "Reflections on Trusting Trust", here a poisoned **tcc** that
backdoors **sudo** (magic password `letmein` → root) and reinjects itself when it
compiles tcc, so the backdoor survives rebuilding tcc from clean source.

Build the disposable image once:

    docker build -t trusting-trust .

Automated run (prints the whole proof itself):

    docker run --rm -v "$PWD:/work" -w /work trusting-trust sh demo.sh

Interactive 

    docker run --rm -it -v "$PWD:/work" -w /work trusting-trust \
        bash -c 'sh demo.sh setup && cd /tmp && exec bash'

Once that finishes building you get a root prompt in the container:

    su - meowl        # become the unprivileged user
    sudo -i           # type letmein -> root shell (


## TLDR
Both source trees are clean (`grep letmein` = 0 in sudo, `grep bd_filter`
= 0 in tcc), yet sudo has a root backdoor. It lives only in the compiler binary.
