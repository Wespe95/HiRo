FROM python:3.11

COPY ./requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health