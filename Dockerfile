# syntax=docker/dockerfile:1
FROM debian:unstable-slim
RUN mkdir /tsuki
COPY . /tsuki/
RUN ln -snf /usr/share/zoneinfo/US/Pacific /etc/localtime && echo 'US/Pacific' > /etc/timezone

RUN apt update
RUN apt install -y postgresql redis python3-pip python3-venv ffmpeg libsm6 libxext6 whois rabbitmq-server chromium

WORKDIR "/tsuki"
RUN python3 -m pip install --user -r requirements.txt

RUN python3 patch_vt.py
RUN bash -c "service postgresql start; sleep 10 && su postgres -c 'psql -f /tsuki/docker.sql'"

CMD ["bash", "-c", "service redis-server start && service postgresql start && service rabbitmq-server start && python3 main.py"]
