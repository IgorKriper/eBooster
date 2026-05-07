from __future__ import annotations

import html
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.backend.dependencies import session_dependency
from eboost.core.branding import BRAND_NAME
from eboost.core.config import get_settings
from eboost.models import User
from eboost.services import connect_tokens

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connect"])


def _mask(value: str | None) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}…{value[-4:]}"


def _render_error(title: str, message: str) -> HTMLResponse:
    body = _PAGE_TEMPLATE.replace("__TITLE__", html.escape(title)).replace(
        "__BODY__",
        f"""
        <main class="card">
            <h1>{html.escape(title)}</h1>
            <p class="muted">{html.escape(message)}</p>
            <p class="muted small">Если не получилось — напиши в поддержку из бота.</p>
        </main>
        """,
    )
    return HTMLResponse(body, status_code=410)


@router.get("/connect", response_class=HTMLResponse)
async def connect_page(
    token: str = Query(..., min_length=8, max_length=128),
    session: AsyncSession = Depends(session_dependency),
) -> HTMLResponse:
    settings = get_settings()
    record = await connect_tokens.get_token(session, token)
    if record is None:
        logger.info("connect_page token_not_found token=%s", _mask(token))
        return _render_error(
            "Ссылка не действительна",
            "Сгенерируй новую кнопку подключения в боте.",
        )
    if not connect_tokens.is_token_active(record):
        logger.info("connect_page token_expired token=%s", _mask(token))
        return _render_error(
            "Ссылка устарела",
            "Сгенерируй новую кнопку подключения в боте.",
        )

    user: User | None = await session.get(User, record.user_id)
    if user is None or not user.vpn_subscription_url:
        logger.warning("connect_page no_subscription token=%s", _mask(token))
        return _render_error(
            "Подписка ещё не готова",
            "Активируй пробный период или оплати подписку в боте.",
        )

    subscription_url = user.vpn_subscription_url
    deep_link = f"happ://add/{subscription_url}"

    await connect_tokens.consume_token(session, record)

    body = _build_body(deep_link=deep_link, manual_link=subscription_url, settings=settings)
    page = _PAGE_TEMPLATE.replace("__TITLE__", f"{BRAND_NAME} — подключение").replace(
        "__BODY__", body
    )
    return HTMLResponse(page)


def _build_body(*, deep_link: str, manual_link: str, settings) -> str:
    happ_buttons = "".join(
        f'<a class="link-button" href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(label)}</a>'
        for label, url in (
            ("📱 iOS", settings.happ_ios_url),
            ("🤖 Android", settings.happ_android_url),
            ("💻 macOS", settings.happ_macos_url),
            ("🪟 Windows", settings.happ_windows_url),
        )
        if url
    )
    safe_deep_link = html.escape(deep_link, quote=True)
    safe_manual = html.escape(manual_link, quote=True)
    masked_manual_attr = quote(manual_link, safe="")  # for data attribute
    return f"""
        <main class="card">
            <header class="brand">
                <span class="logo">e</span>
                <h1>{BRAND_NAME}</h1>
                <p class="tagline">Защищённый VPN-ускоритель</p>
            </header>

            <section>
                <h2>Подключение в 3 шага</h2>
                <ol class="steps">
                    <li>Скачай приложение <b>Happ</b> для своей платформы.</li>
                    <li>Нажми «🚀 Подключить подписку» — откроется Happ.</li>
                    <li>Готово, можно пользоваться eBooster.</li>
                </ol>

                <a class="primary" href="{safe_deep_link}">🚀 Подключить подписку</a>

                <h3>Скачать Happ</h3>
                <div class="links">
                    {happ_buttons}
                </div>
            </section>

            <section class="instructions">
                <h2>Как подключить вручную</h2>
                <details>
                    <summary>iOS / iPadOS</summary>
                    <ol>
                        <li>Установи Happ из App Store.</li>
                        <li>Открой Happ → «+» → «Импортировать из URL».</li>
                        <li>Вставь ссылку и подтверди добавление подписки.</li>
                    </ol>
                </details>
                <details>
                    <summary>Android</summary>
                    <ol>
                        <li>Установи Happ из Google Play.</li>
                        <li>Нажми «Импортировать ссылку» и вставь её.</li>
                        <li>Включи подключение.</li>
                    </ol>
                </details>
                <details>
                    <summary>macOS</summary>
                    <ol>
                        <li>Установи Happ из App Store.</li>
                        <li>Открой Happ → «+» → «Из URL» и вставь ссылку.</li>
                    </ol>
                </details>
                <details>
                    <summary>Windows</summary>
                    <ol>
                        <li>Скачай Happ Desktop и установи.</li>
                        <li>В приложении выбери «Add subscription» → вставь ссылку.</li>
                    </ol>
                </details>
            </section>

            <section class="fallback">
                <details>
                    <summary>Не открылось автоматически?</summary>
                    <p class="muted">Покажу ссылку только тебе. Не передавай её другим — лимит устройств действует.</p>
                    <button class="ghost" type="button" id="reveal-link">Показать ссылку</button>
                    <code id="manual-link" class="hidden" data-link="{html.escape(masked_manual_attr)}">{safe_manual}</code>
                </details>
            </section>

            <footer class="muted small">© {BRAND_NAME}. Не сохраняем твою ссылку и не передаём третьим лицам.</footer>
        </main>
        <script>
            (function () {{
                var btn = document.getElementById('reveal-link');
                var code = document.getElementById('manual-link');
                if (!btn || !code) return;
                btn.addEventListener('click', function () {{
                    code.classList.remove('hidden');
                    btn.style.display = 'none';
                }});
            }})();
        </script>
    """


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex,nofollow" />
    <title>__TITLE__</title>
    <style>
        :root { color-scheme: dark light; }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 100%);
            color: #f0f3ff;
            min-height: 100vh;
            padding: 24px 16px;
        }
        .card {
            max-width: 560px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 28px 24px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(8px);
        }
        .brand { text-align: center; margin-bottom: 24px; }
        .brand h1 { margin: 8px 0 4px; font-size: 28px; letter-spacing: 0.5px; }
        .brand .logo {
            display: inline-flex;
            width: 56px;
            height: 56px;
            border-radius: 16px;
            background: linear-gradient(135deg, #2f6fed, #7aa7ff);
            color: #fff;
            font-weight: 700;
            font-size: 28px;
            align-items: center;
            justify-content: center;
            box-shadow: 0 12px 30px rgba(47, 111, 237, 0.45);
        }
        .tagline { margin: 0; opacity: 0.75; }
        h2 { font-size: 18px; margin-top: 24px; margin-bottom: 8px; }
        h3 { font-size: 15px; margin-top: 20px; margin-bottom: 8px; opacity: 0.85; }
        .steps { padding-left: 20px; }
        .steps li { margin-bottom: 6px; }
        .primary {
            display: block;
            text-align: center;
            background: linear-gradient(135deg, #2f6fed, #4d8bff);
            color: #fff;
            text-decoration: none;
            padding: 16px 18px;
            border-radius: 16px;
            font-size: 17px;
            font-weight: 600;
            margin: 18px 0 4px;
            box-shadow: 0 12px 28px rgba(47, 111, 237, 0.45);
        }
        .primary:active { transform: translateY(1px); }
        .links { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .link-button {
            display: block;
            text-align: center;
            background: rgba(255, 255, 255, 0.08);
            color: inherit;
            text-decoration: none;
            padding: 12px 14px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            font-weight: 500;
        }
        .link-button:hover { background: rgba(255, 255, 255, 0.12); }
        .instructions details, .fallback details {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            padding: 10px 14px;
            margin-bottom: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        .instructions summary, .fallback summary {
            cursor: pointer;
            font-weight: 600;
        }
        .instructions ol { margin: 8px 0 4px 18px; }
        .ghost {
            background: transparent;
            color: inherit;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 12px;
            padding: 10px 14px;
            cursor: pointer;
            margin-top: 6px;
        }
        code {
            display: block;
            margin-top: 10px;
            padding: 12px;
            background: rgba(0, 0, 0, 0.35);
            border-radius: 12px;
            word-break: break-all;
            font-size: 12px;
        }
        .hidden { display: none; }
        .muted { opacity: 0.7; }
        .small { font-size: 12px; }
        footer { margin-top: 22px; text-align: center; }
        @media (max-width: 420px) {
            .links { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
__BODY__
</body>
</html>
"""
