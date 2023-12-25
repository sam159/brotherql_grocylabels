from pylibdmtx.pylibdmtx import encode
from PIL import Image, ImageColor, ImageFont, ImageDraw

def createBarcode(text: str):
    encoded = encode(text.encode('utf8'), "Ascii", "ShapeAuto")
    barcode = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    return barcode

def createLabelImage(labelSize : tuple, text : str, textFont : ImageFont, textMaxLines : int, barcode : Image, dueDate : str, dueDateFont : ImageFont):
    # increase the size of the barcode if space permits
    if (barcode.size[1] * 4) < labelSize[1]:
        barcode = barcode.resize((barcode.size[0] * 4, barcode.size[1] * 4), Image.Resampling.NEAREST)
    if (barcode.size[1] * 2) < labelSize[1]:
        barcode = barcode.resize((barcode.size[0] * 2, barcode.size[1] * 2), Image.Resampling.NEAREST)
    
    label = Image.new("RGB", labelSize, ImageColor.getrgb("#FFF"))
    barcode_padding = [0, (int)((label.size[1] / 2) - (barcode.size[1] / 2))]
    label.paste(barcode, barcode_padding)
    
    draw = ImageDraw.Draw(label)

    (nameText, nameTextWidth) = wrapText(text, textFont, label.size[0] - barcode.size[0], textMaxLines)
    nameMaxWidth = label.size[0] - barcode.size[0]
    nameLeftMargin = (nameMaxWidth - nameTextWidth) / 2

    print((nameTextWidth, nameMaxWidth, nameLeftMargin))

    draw.multiline_text(
        [barcode.size[0] + nameLeftMargin, 0],
        nameText,
        fill = ImageColor.getrgb("#000"),
        font = textFont,
        align = "center"
    )

    if dueDate:
        (_, _, ddRight, ddBottom) = dueDateFont.getbbox(dueDate)
        draw.text(
            [label.size[0] - ddRight, label.size[1] - ddBottom],
            dueDate,
            fill = ImageColor.getrgb("#000"),
            font = dueDateFont
        )

    return label

def wrapText(text : str, font : ImageFont, maxWidth : int, maxLines : int):
    parts = text.split(" ")
    parts.reverse()
    lines = []
    longestLine = 0

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
            lines.append(' '.join(nextLine))
            lineLength = font.getlength(' '.join(nextLine))
            if lineLength > longestLine:
                longestLine = lineLength
    
    if len(lines) > maxLines:
        lines = lines[0:maxLines]
        lines[-1] += '...'

    return ('\n'.join(lines), longestLine)