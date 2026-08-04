# --- Étape 1 : build Vite ---
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# L'URL de l'API est injectée à la compilation dans le bundle client
# (Vite remplace `import.meta.env.VITE_API_URL` par la valeur au build,
# pas au runtime — c'est spécifique aux frontends statiques compilés).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# --- Étape 2 : service statique par nginx ---
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
