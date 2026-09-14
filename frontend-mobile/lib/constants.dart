/// API base-URL resolution (priority order):
///
/// 1. Build-time override via `--dart-define=API_BASE_URL=http://...`
///    (use this for CI, physical devices, staging, or production).
/// 2. Android emulator default: 10.0.2.2 → host machine port 8000.
///    On iOS simulator use 127.0.0.1:8000.
///    On a physical device on the same LAN, replace with the host machine's
///    LAN IP (e.g. 192.168.x.x:8000).
///
/// The docker-compose.yml exposes the FastAPI backend on host port 8000,
/// so there is no need to change this default for the standard dev setup.
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

/// Hive box names
const String kPendingUploadsBox = 'pending_uploads';

/// Workmanager task names
const String kUploadFlushTask = 'com.lmpc.uploadFlush';

/// Polling interval for scan status (seconds)
const int kStatusPollIntervalSec = 3;
