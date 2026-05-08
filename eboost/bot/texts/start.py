def main(active_until: str | None = None) -> str:
    status = f"\n\nДоступ активен до: <b>{active_until}</b>" if active_until else ""
    return (
        "<b>🚀 eBoost</b>\n\n"
        "Сервис для стабильного и комфортного интернет-соединения.\n\n"
        "eBoost работает в фоне и помогает поддерживать быстрое и стабильное подключение без сложных настроек.\n\n"
        "Подключение занимает меньше минуты."
        f"{status}\n\n"
        "Выбери действие:"
    )


MAIN = main()
