# NephroAI Mobile — Setup Guide

## 1. Установить Flutter SDK

1. Скачать: https://docs.flutter.dev/get-started/install/windows/android
2. Распаковать в `C:\flutter` (не в Program Files!)
3. Добавить `C:\flutter\bin` в PATH (Система → Переменные среды → Path)
4. Перезапустить PowerShell/CMD
5. Проверить: `flutter --version`

## 2. Установить Android Studio

1. Скачать: https://developer.android.com/studio
2. Установить с SDK (минимум Android 13/API 33)
3. `flutter doctor --android-licenses` (принять все лицензии)
4. Проверить: `flutter doctor` — должен показать ✓ для Android

## 3. Подключить Android телефон

1. Включить Developer Options: Настройки → О телефоне → нажать 7 раз на "Номер сборки"
2. Включить USB Debugging в Developer Options
3. Подключить телефон по USB
4. Принять запрос отладки на телефоне
5. Проверить: `flutter devices` — должен показать твой телефон

## 4. Запустить приложение

```bash
cd mobile
flutter pub get          # установить зависимости
flutter run              # запустить на подключённом устройстве
```

## 5. Собрать APK для установки

```bash
flutter build apk --release
# APK будет в: build/app/outputs/flutter-apk/app-release.apk
```

## Настройки API

Файл: `lib/core/constants.dart`
- Production: `http://209.50.54.90/api` (уже настроено)
- Local dev (Android emulator): `http://10.0.2.2:8000/api`

## Структура проекта

```
lib/
  main.dart              → точка входа
  app.dart               → GoRouter навигация
  core/
    constants.dart       → API URL
    api_client.dart      → HTTP клиент с JWT
    storage.dart         → хранение токена
    theme.dart           → тёмная тема
  models/                → data классы
  services/              → API вызовы
  screens/
    auth/                → Login, Register, Verify
    patient/             → Dashboard, Series, Upload, Chat, Profile, Share
    doctor/              → Patients, PatientDetail
  widgets/               → AnalyteCard, MetricChart
```
