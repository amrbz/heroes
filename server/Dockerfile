FROM ubuntu

RUN mkdir /opt/web
WORKDIR /opt/web
RUN apt-get update

RUN apt-get install -y tar git curl nano wget dialog net-tools build-essential
RUN apt-get install -y python python-dev python-distribute python-pip
RUN apt-get update

RUN pip install --upgrade pip
COPY requirements.txt /opt/web
RUN pip install -r requirements.txt

ENV FLASK_CONFIG development

EXPOSE 80

CMD  python server.py
