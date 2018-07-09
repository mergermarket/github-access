FROM python:3 as base

ADD requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

WORKDIR /usr/local/app
ENV PYTHONPATH /usr/local/app




FROM base

ADD . .

ENTRYPOINT [ "python", "-m", "github_access" ]
