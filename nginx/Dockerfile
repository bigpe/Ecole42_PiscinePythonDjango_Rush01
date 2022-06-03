FROM nginx

WORKDIR /app

RUN apt update && apt install -y openssl
RUN openssl genrsa -aes256 -passout pass:gsahdg -out server.pass.key 4096
RUN openssl rsa -passin pass:gsahdg -in server.pass.key -out server.key
RUN rm server.pass.key
RUN openssl req -new -key server.key -subj "/C=RU/ST=Moscow/L=Moscow/O=Dis/CN=www.example.com"  -out server.csr
RUN openssl x509 -req -sha256 -days 365 -in server.csr -signkey server.key -out server.crt
