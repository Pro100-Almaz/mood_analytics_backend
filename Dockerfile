FROM python:3.11

ENV PYTHONUNBUFFERED 1
WORKDIR .

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5010

CMD ["flask", "run", "--host=0.0.0.0"]
