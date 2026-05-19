# Local Deployment

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` before running the app. At minimum, change `SECRET_KEY`.

## Development Run

```sh
python3 app.py
```

## Production-Style Local Run

```sh
source .venv/bin/activate
gunicorn --bind 127.0.0.1:8000 wsgi:app
```

Use `wsgi.py` as the stable Gunicorn entrypoint.

## System Packages

OCR needs Tesseract installed on the machine:

```sh
brew install tesseract
```

