FROM python:3.7

RUN mkdir /storage

ADD bot/terra_node_bot.py /
ADD bot/constants.py /
ADD bot/helpers.py /
ADD bot/jobs.py /
ADD requirements.txt/ /

RUN pip install -r requirements.txt

CMD [ "python3", "./terra_node_bot.py" ]
