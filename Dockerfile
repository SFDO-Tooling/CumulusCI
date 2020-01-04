FROM python:3.8

ENV PYTHONUNBUFFERED 1
# # Don't write .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# installing sfdx
COPY ./docker/utility/install_sfdx.sh /app/docker/utility/install_sfdx.sh
RUN /app/docker/utility/install_sfdx.sh

# COPY ./requirements.txt /app/requirements.txt
# COPY ./requirements_dev.txt /app/requirements_dev.txt
# # installing python related dependencies with pip
# # COPY  ./README.rst /app/README.rst
# COPY ./setup.py /app/setup.py

# installing yarn dependencies
# copying rest of working directory to /app folder

COPY . /app
# WORKDIR /app


WORKDIR /app

RUN pip install --no-cache --upgrade pip
RUN if [ "${BUILD_ENV}" = "production" ] ; then pip install --no-cache -r /app/requirements.txt ; else pip install --no-cache -r /app/requirements_dev.txt ; fi

