# Dockerfile
FROM python:3.7-stretch
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENV PORT 8080
ENV HOST 0.0.0.0
ENV API_VERSION '2020-04'
ENTRYPOINT ["python"]
CMD ["main.py", "local"]
