FROM node:24-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_DEV_LOGIN=
ENV API_URL=http://api:8000
ENV NEXT_PUBLIC_DEV_LOGIN=$NEXT_PUBLIC_DEV_LOGIN
RUN npm run build
EXPOSE 3000
CMD ["sh", "-c", "npm start -- --hostname 0.0.0.0 --port ${PORT:-3000}"]
