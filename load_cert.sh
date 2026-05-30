#!/bin/bash

mkdir -p ~/certbot/conf/live/wedding-site
cat cert/certificate.crt cert/certificate_ca.crt > ~/certbot/conf/live/wedding-site/fullchain.pem
cp cert/certificate.key ~/certbot/conf/live/wedding-site/privkey.pem