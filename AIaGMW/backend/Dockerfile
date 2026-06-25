FROM node:24-alpine

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY docs ./docs
COPY packages ./packages
COPY backend ./backend

RUN pnpm install --filter @aiagmw/backend... --frozen-lockfile=false

EXPOSE 3000
CMD ["pnpm", "--filter", "@aiagmw/backend", "start"]
