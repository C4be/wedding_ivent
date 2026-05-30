#!/bin/bash

mkdir -p ~/certbot/conf/live/свадьба-дмитрий-и-наталья.рф
cat cert/certificate.crt cert/certificate_ca.crt > ~/certbot/conf/live/свадьба-дмитрий-и-наталья.рф/fullchain.pem
cp cert/certificate.key ~/certbot/conf/live/свадьба-дмитрий-и-наталья.рф/privkey.pem