# Deploy de AMÉRICO con Docker / Coolify

Stack de 3 servicios sobre una imagen Python compartida + nginx:

| Servicio | Qué hace | Expone |
|----------|----------|--------|
| `bot` | Worker que opera en **paper** y escribe el estado (decisiones, fills, posiciones, equity) en SQLite. | — |
| `api` | FastAPI de solo lectura sobre el mismo SQLite. | `8000` (interno) |
| `web` | nginx que sirve el panel buildeado y proxea `/api/*` → `api:8000`. | `80` → público |

El SQLite vive en el volumen `americo-data` (`/data/americo.sqlite`), compartido entre `bot` (escribe) y `api` (lee). El panel llama a `/api/*` **same-origin**, así que no hay CORS ni un segundo dominio que exponer.

```
navegador ──▶ web (nginx :80) ──┬─ archivos estáticos del panel
                                └─ /api/* ──▶ api (uvicorn :8000) ──┐
                                                                    ├─▶ volumen americo-data (/data/americo.sqlite)
                              bot (loop) ───────────────────────────┘
```

## Probar local

```bash
cp .env.example .env        # editá BOT_SYMBOL / ANTHROPIC_API_KEY si querés
docker compose build
WEB_PORT=8080 docker compose up
```

Abrí http://localhost:8080 — el panel aparece y se va poblando a medida que el bot decide. Pará con `Ctrl+C`; los datos quedan en el volumen.

## Deploy en Coolify

1. **Subí el repo a GitHub** (Coolify clona desde ahí).
2. En Coolify: **New Resource → Docker Compose**, apuntá al repositorio y a `docker-compose.yml`.
3. **Variables de entorno** (Coolify las inyecta al `compose`):
   - `BOT_SYMBOL` — el par a operar (ej. `BTC/USDT`).
   - `ANTHROPIC_API_KEY` — *opcional*; activa el filtro IA. Requiere además poner `ai.enabled: true` en `config.docker.yaml`. Sin key el bot corre en solo-reglas.
   - `OKX_API_KEY` / `OKX_API_SECRET` / `OKX_API_PASSWORD` — *opcional*; solo si cambiás `broker.kind` a `okx_demo`.
   - `AMERICO_CORS_ORIGINS` — dejalo en `*` (el panel es same-origin).
4. **Dominio:** asigná tu dominio al servicio **`web`** (puerto `80`). El proxy de Coolify lo enruta; el panel resuelve `/api/*` solo. No expongas `api` directo.
5. **Persistencia:** el volumen `americo-data` ya está declarado; Coolify lo mantiene entre redeploys. El historial del bot sobrevive.

## Configuración

`config.docker.yaml` es la config de producción (la edita el repo, no el entorno):
- `broker.kind: paper` — simulación con datos reales de OKX. Cambiá a `okx_demo` para ejecutar contra el order book demo (necesita las `OKX_*`).
- `ai.enabled: false` — poné `true` + `ANTHROPIC_API_KEY` para el filtro IA (veta entradas dudosas; ante cualquier error cae a solo-reglas).
- `timeframe`, `strategy`, `risk` — ajustá a gusto; el `bot` y la `api` releen el archivo al reiniciar.

## Notas

- **Un símbolo por worker.** El servicio `bot` opera el par de `BOT_SYMBOL`. Para varios pares, duplicá el servicio `bot` con otro símbolo y el mismo volumen.
- **SQLite en volumen compartido** alcanza para esta escala (escritura cada `loop_interval_seconds`). Si subís frecuencia o agregás workers, migrá a Postgres.
- **Las llaves nunca van al repo.** `ANTHROPIC_API_KEY` y las `OKX_*` salen siempre del entorno (Coolify) o de un `.env` local (gitignored).
