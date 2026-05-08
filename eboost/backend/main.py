from __future__ import annotations

from fastapi import FastAPI

from eboost.backend.routes import connect, happ, payments
from eboost.db.init import create_sqlite_schema_for_local_dev
from eboost.db.session import async_session_maker
from eboost.services.bootstrap import seed_defaults

app = FastAPI(title="eBooster Backend", version="0.2.0")
app.include_router(happ.router)
app.include_router(connect.router)
app.include_router(payments.router)
app.include_router(payments.checkout_router)


@app.on_event("startup")
async def startup() -> None:
    await create_sqlite_schema_for_local_dev()
    async with async_session_maker() as session:
        await seed_defaults(session)
        await session.commit()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
