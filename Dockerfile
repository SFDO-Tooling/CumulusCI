FROM python:3.8
ENV CHROMEDRIVER_VERSION 95.0.4638.54

ARG BUILD_ENV
ENV PYTHONUNBUFFERED 1
# # Don't write .pyc files
ENV PYTHONDONTWRITEBYTECODE 1

ENV CHROMEDRIVER_VERSION 95.0.4638.54

RUN mkdir -p /app/.apt/usr/bin

# Set up the Chrome PPA
# Update the package list and install chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> \
    /etc/apt/sources.list.d/google.list \
    && apt-get update -y \
    && apt-get install --no-install-recommends -y \
    google-chrome-stable \
    jq \
    && rm -rf /var/lib/apt/lists/*

COPY ./docker/utility/wrap_chrome_binary.sh /app/docker/utility/wrap_chrome_binary.sh
RUN /app/docker/utility/wrap_chrome_binary.sh
RUN ln -fs /usr/bin/google-chrome /usr/bin/chrome

# Set up Chromedriver Environment variables
ENV CHROMEDRIVER_DIR /chromedriver
RUN mkdir $CHROMEDRIVER_DIR
# installing sfdx
COPY ./docker/utility/install_sfdx.sh /app/docker/utility/install_sfdx.sh
RUN /app/docker/utility/install_sfdx.sh

# Update PATH
ENV PATH $CHROMEDRIVER_DIR:./node_modules/.bin:$PATH:/app/sfdx/bin

COPY . /app
WORKDIR /app

RUN pip install --no-cache --upgrade pip
RUN if [ "${BUILD_ENV}" = "production" ] ; then pip install --no-cache -r /app/requirements.txt ; else pip install --no-cache -r /app/requirements_dev.txt ; fi
ENV CUMULUSCI_KEY "0123456789101112"

