# Metadata-Manager (WIP)

## Install
* > pip install virtualenv
* > virtualenv .env
* > pip install pipenv
* > pipenv install
  
**Windows**:
* PowerShell: Run the following command as admin to allow environment activation-script execution:
    ```powershell
    Set-ExecutionPolicy Unrestricted -Force
    ```

## Installing new Packages
* > pipenv install <package>
* If version conflict errors occur the following may help:
    * > pipenv lock --clear
    * There may also be an importlib-metadata version conflict error. It may be resolvable with
      > pip install -U pipenv

## Deploy
```shell
pyinstaller metadata_viewer.spec
pyinstaller launcher/launcher.spec
```

## Update Qt Resource File
- Run update_qrc.py