from pylibdmtx.pylibdmtx import encode
import qrcode
from PIL import Image, ImageColor, ImageFont, ImageDraw

def createDatamatrix(text: str):
    encoded = encode(text.encode('utf8'), "Ascii", "ShapeAuto")
    barcode = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    return barcode

def createQRCode(text: str):
    return qrcode.make(text, box_size = 1)

def createBarcode(text: str, type: str):
    match type:
        case "QRCode":
            return createQRCode(text)
        case "DataMatrix":
            return createDatamatrix(text)
        case _:
            return createDatamatrix(text)

def createLabelImage(labelSize : tuple, endlessMargin : int, text : str, textFont : ImageFont, textFontSize : int, textMaxLines : int, barcode : Image, dueDate : str, dueDateFont : ImageFont):
    (width, height) = labelSize
    # default line spacing used by multiline_text, doesn't seem to have an effect if changed though but we need to take into account
    lineSpacing = 4
    # margin to use for label
    marginTop = 0
    marginBottom = 0

    # for endless labels with a height of zero
    if height == 0:
        # height should be text size + spacing x max lines + margin x 2
        height = (textFontSize + lineSpacing) * textMaxLines + endlessMargin * 2
        # negate the empty space above the text
        (_, tTop, _, _) = textFont.getbbox("testing")
        marginTop = endlessMargin - tTop
        # regular bottom margin
        marginBottom = endlessMargin
        # make space for the due date
        if dueDate:
            (_, _, _, ddBottom) = dueDateFont.getbbox(dueDate)
            height += ddBottom

    # increase the size of the barcode if space permits
    if (barcode.size[1] * 8) < height:
        barcode = barcode.resize((barcode.size[0] * 8, barcode.size[1] * 8), Image.Resampling.NEAREST)
    if (barcode.size[1] * 6) < height:
        barcode = barcode.resize((barcode.size[0] * 6, barcode.size[1] * 6), Image.Resampling.NEAREST)
    if (barcode.size[1] * 4) < height:
        barcode = barcode.resize((barcode.size[0] * 4, barcode.size[1] * 4), Image.Resampling.NEAREST)
    if (barcode.size[1] * 2) < height:
        barcode = barcode.resize((barcode.size[0] * 2, barcode.size[1] * 2), Image.Resampling.NEAREST)
    
    label = Image.new("RGB", (width, height), ImageColor.getrgb("#FFF"))
    # vertically align barcode (ignoring margin)
    barcode_padding = [0, (int)((label.size[1] / 2) - (barcode.size[1] / 2))]
    label.paste(barcode, barcode_padding)
    
    draw = ImageDraw.Draw(label)

    (nameText, nameTextWidth) = wrapText(text, textFont, width - barcode.size[0], textMaxLines)
    nameMaxWidth = width - barcode.size[0]
    nameLeftMargin = (nameMaxWidth - nameTextWidth) / 2

    draw.multiline_text(
        [barcode.size[0] + nameLeftMargin, marginTop],
        nameText,
        fill = ImageColor.getrgb("#000"),
        font = textFont,
        align = "center",
        spacing = lineSpacing
    )

    if dueDate:
        (_, _, ddRight, ddBottom) = dueDateFont.getbbox(dueDate)
        draw.text(
            [label.size[0] - ddRight, label.size[1] - ddBottom - marginBottom],
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
        lineLength = font.getlength(lines[-1])
        if lineLength > longestLine:
            longestLine = lineLength

    return ('\n'.join(lines), longestLine)
