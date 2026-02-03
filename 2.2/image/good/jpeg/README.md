# JPEG Test Files (Good)

Files in this directory are valid C2PA test files following the C2PA 2.2 specification.

## Ed25519 Signature Examples

| Image | Description | Manifest | Detailed Manifest |
|-------|-------------|----------|-------------------|
| [test-20260203-ed25519.jpg](test-20260203-ed25519.jpg) | Test image signed with Ed25519 algorithm | [manifest_store.json](manifests/test-20260203-ed25519/manifest_store.json) | [detailed.json](manifests/test-20260203-ed25519/detailed.json) |

### Notes

- The Ed25519 test file uses a test certificate which is not on any trusted certificate list
- The signature itself is valid, but validators will report the certificate as untrusted
