# Supertonic Flutter Example

This example demonstrates how to use Supertonic 3 in a Flutter application using ONNX Runtime.

> **Note:** This project uses the `flutter_onnxruntime` package ([https://pub.dev/packages/flutter_onnxruntime](https://pub.dev/packages/flutter_onnxruntime)). At the moment, only the macOS platform has been tested. Although the flutter_onnxruntime package supports several other platforms, they have not been tested in this project yet and may require additional verification.


## 📰 Update News

**2026.04.29** - 🎉 **Supertonic 3** released with 31-language support, improved reading accuracy, and v2-compatible public ONNX assets. [Demo](https://huggingface.co/spaces/Supertone/supertonic-3) | [Models](https://huggingface.co/Supertone/supertonic-3)

**2025.12.10** - Added [6 new voice styles](https://huggingface.co/Supertone/supertonic/tree/b10dbaf18b316159be75b34d24f740008fddd381) (M3, M4, M5, F3, F4, F5). See [Voices](https://supertone-inc.github.io/supertonic-py/voices/) for details

**2025.12.08** - Optimized ONNX models via [OnnxSlim](https://github.com/inisis/OnnxSlim) now available on [Hugging Face Models](https://huggingface.co/Supertone/supertonic)

**2025.11.23** - Added and tested macos support.

## Multilingual Support

Supertonic 3 supports 31 languages. Select the appropriate language from the dropdown; see the main README for the full code list.

## Requirements

- Flutter SDK version ^3.5.0

## Running the Demo

```bash
flutter clean
flutter pub get
flutter run -d macos
```
