FROM python:3.10-alpine as builder

WORKDIR /app

RUN apk add fontconfig build-base tiff-dev jpeg-dev openjpeg-dev \
    zlib-dev freetype-dev lcms2-dev libwebp-dev tcl-dev tk-dev \
    harfbuzz-dev fribidi-dev libimagequant-dev libxcb-dev libpng-dev \
    libdmtx libdmtx-dev

RUN python3 -m venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

FROM python:3.10-alpine

# gcc needed because pythons find_libary doesn't work without it https://bugs.python.org/issue21622
RUN apk add gcc fontconfig jpeg lcms2 zlib freetype tcl tk harfbuzz \
    fribidi libimagequant libxcb libpng libdmtx libdmtx-dev

WORKDIR /app

COPY --from=builder /app /app
ENV PATH=/app/.venv/bin:$PATH

COPY . .

EXPOSE 8000
CMD ["gunicorn", "--conf", "/app/gunicorn_conf.py", "--bind", "0.0.0.0:8000", "app:app"]