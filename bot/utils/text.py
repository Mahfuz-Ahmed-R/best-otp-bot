def make_bold_unicode(text: str) -> str:
    out = []
    for char in text:
        codepoint = ord(char)
        if 65 <= codepoint <= 90:
            out.append(chr(codepoint - 65 + 0x1D5D4))
        elif 97 <= codepoint <= 122:
            out.append(chr(codepoint - 97 + 0x1D5EE))
        elif 48 <= codepoint <= 57:
            out.append(chr(codepoint - 48 + 0x1D7EC))
        else:
            out.append(char)
    return "".join(out)


def normalize_stylized_text(text: str) -> str:
    if not text:
        return ""
    out = []
    for char in text:
        cp = ord(char)
        if 0x1D5D4 <= cp <= 0x1D5ED:
            out.append(chr(cp - 0x1D5D4 + 65))
        elif 0x1D5EE <= cp <= 0x1D607:
            out.append(chr(cp - 0x1D5EE + 97))
        elif 0x1D7EC <= cp <= 0x1D7F5:
            out.append(chr(cp - 0x1D7EC + 48))
        else:
            out.append(char)
    return "".join(out)
