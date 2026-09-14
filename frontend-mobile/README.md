# LMPC Inspector — Flutter Mobile App

Inspector-facing mobile app. Phase 3 scope: camera capture with PDP framing
overlay, offline upload queue (Hive + Workmanager), and scan status polling.

## Phase 3 deliverables

| File | Purpose |
|---|---|
| `lib/camera_screen.dart` | Live camera viewfinder + `CustomPainter` PDP framing guide |
| `lib/upload_queue.dart` | Hive offline store + Workmanager background flush |
| `lib/scan_status_screen.dart` | Polls `GET /scans/{scan_id}/status` every 3 s |
| `lib/services/api_service.dart` | Dio HTTP client (upload + status + auth stubs) |
| `lib/constants.dart` | API base URL, box names, task names |
| `lib/main.dart` | App entry point (Phase 3 launcher screen) |

Phase 11 adds: login screen, product selection, declaration review, report download.

## Prerequisites

- Flutter ≥ 3.22.0 (Dart ≥ 3.3.0)
- Android SDK 23+ / Xcode 15+
- Backend running at `http://10.0.2.2:8000` (Android emulator → host port 8000)

## Setup

```bash
# 1. Bootstrap Flutter project structure (one-time)
cd frontend-mobile
flutter create . --project-name lmpc_mobile --org com.lmpc --platforms android,ios

# 2. Install dependencies
flutter pub get

# 3. Generate Hive TypeAdapter (PendingUpload)
flutter pub run build_runner build --delete-conflicting-outputs

# 4. Merge Android permissions
#    Copy the <uses-permission> entries from
#    android/app/src/main/permissions_stub.xml
#    into android/app/src/main/AndroidManifest.xml
#    and set minSdkVersion=23 in android/app/build.gradle.

# 5. Run on emulator
flutter run
```

## API base URL

The default is `http://10.0.2.2:8000` (Android emulator → host machine).

Override at build time:
```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.x:8000
```

## Offline queue

1. Inspector captures a label → stored in Hive box `pending_uploads`.
2. `UploadQueueService.flush()` runs on capture (online) and via Workmanager
   every 15 min in background.
3. On Android, toggle airplane mode off → Workmanager fires `com.lmpc.uploadFlush`
   → uploads pending entries → image appears in MinIO `raw-images`.

## Phase 3 DoD checklist

- [ ] Camera screen opens with PDP framing guide overlay
- [ ] Shutter captures image and enqueues it in Hive
- [ ] Online: flush uploads immediately, navigates to status screen
- [ ] Offline: banner shown, entry persists in Hive
- [ ] Background flush fires on reconnect
- [ ] Status screen polls correctly (`queued → processing → done`)
- [ ] `Scan` row in PostgreSQL has correct `status`, `product_id`, `uploaded_by`
- [ ] Image present in MinIO `raw-images/{scan_id}/original.jpg`
