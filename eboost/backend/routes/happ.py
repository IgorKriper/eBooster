from __future__ import annotations

import html
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.backend.dependencies import session_dependency
from eboost.core.config import get_settings
from eboost.models import User
from eboost.services import happ
from eboost.services.subscriptions import is_subscription_active

router = APIRouter(prefix="/api/happ", tags=["happ"])


@router.get("/connect/{telegram_id}", response_class=HTMLResponse)
async def open_happ(telegram_id: int, token: str, session: AsyncSession = Depends(session_dependency)) -> str:
    settings = get_settings()
    if token != happ.connect_token(settings, telegram_id):
        raise HTTPException(status_code=404, detail="Not found")

    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user or not user.vpn_subscription_url or not is_subscription_active(user):
        return _plain_page("Доступ не активен", "Вернись в eBooster и активируй доступ.")

    try:
        happ_link = await happ.encrypted_link(settings, user.vpn_subscription_url)
    except RuntimeError:
        return _fallback_page(user.vpn_subscription_url)
    return _open_page(happ_link, user.vpn_subscription_url)


def _open_page(happ_link: str, subscription_url: str) -> str:
    safe_link = html.escape(happ_link, quote=True)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>eBooster</title>
  <style>{_css()}</style>
</head>
<body>
  <main>
    <h1>eBooster</h1>
    <p>Открываем Happ.</p>
    <p>Подтверди добавление eBooster в приложении.</p>
    <a class="button" href="{safe_link}">Открыть Happ</a>
    {_fallback_block(subscription_url)}
  </main>
  <script>
    const happLink = {json.dumps(happ_link)};
    const fallback = document.querySelector(".fallback");
    window.location.href = happLink;
    setTimeout(() => {{ fallback.hidden = false; }}, 1600);
  </script>
</body>
</html>"""


def _fallback_page(subscription_url: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>eBooster</title>
  <style>{_css()}</style>
</head>
<body>
  <main>
    <h1>eBooster</h1>
    {_fallback_block(subscription_url, hidden=False)}
  </main>
</body>
</html>"""


def _plain_page(title: str, message: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>eBooster</title>
  <style>{_css()}</style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(message)}</p>
  </main>
</body>
</html>"""


def _fallback_block(subscription_url: str, *, hidden: bool = True) -> str:
    hidden_attr = " hidden" if hidden else ""
    return f"""
    <section class="fallback"{hidden_attr}>
      <h2>Не получилось автоматически</h2>
      <ol>
        <li>Скопируй ссылку</li>
        <li>Открой Happ</li>
        <li>Добавь подключение</li>
      </ol>
      <button type="button" onclick="copyLink()">Скопировать</button>
      <p class="hint">Если не работает приложение - просто временно отключи ускорение.</p>
    </section>
    <script>
      async function copyLink() {{
        await navigator.clipboard.writeText({json.dumps(subscription_url)});
        const button = document.querySelector("button");
        button.textContent = "Скопировано";
      }}
    </script>"""


def _css() -> str:
    return """
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7fb;
      color: #0f1f35;
    }
    main {
      width: min(420px, calc(100% - 32px));
      padding: 28px;
      border-radius: 18px;
      background: #fff;
      box-shadow: 0 18px 45px rgba(15, 31, 53, .08);
    }
    h1 { margin: 0 0 14px; font-size: 28px; }
    h2 { margin: 22px 0 12px; font-size: 20px; }
    p, li { color: #42526b; line-height: 1.5; }
    ol { padding-left: 22px; }
    .button, button {
      width: 100%;
      display: block;
      margin-top: 18px;
      padding: 14px 16px;
      border: 0;
      border-radius: 12px;
      background: #1769ff;
      color: #fff;
      text-align: center;
      text-decoration: none;
      font-size: 16px;
      font-weight: 800;
    }
    .hint { margin-top: 16px; font-size: 14px; }
    """
