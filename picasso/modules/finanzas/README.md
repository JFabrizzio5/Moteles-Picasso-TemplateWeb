# Finanzas

Modular layout: one package per concern, each re-exporting its public names.

## Responsibility

<!-- One paragraph: what this module owns. If you cannot write it in one
     paragraph, the module is doing two jobs. -->


## Fields

None yet (`--bare`). Add each one to the entity, the wire models and the
public DTO -- or regenerate with `jfast new module finanzas --force --fields
"..."` before anything else is written here.

## Structure

| Path | Role | May import |
| --- | --- | --- |
| `api/` | HTTP surface. Validation in, serialization out. | FastAPI, the services |
| `services/` | Orchestration and domain rules. | models, repositories, validations |
| `validations/` | Business rules a schema cannot express. | the framework errors |
| `repositories/` | Data access. Extends `BaseRepository`. | SQLAlchemy, the entity |
| `models/` | `finanzas_entity.py` = SQLAlchemy, `finanzas_models.py` = Pydantic. | SQLAlchemy, Pydantic |
| `enums.py` | Values only this module speaks. | nothing |
| `public.py` | The only file other modules may import. Takes a session and `tenant_id`, returns DTOs. | repositories, services, models |

Import from the package, never from the file inside it: `from ..services
import FinanzasService`, not `from ..services.finanzas_service import
FinanzasService`. Splitting a file in two then stays a local edit.

The import direction points inward. `api` knows `services`, `services` knows
`repositories` and `validations`, and `models` knows nothing about either.

## Validations

`validations/` holds the rules Pydantic cannot state, because they need
something beyond the payload -- the rest of the table, or the current state of
the row. Shape stays in `models/`: lengths, types, what may be omitted. If a
check only reads the payload, it is a `Field` constraint, not a rule.

None yet.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/finanzases` | List, paginated |
| GET | `/finanzases/{id}` | Fetch one |
| POST | `/finanzases` | Create |
| PATCH | `/finanzases/{id}` | Partial update |
| DELETE | `/finanzases/{id}` | Delete |

## Wiring

```python
from modules.finanzas import router as finanzas_router

app = create_app(routers=[finanzas_router])
```

## Migration

This module ships a table. Generate the migration before first run:

```bash
jfast exec -- alembic revision --autogenerate -m "add finanzases"
jfast exec -- alembic upgrade head
```


## Invariants

<!-- Rules the code cannot express on its own. Delete this section if there
     are none; do not leave the placeholder text. -->
