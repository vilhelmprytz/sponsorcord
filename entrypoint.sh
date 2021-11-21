#!/bin/bash

RANDOM_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 50 | head -n 1)

if [[ "$SECRET_KEY" == "random" ]]; then
    export SECRET_KEY="$RANDOM_KEY"
fi

gunicorn --workers=4 --bind 0.0.0.0:"$PORT" app:app
