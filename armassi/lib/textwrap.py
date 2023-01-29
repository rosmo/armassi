__all__ = ["wrap"]

def wrap(text, max_width, font=None, indent0="", indent1="    "):
    if font is None:
        def measure(s):
            return len(s)
    else:
        if hasattr(font, 'load_glyphs'):
            font.load_glyphs(text)
        def measure(s):
            return sum(font.get_glyph(ord(c)).shift_x for c in s)

    lines = []
    partial = [indent0]
    width = measure(indent0)
    swidth = measure(' ')
    firstword = True
    for word in text.split():
        wwidth = measure(word)
        if firstword:
            partial.append(word)
            firstword = False
            width += wwidth
        elif width + swidth + wwidth < max_width:
            partial.append(" ")
            partial.append(word)
            width += wwidth + swidth
        else:
            lines.append("".join(partial))
            partial = [indent1, word, ' ']
            width = measure(indent1) + wwidth + swidth
            firstword = True
    if partial:
        lines.append("".join(partial))
    return lines