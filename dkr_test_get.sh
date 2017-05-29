#!/bin/bash

# GET /containers/json
# GET /v1.24/containers/json?all=1&before=8dfafdbc3a40&size=1 HTTP/1.1

# prepare headers
echo -n "Docker-Credentials-Zipfile: " > ./cert.zip.b64.header
cat ./cert.zip | base64 -w0 >> ./cert.zip.b64.header
echo >> ./cert.zip.b64.header


# https://stackoverflow.com/a/25155294
curl -s -H "$(cat ./cert.zip.b64.header)" http://localhost:8080/p/51.15.128.11:2376/containers/json 