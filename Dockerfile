FROM python:3.9-slim-buster
WORKDIR /cndproject
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY app.py /cndproject
COPY templates/ /cndproject/templates
ENV FLASK_APP=app.py
CMD ["flask", "run","--host=0.0.0.0","--port=8080"]