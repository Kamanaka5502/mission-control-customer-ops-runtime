FROM node:22-alpine

ENV NODE_ENV=production

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

USER app

CMD ["npm", "run", "start"]
