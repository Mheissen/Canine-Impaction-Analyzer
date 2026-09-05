# Windows Build — Important

If PySide6 installation fails with an error containing a very long path such as:

`PySide6\qml\Qt\labs\...`

this is normally a Windows path-length problem.

The included `build_windows.bat` fixes this by creating the Python virtual
environment at the short path:

`C:\CIA_BUILD\venv`

## Use

1. Extract this ZIP normally.
2. Open the extracted folder.
3. Double-click `build_windows.bat`.
4. When it says BUILD COMPLETE, open:

`dist\Canine Impaction Analyzer\Canine Impaction Analyzer.exe`

Do not manually create `.venv` inside the extracted Downloads folder.

If an old `.venv` folder already exists there, it can be deleted.
