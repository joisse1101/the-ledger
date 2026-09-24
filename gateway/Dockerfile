FROM nginx:alpine

# Self-signed certificate, generated once at image build time so there's no manual step. Docker's
# layer cache keeps it across rebuilds, so a phone that accepted it once isn't warned again until
# the image is rebuilt from scratch (or this layer changes). There's no stable hostname on a LAN to
# get a real certificate for, so every address is covered by the browser's one-time warning instead.
RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/certs \
    && openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
        -keyout /etc/nginx/certs/gateway.key -out /etc/nginx/certs/gateway.crt \
        -days 3650 -subj "/CN=the-ledger-gateway" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    && chmod 600 /etc/nginx/certs/gateway.key \
    && apk del openssl

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
