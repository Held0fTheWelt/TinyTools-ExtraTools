FROM node:24-alpine

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY packages ./packages
COPY frontend ./frontend

RUN pnpm install --filter @aiagmw/frontend... --frozen-lockfile=false

EXPOSE 5173
CMD ["pnpm", "--filter", "@aiagmw/frontend", "dev", "--host", "0.0.0.0"]
