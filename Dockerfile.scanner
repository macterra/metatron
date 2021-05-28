FROM python:3

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN sh install-ipfshttpclient.sh

CMD [ "python", "./scanner.py" ]
