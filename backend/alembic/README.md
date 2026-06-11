The MVP initializes tables from SQLAlchemy metadata for fast local setup.

For production, configure Alembic with `app.db.session.Base.metadata` and generate the initial revision:

```powershell
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

