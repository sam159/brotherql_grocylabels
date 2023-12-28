# Brother QL Grocy Label Printer Service

<img src="example.png" alt="Example Label" width="348" height="135">

This project is intended to be a webhook target for [Grocy](https://github.com/grocy/grocy) to print labels to a brother QL label printer. 

Datamatrix or QR codes can be used with Datamatrix being the default. Datamatrix will fit better in smaller labels but I've found aren't as easily read by the Grocy 
barcode reader or by the [Android App](https://github.com/patzly/grocy-android).

Only die-cut labels are supported as I don't have any endless rolls to test with.

## Connecting Grocy

Once you have this running somewhere update your config at `app/data/config.php` to match the following. Presuming that you have this running on localhost at port 8000.

```
    // Label printer settings
    Setting('LABEL_PRINTER_WEBHOOK', 'http://127.0.0.1:8000/print');
    Setting('LABEL_PRINTER_RUN_SERVER', true);
    Setting('LABEL_PRINTER_PARAMS', []);
    Setting('LABEL_PRINTER_HOOK_JSON', false);

    Setting('FEATURE_FLAG_LABEL_PRINTER', true);
```

## Environment Variables

The label size and printer are configured via environmental variables. You can also create a `.env` file instead.

| Variable           | Default               | Description                                                                                   |
| ------------------ | --------------------- | --------------------------------------------------------------------------------------------- |
| LABEL_SIZE         | 62x29                 | See the [brother_ql](https://github.com/pklaus/brother_ql) readme for the names of the labels |
| PRINTER_MODEL      | QL-500                | The printer model. One of the values accepted by brother_ql                                   |
| PRINTER_PATH       | file:///dev/usb/lp1   | Where the printer is found on the system. For network printers use `tcp://printer.address`    |
| BARCODE_FORMAT     | Datamatrix            | `Datamatrix` or `QRCode`                                                                      |
| NAME_FONT          | NotoSerif-Regular.ttf | The file name of the font in the fonts directory                                              |
| NAME_FONT_SIZE     | 48                    | The size of that font                                                                         |
| NAME_MAX_LINES     | 4                     | The maximum number of lines to use for the name                                               |
| DUE_DATE_FONT      | NotoSerif-Regular.ttf | The file name of the font in the fonts directory                                              |
| DUE_DATE_FONT_SIZE | 30                    | The size of that font                                                                         |

Included fonts are `NotoSans-Regular.ttf` and `NotoSerif-Regular.ttf`

## Endpoints

Two endpoints are available `/print` and `/image` both accept the same parameters. `/image` will return the rendered image as a PNG instead of sending to the printer.

### Parameters

POST or GET accepted.

| Name      | Use                                 |
| --------- | ------------------------------------|
| product   | name                                |
| battery   | name                                |
| chore     | name                                |
| recipe    | name                                |
| grocycode | the barcode                         |
| due_date  | the text at the bottom of the label |

The name will use whichever parameter is given.

## Running

**Note:** Theres no security on this web service, so don't make it publicly available.

This has been tested with python 3.10, newer may work fine.

You will need to install the `libdmtx` library for the barcodes to generate, see [pylibdmtx](https://pypi.org/project/pylibdmtx/) documentation on pypi.

Its advisable to run and install in a [venv](https://docs.python.org/3/library/venv.html). For example:

```
    # Create and enter the venv
    python -m venv .venv
    source ./.venv/bin/activate
    # Install packages
    python -m pip install -U -r requirements

    # exit with ./.venv/bin/deactivate
```

For development you can use `flask run --debug` to run the service on port 5000. Alternatively use `gunicorn -c gunicorn_conf.py app:app` to run the service on port 8000.

## TODO

- Endless Labels
- Some more formatting options

### Docker

A Dockerfile is included based on a python 3.10 alpine image. The default port is 8000.

Published to Dockerhub as [sam159/brotherql_grocylabels](https://hub.docker.com/r/sam159/brotherql_grocylabels) for architectures amd64, arm64, and armv7.

As an example, you can launch this with `docker run -d -p 8000:8000 -e PRINTER_MODEL=QL-500 -e PRINTER_PATH=file:///dev/usb/lp1 sam159/brotherql_grocylabels:latest`.

An example `docker-compose.yml` file can be found [here](docker-compose.yml).

## Contributing

I'll try to keep on top of bugs but feature requests may go unfulfilled. Please use the issue tracking in Github.

PRs welcome!