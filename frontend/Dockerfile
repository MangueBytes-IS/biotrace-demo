FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* npm-shrinkwrap.json* ./

RUN npm ci

COPY . .

# O Vite grava VITE_* no bundle durante o build, não em runtime
ARG VITE_API_URL=http://127.0.0.1:5000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=build /app/dist dist

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
