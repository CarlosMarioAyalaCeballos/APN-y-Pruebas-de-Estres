FROM node:20-alpine

WORKDIR /usr/src/app
ENV NODE_ENV=production

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY src ./src

EXPOSE 3000
USER node
CMD ["node", "--require", "./src/tracing.js", "src/server.js"]
