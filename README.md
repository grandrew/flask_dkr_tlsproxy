# flask_dkr_tlsproxy
Flask based docker engine API TLS proxy microservice

Useful if you want to separate the API logic and the actual docker interface. Dockerized.

# Usage example

## Run the proxy 

### By hand

(use your wsgi here)

    export FLASK_APP=./flask_tlsproxy.py; /usr/bin/python2.7 -m flask run --host=0.0.0.0 --port=8080

### Docker image

TBD

## Zip the docker credentials folder

    eval "$(docker-machine env testmachine)"
    cd $DOCKER_CERT_PATH
    zip cert.zip ./*

## Create the header and make request through the proxy to docker

    echo -n "Docker-Credentials-Zipfile: " > ./cert.zip.b64.header
    cat ./cert.zip | base64 -w0 >> ./cert.zip.b64.header
    curl -s -H "$(cat ./cert.zip.b64.header)" http://localhost:8080/p/localhost:2376/containers/json 