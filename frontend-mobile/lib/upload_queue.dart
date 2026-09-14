import 'dart:io';
import 'dart:isolate';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:uuid/uuid.dart';
import 'package:workmanager/workmanager.dart';

import '../constants.dart';
import 'api_service.dart';

// ---------------------------------------------------------------------------
// Hive TypeAdapter for [PendingUpload]
// ---------------------------------------------------------------------------

part 'upload_queue.g.dart';

/// One pending upload entry stored in the offline Hive box.
///
/// [typeId] = 0 — must be unique across all registered Hive adapters.
@HiveType(typeId: 0)
class PendingUpload extends HiveObject {
  @HiveField(0)
  late String localId; // UUID generated on device

  @HiveField(1)
  late String productId;

  @HiveField(2)
  late String imagePath; // absolute path on device

  @HiveField(3)
  late String imageContentType; // 'image/jpeg' or 'image/png'

  @HiveField(4)
  late DateTime capturedAt;

  /// Set to the server-assigned scan_id once the upload succeeds.
  @HiveField(5)
  String? remoteScanId;
}

// ---------------------------------------------------------------------------
// Upload Queue Service
// ---------------------------------------------------------------------------

/// Manages the offline upload queue backed by Hive.
///
/// Usage:
/// ```dart
/// await UploadQueueService.instance.enqueue(
///   productId: '...', imagePath: '/path/to/capture.jpg',
/// );
/// ```
class UploadQueueService {
  UploadQueueService._();
  static final UploadQueueService instance = UploadQueueService._();

  static const _uuid = Uuid();

  /// Must be called from [main] **after** [Hive.initFlutter].
  static Future<void> init() async {
    if (!Hive.isAdapterRegistered(0)) {
      Hive.registerAdapter(PendingUploadAdapter());
    }
    await Hive.openBox<PendingUpload>(kPendingUploadsBox);
  }

  Box<PendingUpload> get _box => Hive.box<PendingUpload>(kPendingUploadsBox);

  // -------------------------------------------------------------------------
  // Enqueue
  // -------------------------------------------------------------------------

  /// Serialise a capture into the Hive offline store.
  ///
  /// Returns the [localId] of the created entry so the UI can track it.
  Future<String> enqueue({
    required String productId,
    required String imagePath,
    String imageContentType = 'image/jpeg',
  }) async {
    final entry = PendingUpload()
      ..localId = _uuid.v4()
      ..productId = productId
      ..imagePath = imagePath
      ..imageContentType = imageContentType
      ..capturedAt = DateTime.now()
      ..remoteScanId = null;

    await _box.put(entry.localId, entry);
    return entry.localId;
  }

  // -------------------------------------------------------------------------
  // Flush (called by background isolate and on foreground reconnect)
  // -------------------------------------------------------------------------

  /// Try to upload every pending entry.
  ///
  /// * Entries whose image file no longer exists on disk are dropped silently.
  /// * Entries that fail with a 4xx HTTP error (bad request, auth) are also
  ///   dropped to avoid infinite retries.
  /// * Entries that fail with a network error are left in the box for the next
  ///   flush cycle.
  ///
  /// Returns the number of successfully uploaded entries.
  Future<int> flush() async {
    // Check connectivity before iterating — avoids pointless DioExceptions
    final connectivity = await Connectivity().checkConnectivity();
    if (connectivity == ConnectivityResult.none) return 0;

    final pending = _box.values.where((e) => e.remoteScanId == null).toList();
    int uploaded = 0;

    for (final entry in pending) {
      final file = File(entry.imagePath);
      if (!file.existsSync()) {
        // Image was deleted from device storage — discard the entry.
        await entry.delete();
        continue;
      }

      try {
        final result = await ApiService.instance.uploadScan(
          productId: entry.productId,
          imageFile: file,
          contentType: entry.imageContentType,
        );
        // Mark as synced (keep entry for reference; UI can show scan_id).
        entry.remoteScanId = result['scan_id'] as String;
        await entry.save();
        uploaded++;
      } on DioException catch (e) {
        final statusCode = e.response?.statusCode;
        if (statusCode != null && statusCode >= 400 && statusCode < 500) {
          // Client error — retrying will not help; drop the entry.
          await entry.delete();
        }
        // Network / 5xx errors: leave in box, will retry on next flush.
      }
    }

    return uploaded;
  }

  /// Unsynced entries count — useful for badge display on the UI.
  int get pendingCount =>
      _box.values.where((e) => e.remoteScanId == null).length;
}

// ---------------------------------------------------------------------------
// Workmanager callback dispatcher (top-level function, required by workmanager)
// ---------------------------------------------------------------------------

/// Registered via [Workmanager.initialize] in [main].
///
/// Runs in a background isolate — must be a top-level function.
@pragma('vm:entry-point')
void workmanagerCallbackDispatcher() {
  Workmanager().executeTask((taskName, inputData) async {
    if (taskName == kUploadFlushTask) {
      // Re-initialise Hive inside the background isolate.
      await Hive.initFlutter();
      await UploadQueueService.init();
      await UploadQueueService.instance.flush();
    }
    return Future.value(true);
  });
}

// ---------------------------------------------------------------------------
// Workmanager registration helper
// ---------------------------------------------------------------------------

/// Call this once from [main] to register the periodic background flush task.
///
/// The minimum interval on Android is 15 minutes (OS-enforced); we request
/// 15 minutes which is the closest to the 30-second spec — for testing use
/// [Workmanager.registerOneOffTask] instead.
Future<void> registerUploadFlushTask() async {
  await Workmanager().initialize(
    workmanagerCallbackDispatcher,
    isInDebugMode: false,
  );
  await Workmanager().registerPeriodicTask(
    kUploadFlushTask,
    kUploadFlushTask,
    frequency: const Duration(minutes: 15),
    constraints: Constraints(
      networkType: NetworkType.connected,
    ),
    existingWorkPolicy: ExistingWorkPolicy.keep,
  );
}
