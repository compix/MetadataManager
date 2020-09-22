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

## Deploy
Use pyinstaller inside .env:
```powershell
cd .env
pyinstaller ../metadata_viewer.spec
```