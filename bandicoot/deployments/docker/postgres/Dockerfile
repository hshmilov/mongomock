FROM  postgres:12.1-alpine as builder

ENV POSTGRES_USER postgres
ENV POSTGRES_PASSWORD changeme
ENV POSTGRES_DB axonius

ADD create_db.sql /docker-entrypoint-initdb.d
ADD indexes.sql /docker-entrypoint-initdb.d
ADD functions.sql /docker-entrypoint-initdb.d
ADD conf.sql      /docker-entrypoint-initdb.d
