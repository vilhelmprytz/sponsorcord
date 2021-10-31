FROM python:3.10-slim-bullseye

WORKDIR /var/www/app

# pipenv virtual environment
RUN mkdir .venv

# install dependencies
RUN pip install --upgrade pip
RUN pip install pipenv

COPY . /var/www/app

RUN pipenv install --deploy

ENV PATH="/var/www/app/.venv/bin:$PATH"
EXPOSE 5000

CMD [ "/var/www/app/entrypoint.sh" ]
