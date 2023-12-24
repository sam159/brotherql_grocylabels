from pylibdmtx.pylibdmtx import encode
from PIL import Image, ImageColor, ImageFont, ImageDraw

def createBarcode(text: str):
    encoded = encode(text.encode('utf8'), "Ascii", "32x32")
    barcode = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    return barcode

def createLabelImage(labelSize : tuple, text : str, textFont : ImageFont, textMaxLines : int, barcode : Image, dueDate : str, dueDateFont : ImageFont):
    label = Image.new("RGB", labelSize, ImageColor.getrgb("#FFF"))
    barcode_padding = [0, (int)((label.size[1] / 2) - (barcode.size[1] / 2))]
    label.paste(barcode, barcode_padding)
    
    draw = ImageDraw.Draw(label)
    draw.multiline_text(
        [barcode.size[1], 0],
        wrapText(text, textFont, label.size[0] - barcode.size[0], textMaxLines),
        fill = ImageColor.getrgb("#000"),
        font = textFont
    )

    if dueDate:
        (_, _, _, ddbottom) = dueDateFont.getbbox(dueDate)
        draw.text(
            [barcode.size[1], label.size[1] - ddbottom],
            dueDate,
            fill = ImageColor.getrgb("#000"),
            font = dueDateFont
        )

    return label

def wrapText(text : str, font : ImageFont, maxWidth : int, maxLines : int):
    parts = text.split(" ")
    parts.reverse()
    lines = []

    # break words that are too long for a single line
    trimmedParts = []
    for part in parts:
        if font.getlength(part) >= maxWidth:
            # just chop in half, nothing fancy
            midpoint = int(len(part) / 2);
            trimmedParts.append(part[midpoint:])
            trimmedParts.append(part[0:midpoint] + '-')
        else:
            trimmedParts.append(part)

    parts = trimmedParts
    
    # create lines from input
    while len(parts) > 0:
        nextLine = []
        
        # create this line adding words while the next word fits
        while len(parts) > 0:
            nextPart = parts.pop()

            if font.getlength(' '.join(nextLine) + ' ' + nextPart) < maxWidth:
                nextLine.append(nextPart)
            else:
                # didn't fit so put it back on the stack
                parts.append(nextPart)
                break
        
        # finished with the line
        if len(nextLine) > 0:
            lines.append(' '.join(nextLine));
    
    if len(lines) > maxLines:
        lines = lines[0:maxLines]
        lines[-1] += '...'

    return '\n'.join(lines)