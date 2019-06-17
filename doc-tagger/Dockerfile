# Python support can be specified down to the minor or micro version
# (e.g. 3.6 or 3.6.3).
# OS Support also exists for jessie & stretch (slim and full).
# See https://hub.docker.com/r/library/python/ for all supported Python
# tags from Docker Hub.
FROM python:alpine

VOLUME /docs
ENV CA_DOC_TAGGGING_IN_DOCKER True

WORKDIR /app
ADD requirements.txt /app
RUN python3 -m pip install -r requirements.txt

ADD main.py /app

ENTRYPOINT ["python3", "main.py"]
