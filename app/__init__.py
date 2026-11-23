from io import BytesIO
from os import path, getenv
from threading import Thread
from queue import Queue
import atexit
import logging
from flask import Flask, Response, request
from PIL import Image, ImageFont
from dotenv import load_dotenv
from brother_ql.labels import ALL_LABELS, Color
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
ENDLESS_MARGIN = int(getenv("ENDLESS_MARGIN", "10"))

selected_backend = guess_backend(PRINTER_PATH)
BACKEND_CLASS = backend_factory(selected_backend)['backend_class']

label_spec = next(x for x in ALL_LABELS if x.identifier == LABEL_SIZE)

thisDir = path.dirname(path.abspath(__file__))
nameFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", NAME_FONT), NAME_FONT_SIZE)
ddFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", DUE_DATE_FONT), DUE_DATE_FONT_SIZE)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

print_queue = Queue()


def _print_queue_handler():
    app.logger.info("print thread running")
    while True:
        print_item = print_queue.get()

        cmd = print_item[0]
        if cmd == 'quit':
            app.logger.info("print thread exiting")
            break
        elif cmd == 'print':
            app.logger.info("handling print request")
            label = print_item[1]
            sendToPrinter(label)
        else:
            app.logger.error(f"unknown command {print_item[0]}")


print_thread = Thread(target=_print_queue_handler, group=None, daemon=True)
print_thread.start()


def _exit_handler():
    print_queue.put(('quit',))
    print_thread.join()


atexit.register(_exit_handler)


@app.route("/")
def home_route():
    return "Label %s, %s"%(label_spec.identifier, label_spec.name)

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

    label = createLabelImage(label_spec.dots_printable, ENDLESS_MARGIN, name, nameFont, NAME_FONT_SIZE, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dueDate, ddFont)

    buf = BytesIO()
    label.save(buf, format="PNG")
    buf.seek(0)
    print_queue.put(('print', label))

    return Response("OK", 200)

@app.route("/image")
def test():
    (name, barcode, dueDate) = get_params();

    img = createLabelImage(label_spec.dots_printable, ENDLESS_MARGIN, name, nameFont, NAME_FONT_SIZE, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dueDate, ddFont)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(buf, 200, mimetype="image/png")

def sendToPrinter(image : Image):
    bql = BrotherQLRaster(PRINTER_MODEL)

    redLabel = label_spec.color == Color.BLACK_RED_WHITE

    create_label(
        bql,
        image,
        LABEL_SIZE,
        red=redLabel
    )

    be = BACKEND_CLASS(PRINTER_PATH)
    be.write(bql.data)
    del be
