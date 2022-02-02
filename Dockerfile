# Example/Test Dockerfile using pipt sync-system
# This demonstrates how to install dependencies without a venv
# Usage:
#     Prerequisites: A pipt managed project. Run `pipt shell` to set
#       up one.
#
#     Build:
#       docker build -f Dockerfile -t pipt-python-test .
#     Enter bash in container:
#       docker run -it pipt-python-test bash


FROM python:3.10.2-buster as base

# Copy relevant files
COPY ./pipt_locks.env /app/pipt_locks.env
COPY ./pipt_config.env /app/pipt_config.env
COPY ./requirements-base.txt /app/requirements-base.txt
COPY ./requirements.txt /app/requirements.txt
COPY ./requirements-dev.txt /app/requirements-dev.txt

# Install pipt by copying it from local dir
COPY ./pipt /app/pipt

WORKDIR /app

# Install dependencies without venv using pipt sync-system subcommand
RUN ./pipt sync-system --prod

## Alternatively install dependencies without pipt
## You have to set sync args manually, the pipt_config.env file will
## not be used:
# RUN python -m pip install -r requirements-base.txt
# RUN python -m piptools sync requirements-base.txt requirements.txt # requirements-dev.txt