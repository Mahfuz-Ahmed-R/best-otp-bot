from bot.utils.text import normalize_stylized_text


def is_state_cancelling_input(text_input: str) -> bool:
    if not text_input:
        return False
    clean_text = normalize_stylized_text(text_input).strip().upper()
    if clean_text.startswith("/"):
        return True
    cancelling = [
        "USER MANAGEMENT", "SYSTEM CONFIGURATION", "MANAGE SERVICES",
        "BACK TO MAIN", "ADMIN PANEL", "GET NUMBER", "BALANCE",
        "TRAFFIC", "2FA ONLINE", "SUPPORT", "PROFILE", "REFER AND EARN", "CANCEL",
    ]
    return any(k in clean_text for k in cancelling)
