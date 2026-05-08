"""Branded /connect?token=… landing page that opens eBooster in Happ."""
from __future__ import annotations

import html
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.backend.dependencies import session_dependency
from eboost.core.config import get_settings
from eboost.services import connect_tokens, happ
from eboost.services.subscriptions import is_subscription_active

router = APIRouter(tags=["connect"])


@router.get("/connect", response_class=HTMLResponse)
async def connect_page(
    token: str = Query(default=""),
    session: AsyncSession = Depends(session_dependency),
) -> HTMLResponse:
    settings = get_settings()
    if not token:
        return HTMLResponse(_plain_page("Ссылка устарела", "Открой бот eBooster и нажми «Открыть и подключить» ещё раз."))

    consumed = await connect_tokens.consume_connect_token(session, token_value=token)
    if not consumed:
        return HTMLResponse(_plain_page("Ссылка устарела", "Открой бот eBooster и нажми «Открыть и подключить» ещё раз."))

    token_row, user = consumed
    if not is_subscription_active(user) or not user.vpn_subscription_url:
        return HTMLResponse(
            _plain_page(
                "Подписка не активна",
                "Открой бот eBooster и активируй пробный период или продли тариф.",
            )
        )

    await connect_tokens.mark_token_used(session, token=token_row)

    try:
        happ_link = await happ.encrypted_link(settings, user.vpn_subscription_url)
    except RuntimeError:
        happ_link = f"happ://add/{user.vpn_subscription_url}"
    return HTMLResponse(_open_page(settings, happ_link, user.vpn_subscription_url))


def _open_page(settings, happ_link: str, subscription_url: str) -> str:
    safe_link = html.escape(happ_link, quote=True)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>eBooster — подключение</title>
  <style>{_css()}</style>
</head>
<body>
  <main>
    <div class="brand">
      <span class="logo">🚀</span>
      <h1>eBooster</h1>
    </div>
    <p class="lead">Стабильный интернет без сложных настроек.</p>
    <a class="button primary" href="{safe_link}" id="open-happ">🚀 Открыть и подключить</a>
    {_install_block(settings)}
    {_fallback_block(subscription_url)}
  </main>
  <script>
    const happLink = {json.dumps(happ_link)};
    const fallback = document.querySelector(".fallback");
    setTimeout(() => {{ window.location.href = happLink; }}, 250);
    setTimeout(() => {{ if (fallback) fallback.hidden = false; }}, 1800);
  </script>
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
    <div class="brand"><span class="logo">🚀</span><h1>eBooster</h1></div>
    <h2>{html.escape(title)}</h2>
    <p>{html.escape(message)}</p>
  </main>
</body>
</html>"""


def _install_block(settings) -> str:
    return f"""
    <section class="install">
      <h2>Не установлен Happ?</h2>
      <ul>
        <li><a href="{html.escape(settings.happ_ios_url, quote=True)}" target="_blank" rel="noopener">iOS</a></li>
        <li><a href="{html.escape(settings.happ_android_url, quote=True)}" target="_blank" rel="noopener">Android</a></li>
        <li><a href="{html.escape(settings.happ_macos_url, quote=True)}" target="_blank" rel="noopener">macOS</a></li>
        <li><a href="{html.escape(settings.happ_windows_url, quote=True)}" target="_blank" rel="noopener">Windows</a></li>
      </ul>
    </section>"""


def _fallback_block(subscription_url: str) -> str:
    return f"""
    <section class="fallback" hidden>
      <h2>Не получилось автоматически</h2>
      <ol>
        <li>Скопируй ссылку</li>
        <li>Открой Happ</li>
        <li>Добавь подключение и вставь ссылку</li>
      </ol>
      <button type="button" onclick="copyLink()">Скопировать ссылку</button>
      <p class="hint">Если приложение Happ ещё не установлено — установи его по ссылкам выше.</p>
    </section>
    <script>
      async function copyLink() {{
        try {{
          await navigator.clipboard.writeText({json.dumps(subscription_url)});
        }} catch (err) {{
          window.prompt("Скопируй ссылку вручную:", {json.dumps(subscription_url)});
        }}
        const button = document.querySelector(".fallback button");
        if (button) button.textContent = "Скопировано";
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
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
      background: linear-gradient(140deg, #0f1f35 0%, #1769ff 100%);
      color: #0f1f35;
      padding: 24px;
    }
    main {
      width: min(440px, 100%);
      padding: 32px 28px 28px;
      border-radius: 22px;
      background: #fff;
      box-shadow: 0 24px 60px rgba(15, 31, 53, .25);
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand .logo { font-size: 28px; }
    h1 { margin: 0; font-size: 26px; }
    h2 { margin: 22px 0 10px; font-size: 18px; }
    .lead { color: #42526b; line-height: 1.5; margin: 14px 0 0; }
    .button, button {
      display: block;
      width: 100%;
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
      cursor: pointer;
    }
    .button.primary { background: #1769ff; }
    .install ul { padding-left: 18px; margin: 8px 0 0; color: #42526b; }
    .install ul li { margin: 4px 0; }
    .install a { color: #1769ff; text-decoration: none; font-weight: 600; }
    ol { padding-left: 22px; color: #42526b; }
    ol li { margin: 4px 0; }
    .hint { margin-top: 12px; font-size: 14px; color: #6b7c93; }
    """
