from io import BytesIO
from os import path, getenv
from flask import Flask, Response, request
from PIL import Image, ImageFont
from dotenv import load_dotenv
from brother_ql.labels import ALL_LABELS
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends import guess_backend, backend_factory
from app.imaging import createBarcode, createLabelImage

load_dotenv()

LABEL_SIZE = getenv("LABEL_SIZE", "62x29")
PRINTER_MODEL = getenv("PRINTER_MODEL", "QL-500")
PRINTER_PATH = getenv("PRINTER_PATH", "file:///dev/usb/lp1")
BARCODE_FORMAT = getenv("BARCODE_FORMAT", "Datamatrix")
NAME_FONT = getenv("NAME_FONT", "NotoSerif-Regular.ttf")
NAME_FONT_SIZE = int(getenv("NAME_FONT_SIZE", "48"))
NAME_MAX_LINES = int(getenv("NAME_MAX_LINES", "4"))
DUE_DATE_FONT =  getenv("NAME_FONT", "NotoSerif-Regular.ttf")
DUE_DATE_FONT_SIZE = int(getenv("DUE_DATE_FONT_SIZE", "30"))

selected_backend = guess_backend(PRINTER_PATH)
BACKEND_CLASS = backend_factory(selected_backend)['backend_class']

label_spec = next(x for x in ALL_LABELS if x.identifier == LABEL_SIZE)

thisDir = path.dirname(path.abspath(__file__))
nameFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", NAME_FONT), NAME_FONT_SIZE)
ddFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", DUE_DATE_FONT), DUE_DATE_FONT_SIZE)

app = Flask(__name__)

@app.route("/")
def home_route():
    return "Label %s, Size %ix%i"%(label_spec.identifier, label_spec.dots_printable[0], label_spec.dots_printable[1])

def get_params():
    source = request.form if request.method == "POST" else request.args

    name = ""
    if 'product' in source:
        name = source['product']
    if 'battery' in request.form:
        name = source['battery']
    if 'chore' in request.form:
        name = source['chore']
    if 'recipe' in request.form:
        name = source['recipe']
    
    barcode = source['grocycode'] if 'grocycode' in source else ''
    dueDate = source['due_date'] if 'due_date' in source else ''

    return (name, barcode, dueDate)

@app.route("/print", methods=["GET", "POST"])
def print_route():
    (name, barcode, dueDate) = get_params();

    label = createLabelImage(label_spec.dots_printable, name, nameFont, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dueDate, ddFont)

    buf = BytesIO()
    label.save(buf, format="PNG")
    buf.seek(0)
    sendToPrinter(label)

    return Response("OK", 200)

@app.route("/image")
def test():
    (name, barcode, dueDate) = get_params();

    img = createLabelImage(label_spec.dots_printable, name, nameFont, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dueDate, ddFont)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(buf, 200, mimetype="image/png")

def sendToPrinter(image : Image):
    bql = BrotherQLRaster(PRINTER_MODEL)

    create_label(
        bql,
        image,
        LABEL_SIZE
    )

    be = BACKEND_CLASS(PRINTER_PATH)
    be.write(bql.data)
    del be

