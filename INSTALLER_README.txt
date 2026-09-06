CANINE IMPACTION ANALYZER v1.1.2 - WINDOWS INSTALLER

This package does NOT change the application calculations or interface.
It only adds Windows installer packaging.

EASIEST: GitHub (no Python needed on your PC)
1. Upload this package CONTENTS to the ROOT of your GitHub repository.
   Important: include the hidden .github folder.
2. GitHub -> Actions -> Build Windows Installer -> Run workflow.
3. When complete, open the workflow run and download the artifact.
4. Inside it is:
   CanineImpactionAnalyzer_Setup_v1.1.2.exe
5. That Setup EXE is the file normal Windows users need. They do NOT need Python.

LOCAL WINDOWS OPTION
Double-click build_installer_windows.bat. The build PC needs Python, but the
finished Setup EXE does not.

Note: The installer is unsigned unless you add a code-signing certificate.
Windows SmartScreen may warn users about an unsigned/new publisher.
