# CRUD Students & Pets (FastAPI)

Proyecto FastAPI con CRUD de estudiantes y mascotas, persistencia en PostgreSQL mediante SQLAlchemy y migraciones versionadas con Alembic. PostgreSQL y pgAdmin se ejecutan con Docker Compose.

## Tecnologías

- Python 3.13
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL 17 + pgAdmin en Docker
- HTML + JS + Tailwind CSS (frontend estático)

## Resumen funcional

La API expone operaciones CRUD completas sobre estudiantes y mascotas:

**Estudiantes** — `/api/students`

- **Crear**: `POST /api/students` (opcionalmente con `pets[]` para crear el estudiante y sus mascotas en una sola petición)
- **Listar**: `GET /api/students`
- **Buscar por id**: `GET /api/students/:id`
- **Actualizar**: `PATCH /api/students/:id`
- **Eliminar**: `DELETE /api/students/:id` (elimina también sus mascotas)

**Mascotas** — `/api/students/:studentId/pets`

- **Listar**: `GET /api/students/:studentId/pets`
- **Crear**: `POST /api/students/:studentId/pets`
- **Actualizar**: `PATCH /api/students/:studentId/pets/:petId`
- **Eliminar**: `DELETE /api/students/:studentId/pets/:petId`

### Alta de estudiante con mascotas

`POST /api/students` acepta un arreglo opcional `pets`:

```json
{
	"name": "Ana Pérez",
	"username": "ana_perez",
	"email": "ana@example.com",
	"age": 21,
	"pets": [
		{ "name": "Firulais", "species": "perro", "age": 3 },
		{ "name": "Michi", "species": "gato" }
	]
}
```

Si no se envía `pets` (o se envía vacío), el comportamiento es exactamente el mismo de antes.

> **Transacciones:** crear un estudiante con mascotas usa una única sesión y un único commit. Si falla cualquier escritura, se revierten el estudiante y todas sus mascotas. Eliminar un estudiante elimina sus mascotas en la misma transacción mediante la relación y la clave foránea con `ON DELETE CASCADE`. Los repositorios usan `flush()`; los servicios controlan commit y rollback.

### Modelo de datos

| Estudiante | Mascota        |
| ---------- | -------------- |
| id (UUID)  | id (UUID)      |
| name       | studentId      |
| username   | name           |
| email      | species        |
| age        | age (opcional) |
| createdAt  | createdAt      |
| updatedAt  | updatedAt      |

### Validación y unicidad

La validación se realiza con Pydantic v2:

- `name` (estudiante): texto de 3 a 100 caracteres, sin etiquetas HTML.
- `username`: texto de 3 a 30 caracteres, solo minúsculas, números y guiones bajos (`^[a-z0-9_]+$`).
- `email`: dirección de correo electrónico válida.
- `age` (estudiante): entero entre 18 y 99.
- `name` / `species` (mascota): texto de 1 a 50 caracteres, sin etiquetas HTML.
- `age` (mascota): entero entre 0 y 100 (opcional).

Unicidad (rechazado con `409 Conflict`):

- Estudiante: `email` y `username` deben ser únicos.
- Mascota: `name` debe ser único dentro de un mismo estudiante.

## Estándar de respuesta JSON

Toda respuesta de la API — exitosa o de error — usa el mismo **envelope** `ApiResponse`, definido en [`app/shared/api_response.py`](app/shared/api_response.py). Esto permite que el frontend interprete cualquier respuesta de forma uniforme.

### Envelope común

| Campo       | Tipo                | Descripción                                                               |
| ----------- | ------------------- | ------------------------------------------------------------------------- |
| `code`      | `number`            | Código de estado HTTP (coincide con el status de la respuesta).           |
| `success`   | `boolean`           | `true` si la operación se completó, `false` si hubo error.                |
| `message`   | `string`            | Resumen legible del resultado (varía según el método HTTP).               |
| `timestamp` | `string`            | Fecha/hora en ISO 8601 de la respuesta.                                   |
| `data`      | `object \| null`    | Datos de la operación. Presente en éxito; `null` en errores.              |
| `error`     | `string` (opcional) | Mensaje de error para errores simples (404, 500).                         |
| `errors`    | `object` (opcional) | Errores por campo para validación (400) y conflicto (409). Ver más abajo. |

### Respuestas de éxito

Un middleware global ([`api_response.py`](app/shared/api_response.py)) envuelve el retorno de los controladores en `data`:

- **Recurso único** (`GET :id`, `POST`, `PATCH`, `DELETE`): `data` contiene la entidad directamente.
- **Listado** (`GET` colección): `data` contiene `{ total, items }`.

```json
{
  "code": 201,
  "success": true,
  "message": "Recurso creado",
  "timestamp": "2026-09-09T16:49:33.368Z",
  "data": {
    "id": "c3600646-abe8-4be3-8096-d6ad629388e2",
    "name": "Juan Pérez",
    "username": "juanperez",
    "email": "juan@example.com",
    "age": 20,
    "createdAt": "2026-09-09T16:49:33.000Z",
    "updatedAt": "2026-09-09T16:49:33.000Z"
  }
}
```

`message` según el método HTTP:

| Método   | `message`             | `code` |
| -------- | --------------------- | ------ |
| `GET`    | `Operación exitosa`   | 200    |
| `POST`   | `Recurso creado`      | 201    |
| `PATCH`  | `Recurso actualizado` | 200    |
| `DELETE` | `Recurso eliminado`   | 200    |

### Errores simples (404, 500)

Los errores sin detalle por campo usan el campo `error`:

```json
{
  "code": 404,
  "success": false,
  "message": "Estudiante no encontrado",
  "timestamp": "2026-09-09T16:49:53.816Z",
  "data": null,
  "error": "Estudiante no encontrado"
}
```

### Validación (400) y conflicto (409)

Ambos casos comparten el **mismo esquema** para que el frontend los trate igual: el campo `errors` es un mapa `{ campo: { message } }`, donde la clave es el nombre del campo que falla.

```json
{
  "code": 400,
  "success": false,
  "message": "Error de validación",
  "timestamp": "2026-09-09T16:39:30.397Z",
  "data": null,
  "errors": {
    "name": { "message": "El nombre debe tener entre 3 y 100 caracteres" },
    "email": { "message": "El correo electrónico no es válido" }
  }
}
```

```json
{
  "code": 409,
  "success": false,
  "message": "Conflicto con datos existentes",
  "timestamp": "2026-09-09T16:49:45.110Z",
  "data": null,
  "errors": {
    "email": { "message": "El correo electrónico ya está en uso" }
  }
}
```

- `400 Bad Request`: cuando falla la validación. Los DTOs replican las reglas y mensajes de class-validator (NestJS) en español; el handler global ([`exceptions.py`](app/shared/exceptions.py)) convierte los errores al mapa `{ campo: { message } }` (si un campo falla varias reglas, los mensajes se concatenan con `", "`; las propiedades no permitidas devuelven `errors: {}`).
- `409 Conflict`: cuando se viola una restricción de unicidad. Los servicios lanzan una `HTTPException` con el mismo mapa `errors`, por lo que es indistinguible de una validación a nivel de estructura.

### Interpretación en el frontend

El cliente estático (`public/`) consume este estándar de forma uniforme:

- `public/js/api.js` expone `api()` (hace `fetch` y devuelve `data` en éxito o lanza el envelope en error) y `normalizeErrors()` (convierte `{ campo: { message } }` en `{ campo: message }`).
- En los formularios, si la respuesta trae `errors`, cada mensaje se muestra bajo su input correspondiente; si trae `error`, se muestra como notificación global (toast).

## Contexto técnico

- **Backend**: FastAPI
- **Persistencia**: PostgreSQL con volumen Docker; los datos sobreviven al reinicio de la API y de los contenedores
- **Validación**: Pydantic v2
- **Frontend**: archivos estáticos en `public/` (Alpine.js + Tailwind CSS + vanilla-sonner, vía CDN)
- **Gestor de dependencias**: uv
- **Documentación**: Swagger en `/docs`

## Ejecución local

Requisitos: Docker Desktop, uv y Python 3.13 o superior.

1. Copiar `.env.example` a `.env` solamente si todavía no existe este último. Ajustar usuario, contraseña, base y puertos; `DATABASE_URL` debe coincidir con `POSTGRES_*`. No versionar `.env`.
2. Instalar las dependencias:

    ```powershell
    uv sync
    ```

3. Iniciar PostgreSQL y pgAdmin:

    ```powershell
    docker compose up -d --wait
    ```

4. Aplicar las migraciones:

    ```powershell
    uv run alembic upgrade head
    ```

5. Iniciar la API:

    ```powershell
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
    ```

- Aplicación: http://localhost:3000
- Swagger: http://localhost:3000/docs
- pgAdmin: http://localhost:5050, o el puerto definido en `PGADMIN_PORT`.

En pgAdmin, ingresar con `PGADMIN_DEFAULT_EMAIL` y `PGADMIN_DEFAULT_PASSWORD` del `.env`. Registrar PostgreSQL con host `db`, puerto interno `5432` y los valores de `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`. La API ejecutada en Windows usa `localhost` y el puerto publicado `POSTGRES_PORT`.

El volumen local existente fue inicializado con PostgreSQL 17; `compose.yml` usa esa misma versión. No utilizar `docker compose down -v` para reiniciar: esa opción elimina los volúmenes. Reiniciar con `docker compose restart` o detener con `docker compose down`, sin `-v`.

## Verificación

Con PostgreSQL iniciado y `.env` configurado:

```powershell
uv run pytest -q
uv run alembic check
uv run ruff check app tests alembic/env.py alembic/versions/70e4dfb1ebe7_crear_pets_y_relacion_con_students.py
uv run ruff format --check app tests alembic/env.py alembic/versions/70e4dfb1ebe7_crear_pets_y_relacion_con_students.py
```

Las pruebas crean esquemas PostgreSQL temporales con nombres aleatorios y aplican las migraciones desde cero. Al terminar eliminan únicamente esos esquemas, sin usar las tablas de datos de la aplicación. El usuario configurado necesita permiso para crear esquemas.

Cubren CRUD, lectura desde sesiones nuevas, fechas de actualización, unicidad, pertenencia de mascotas, validación, cascada y rollback. Se fuerzan fallos después de un `flush()` tanto al crear como al eliminar: las pruebas comprueban primero las escrituras dentro de la transacción y después su reversión desde otra sesión.

Para demostrar manualmente el rollback en Swagger, enviar un estudiante nuevo con dos mascotas que tengan el mismo nombre: debe responder `409` y no guardar ni al estudiante ni sus mascotas. Volver a enviarlo con nombres distintos debe funcionar con el mismo usuario y correo del intento fallido.

## Comandos útiles

- `make install` — sincroniza dependencias con uv
- `make dev` — arranca uvicorn en modo reload
- `make lint` — ejecuta Ruff (con autocorrección)
- `make format` — formatea el código con Ruff
- `make format-check` — verifica el formato
- `make clean` — elimina `.venv`, cachés y artefactos

## Ejecución con Docker y PostgreSQL

1. Copiar las variables de entorno (el archivo `.env` no se sube a Git):
   `Copy-Item .env.example .env`
   Si el puerto 5432 ya está ocupado en tu PC, cambia `POSTGRES_PORT` y el puerto de `DATABASE_URL` en tu `.env` (por ejemplo a 5433).
2. Levantar PostgreSQL 17 y pgAdmin: `docker compose up -d`
3. Instalar dependencias: `uv sync`
4. Aplicar migraciones: `uv run alembic upgrade head`
5. Iniciar la API: `uv run uvicorn app.main:app --reload`
6. Documentación de la API: http://localhost:8000/docs
7. pgAdmin: http://localhost:5050. Al registrar el servidor usa host `db`, puerto `5432`, y el usuario y la clave de tu `.env`.
8. Tests: `uv run python -m pytest -v`

## Equipo

- Alonso (líder): Docker, compose y variables de entorno
- Jesús: base del ORM y Alembic
- Tomás: Student (modelo, repositorio, servicio y migración)
- Diego: Pet, relación con Student y transacciones