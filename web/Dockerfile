# --- build del SPA (Vite + React + TS) ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# `npm install` (no `npm ci`): el lockfile se genera en Windows y omite las
# optional deps wasm (@emnapi/*) que la imagen Linux/musl resuelve. install las
# completa sobre la marcha; ci fallaría por lockfile "fuera de sync".
RUN npm install --no-audit --no-fund
COPY . ./
# Base vacía: el panel llama a /api/* (mismo origen), y nginx lo proxea a la API.
ENV VITE_API_BASE=""
RUN npm run build

# --- servir con nginx ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
