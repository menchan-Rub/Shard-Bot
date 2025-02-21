FROM node:18-alpine

WORKDIR /app

# クライアントディレクトリの内容をコピー
COPY client/package*.json ./
RUN npm install

COPY client/ .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"] 