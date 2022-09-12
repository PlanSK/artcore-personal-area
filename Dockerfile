# Construct builder

FROM python:3.10.6-alpine as builder

WORKDIR /usr/src/webapp

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add --no-cache mariadb-dev
RUN pip install --upgrade pip

COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/webapp/wheels -r requirements.txt
RUN apk del build-deps && rm -rf /var/cache/apk/*

# Construct production
FROM python:3.10.6-alpine

RUN mkdir /home/implementer
RUN addgroup -S implementer && adduser -S implementer -G implementer

ENV HOME=/home/implementer
ENV APP_HOME=/home/implementer/web
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles
RUN mkdir $APP_HOME/mediafiles
WORKDIR $APP_HOME

RUN apk update && apk add --no-cache mariadb-connector-c-dev
COPY --from=builder /usr/src/webapp/wheels /wheels
COPY --from=builder /usr/src/webapp/requirements.txt .
RUN pip install --no-cache /wheels/*
RUN rm -rf /var/cache/apk/*

COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' $APP_HOME/entrypoint.sh
RUN chmod +x $APP_HOME/entrypoint.sh

COPY . $APP_HOME
RUN chown -R implementer:implementer $APP_HOME
USER implementer

ENTRYPOINT ["/home/implementer/web/entrypoint.sh"]
