# Cross-Platform Secret Storage

Research date: 2026-08-18

## Goal

Identify a secure method for persisting the Jetstream archive bearer credential on Linux and WSL in a Python 3.14 application while considering broader portability options.

## Method

Review the native credential-store documentation for each supported operating system and the official documentation and package metadata for Python `keyring`. Evaluate security boundary, platform coverage, Python compatibility, operational requirements, and failure behavior.

## Evidence

### Each supported platform provides a native credential store

- macOS Keychain stores small secrets in an encrypted database and controls application access.
- Windows Credential Locker stores credentials for desktop applications and supports retrieval by application resource and username.
- Linux desktop environments expose secret collections through the Freedesktop Secret Service D-Bus API. The service supports locked collections, user prompts, and protected secret transfer.

### Python keyring provides one interface to native stores

Python `keyring` supports macOS Keychain, Windows Credential Locker, Freedesktop Secret Service, and KDE KWallet. Its package metadata requires Python 3.9 or newer and provides a platform-independent wheel, which is compatible with Spex's Python 3.14 requirement.

### Linux availability depends on the desktop session

The Linux Secret Service and KWallet backends require a compatible D-Bus service. Minimal, headless, or incompletely configured Linux environments may provide no recommended backend. KWallet may also require a system installation of `dbus-python`.

### WSL behaves as Linux for Python keyring selection

Python running inside WSL does not use the standard `keyring` Windows backend. That backend runs on Windows and calls Windows credential APIs through Windows-specific Python bindings. Inside WSL, `keyring` instead searches for a Linux backend such as Freedesktop Secret Service or KWallet.

A WSL installation can run systemd and D-Bus services, but a usable Secret Service still requires installation, session startup, and unlocking. This makes native Linux keyring behavior possible in WSL without making it automatic.

The third-party `keyring-wincred` package provides a WSL-specific `keyring` backend that invokes PowerShell with inline C# and calls the Windows Credential Manager API. Version 0.1.0 is its only published release. Its small release history and PowerShell subprocess boundary require source review and functional testing before Spex can depend on it.

### The development environment is Arch Linux on WSL

Arch Linux packages `gnome-keyring` as an implementation of `org.freedesktop.secrets` and `libsecret` as its client library and command-line tooling. GNOME Keyring normally starts through a systemd user service or D-Bus activation and unlocks through PAM during login.

An Arch Linux WSL shell may lack the desktop login and PAM sequence that normally unlocks the keyring. Validation therefore needs to cover systemd user-session availability, D-Bus activation, initial keyring creation, interactive unlocking, and behavior after WSL restarts. Package availability alone does not establish a usable unattended credential store.

### Plaintext fallback weakens the security boundary

Native stores protect secrets through the user's operating-system session. A plaintext configuration file exposes the bearer credential to any process or user that can read the file. Spex should identify an unavailable secure backend instead of silently selecting a plaintext backend.

### An encrypted file requires a separate key source

An authenticated encrypted file protects confidentiality and detects tampering. Fernet provides authenticated symmetric encryption, and its documentation recommends Argon2id when deriving the encryption key from a password. The file can store the random salt because the salt is not secret.

The encryption key remains secret. Spex has three ways to obtain it:

- Ask for a master password during each application session.
- Retrieve a random encryption key from the operating-system credential store.
- Store the key on disk and rely on file permissions, which places the key beside the protected data and weakens the design.

OWASP recommends storing encryption keys separately from encrypted data and using operating-system secure storage when available.

### Existing encrypted-file backends add constraints

`keyrings.cryptfile` stores an authenticated AES-encrypted file protected by an Argon2id-derived key. It prompts for a keyring password unless another source supplies that password. Its latest PyPI release is from 2022, and its published Python classifiers stop at Python 3.11, so Python 3.14 compatibility requires validation.

`keyrings.alt` includes filesystem backends but explicitly discourages them for general production use because some have security risks. Its plaintext backend provides no secret confidentiality.

## Conclusions

Spex selects a master-password-protected encrypted file for persisted secrets. This approach provides one storage model across Linux and WSL without requiring a configured desktop credential service.

The user supplies the master password when starting a backfill that needs the stored Jetstream archive credential. Application startup and workflows that do not need the credential do not prompt. The unlocked credential remains available for the complete backfill session, including automatic retries. A later backfill session requires another unlock. Spex does not persist the master password or a derived encryption key. The encrypted file stores the salt and the parameters required to derive a key from the supplied password.

Native credential stores and Python `keyring` remain documented alternatives rather than application dependencies.

The design still needs decisions for:

- Authenticated-encryption format and library
- Password-based key-derivation algorithm and parameters
- Encrypted-file subdirectory and filesystem permissions
- The service and account identifiers used for lookup
- Credential replacement and deletion
- Transfer from the TUI process through the orchestrator to the backfill process
- Log and error-message redaction

## Next steps

- Select the authenticated-encryption format and library.
- Select the password-based key-derivation algorithm and parameters.
- Define permissions, corruption handling, migration, and the encrypted credential filename beneath `user_data_path/credentials/`.
- Design credential lifecycle and inter-process transfer.
- Validate the encrypted-file design on Linux and Arch Linux under WSL.

## Sources

- [Python keyring documentation](https://keyring.readthedocs.io/en/latest/)
- [Python keyring package metadata](https://pypi.org/project/keyring/)
- [Apple Keychain Services](https://developer.apple.com/documentation/security/keychain-services)
- [Microsoft Credential Locker](https://learn.microsoft.com/en-us/windows/apps/develop/security/credential-locker)
- [Freedesktop Secret Service API](https://specifications.freedesktop.org/secret-service/latest/)
- [Cryptography Fernet documentation](https://cryptography.io/en/latest/fernet/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [keyrings.cryptfile package](https://pypi.org/project/keyrings.cryptfile/)
- [keyrings.alt package](https://pypi.org/project/keyrings.alt/)
- [Microsoft WSL systemd configuration](https://learn.microsoft.com/en-us/windows/wsl/wsl-config#systemd-support)
- [keyring Windows backend source](https://github.com/jaraco/keyring/blob/main/keyring/backends/Windows.py)
- [keyring-wincred package](https://pypi.org/project/keyring-wincred/)
- [ArchWiki GNOME Keyring](https://wiki.archlinux.org/title/GNOME/Keyring)
- [Arch Linux gnome-keyring package](https://archlinux.org/packages/extra/x86_64/gnome-keyring/)
- [Arch Linux libsecret package](https://archlinux.org/packages/core/x86_64/libsecret/)
