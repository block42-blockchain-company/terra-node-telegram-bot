FROM python:3.7

RUN mkdir /storage

ADD bot /
ADD requirements.txt/ /


RUN pip install -r requirements.txt

CMD [ "python3", "./terra_node_bot.py" ]
