FROM ubuntu:latest
LABEL authors="caephas"

ENTRYPOINT ["top", "-b"]