FROM python:3.8

ARG BUILD_ENV
ENV PYTHONUNBUFFERED 1
# # Don't write .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# installing sfdx
COPY ./docker/utility/install_sfdx.sh /app/docker/utility/install_sfdx.sh
RUN /app/docker/utility/install_sfdx.sh
# ENV "0123456789101112"
COPY . /app
WORKDIR /app

RUN pip install --no-cache --upgrade pip
RUN if [ "${BUILD_ENV}" = "production" ] ; then pip install --no-cache -r /app/requirements.txt ; else pip install --no-cache -r /app/requirements_dev.txt ; fi
ENV CUMULUSCI_KEY "0123456789101112"

