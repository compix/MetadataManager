# Metadata-Manager (WIP)

## Setup
* `python -m venv tutorial-env`
* Activate env: 
  * Windows with git bash: `source .env/Scripts/activate`
* With activated env run: `pip install -r requirements.txt`

## Deploy
```shell
pyinstaller metadata_viewer.spec
pyinstaller launcher/launcher.spec
```

## Update Qt Resource File
- Run update_qrc.py (make sure pyside2-rcc is a known command)