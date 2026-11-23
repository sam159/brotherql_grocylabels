from io import BytesIO
from os import path, getenv
from threading import Thread, Event
from queue import Queue, Full
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

PRINT_QUEUE_MAX_SIZE = 50
PRINT_MAX_RETRIES = 3
PRINT_RETRY_DELAY = 2
PRINT_SHUTDOWN_TIMEOUT = 10

print_queue = Queue(PRINT_QUEUE_MAX_SIZE)
shutdown_event = Event()


def _print_with_retry(label):
    """Print a label, retrying up to PRINT_MAX_RETRIES times with increasing delay."""
    delay = PRINT_RETRY_DELAY
    for attempt in range(1, PRINT_MAX_RETRIES + 2):
        try:
            sendToPrinter(label)
            return
        except Exception:
            if attempt > PRINT_MAX_RETRIES:
                app.logger.exception("failed to print label after %s attempts, dropping it", attempt)
                return

            if shutdown_event.is_set():
                app.logger.warning("shutdown in progress, not retrying failed print")
                return

            app.logger.exception(
                "print attempt %s of %s failed, retrying in %ss",
                attempt, PRINT_MAX_RETRIES + 1, delay
            )
            if shutdown_event.wait(delay):
                app.logger.warning("shutdown in progress, abandoning print retries")
                return
            delay *= 2


def _print_queue_handler():
    app.logger.info("print thread running")
    while True:
        print_item = print_queue.get()

        cmd = print_item[0]
        if cmd == 'quit':
            shutdown_event.set()
            app.logger.info("print thread exiting")
            break
        elif cmd == 'print':
            app.logger.info("handling print request")
            _print_with_retry(print_item[1])
        else:
            app.logger.error(f"unknown command {cmd}")


print_thread = Thread(target=_print_queue_handler, group=None, daemon=True)
print_thread.start()


def _exit_handler():
    shutdown_event.set()

    try:
        print_queue.put(('quit',), block=False)
    except Full:
        app.logger.warning("print queue full on exit, dropping pending print requests")
        return

    print_thread.join(timeout=PRINT_SHUTDOWN_TIMEOUT)
    if print_thread.is_alive():
        app.logger.warning("print thread did not exit within %ss, dropping pending print requests", PRINT_SHUTDOWN_TIMEOUT)


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
    (name, barcode, dueDate) = get_params()

    label = createLabelImage(label_spec.dots_printable, ENDLESS_MARGIN, name, nameFont, NAME_FONT_SIZE, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), dueDate, ddFont)

    try:
        print_queue.put(('print', label), block=False)
    except Full:
        app.logger.warning("print queue full, rejecting print request")
        return Response("print queue full", 503, mimetype="text/plain")

    return Response("accepted", 200, mimetype="text/plain")

@app.route("/image")
def test():
    (name, barcode, dueDate) = get_params()

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
