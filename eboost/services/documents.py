from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import Document


DEFAULT_DOCUMENTS = [
    {
        "slug": "privacy",
        "title": "Политика конфиденциальности",
        "body": "eBoost хранит Telegram ID, данные подписки, платежей и рефералов только для работы сервиса. Данные не продаются третьим лицам.",
    },
    {
        "slug": "terms",
        "title": "Пользовательское соглашение",
        "body": "Используя eBoost, пользователь соглашается соблюдать правила сервиса и не применять доступ для незаконных действий.",
    },
    {
        "slug": "refunds",
        "title": "Политика возвратов",
        "body": "Возвраты рассматриваются поддержкой индивидуально. Напишите @eBoost_support и укажите Telegram ID.",
    },
]


async def list_documents(session: AsyncSession) -> list[Document]:
    result = await session.execute(select(Document).order_by(Document.id))
    return list(result.scalars().all())


async def get_document(session: AsyncSession, slug: str) -> Document | None:
    result = await session.execute(select(Document).where(Document.slug == slug))
    return result.scalar_one_or_none()


async def seed_documents(session: AsyncSession) -> None:
    for item in DEFAULT_DOCUMENTS:
        result = await session.execute(select(Document).where(Document.slug == item["slug"]))
        document = result.scalar_one_or_none()
        if document is None:
            session.add(Document(**item))
        else:
            document.title = item["title"]
            document.body = item["body"]
