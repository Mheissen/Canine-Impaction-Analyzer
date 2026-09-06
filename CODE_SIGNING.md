# Code Signing Checklist

## Windows
- Obtain a trusted code-signing certificate.
- Build the application on Windows.
- Sign the EXE or installer with Microsoft's SignTool.
- Verify the signature before release.
- Re-scan the final signed binary.

## macOS
- Join the Apple Developer Program.
- Obtain a Developer ID Application certificate.
- Build the .app on macOS.
- Sign the application and bundled components.
- Submit for Apple notarization.
- Staple the notarization ticket.
- Verify with Gatekeeper before distribution.

Signing cannot be completed without the developer's own private certificate
credentials.
