import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'scan_status_screen.dart';
import 'upload_queue.dart';

// ---------------------------------------------------------------------------
// PDP Framing Overlay
// ---------------------------------------------------------------------------

/// Draws a rounded-rectangle guide that frames the Principal Display Panel
/// of the product label, matching the Workflow L1-3 framing guide spec.
///
/// The guide covers 80 % of the shorter viewport dimension, centred, with
/// a 16:9 aspect ratio (landscape label assumption). Four corner indicators
/// (L-shaped white strokes) make alignment intuitive on any device.
class _PdpFrameOverlay extends CustomPainter {
  const _PdpFrameOverlay();

  @override
  void paint(Canvas canvas, Size size) {
    // --- Compute guide rect ---
    const double aspectRatio = 16 / 9;
    final double guideWidth = size.width * 0.85;
    final double guideHeight = guideWidth / aspectRatio;
    final double left = (size.width - guideWidth) / 2;
    final double top = (size.height - guideHeight) / 2;
    final Rect guideRect = Rect.fromLTWH(left, top, guideWidth, guideHeight);
    const double cornerLength = 24.0;
    const double radius = 8.0;

    // --- Semi-transparent scrim outside the guide ---
    final scrimPaint = Paint()..color = Colors.black54;
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, top), scrimPaint);
    canvas.drawRect(
        Rect.fromLTWH(0, top + guideHeight, size.width, size.height - top - guideHeight),
        scrimPaint);
    canvas.drawRect(Rect.fromLTWH(0, top, left, guideHeight), scrimPaint);
    canvas.drawRect(
        Rect.fromLTWH(left + guideWidth, top, size.width - left - guideWidth, guideHeight),
        scrimPaint);

    // --- Rounded-rect border ---
    final borderPaint = Paint()
      ..color = Colors.white.withOpacity(0.85)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawRRect(
      RRect.fromRectAndRadius(guideRect, const Radius.circular(radius)),
      borderPaint,
    );

    // --- Corner indicators (L-shapes) ---
    final cornerPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0
      ..strokeCap = StrokeCap.square;

    void drawCorner(Offset corner, double dx, double dy) {
      canvas.drawLine(corner, corner.translate(dx * cornerLength, 0), cornerPaint);
      canvas.drawLine(corner, corner.translate(0, dy * cornerLength), cornerPaint);
    }

    drawCorner(guideRect.topLeft.translate(radius, 0), 1, 1);
    drawCorner(guideRect.topRight.translate(-radius, 0), -1, 1);
    drawCorner(guideRect.bottomLeft.translate(radius, 0), 1, -1);
    drawCorner(guideRect.bottomRight.translate(-radius, 0), -1, -1);

    // --- Instruction text ---
    final textPainter = TextPainter(
      text: const TextSpan(
        text: 'Align product label within frame',
        style: TextStyle(
          color: Colors.white,
          fontSize: 12,
          letterSpacing: 0.4,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout(maxWidth: guideWidth);

    textPainter.paint(
      canvas,
      Offset(left + (guideWidth - textPainter.width) / 2, top + guideHeight + 10),
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ---------------------------------------------------------------------------
// Camera Screen
// ---------------------------------------------------------------------------

/// Presents a live camera viewfinder with the [_PdpFrameOverlay] guide.
///
/// Flow:
///   1. Initialise [CameraController] on the rear camera.
///   2. User taps the shutter button → capture to temp file.
///   3. Pass the captured file to [UploadQueueService.enqueue].
///   4. Navigate to [ScanStatusScreen] if online; otherwise show
///      "Saved offline" banner.
///
/// [productId] is required and comes from the product selection screen
/// (Phase 2 web flow equivalent — in Phase 11 a full ProductSelectScreen
/// will be added to the mobile app).
class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key, required this.productId});

  /// The [Product.product_id] (UUID string) selected before opening this screen.
  final String productId;

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen>
    with WidgetsBindingObserver {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _isInitialised = false;
  bool _isBusy = false; // capture / upload in progress

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;

    if (state == AppLifecycleState.inactive) {
      controller.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();
    } catch (_) {
      _cameras = [];
    }

    if (_cameras.isEmpty) {
      setState(() => _isInitialised = false);
      return;
    }

    // Prefer rear camera; fall back to first available.
    final rear = _cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.back,
      orElse: () => _cameras.first,
    );

    final controller = CameraController(
      rear,
      ResolutionPreset.high, // adequate for label text; balances file size
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );

    try {
      await controller.initialize();
      if (!mounted) return;
      setState(() {
        _controller = controller;
        _isInitialised = true;
      });
    } catch (_) {
      setState(() => _isInitialised = false);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  // -------------------------------------------------------------------------
  // Capture + enqueue
  // -------------------------------------------------------------------------

  Future<void> _onShutter() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized || _isBusy) return;

    setState(() => _isBusy = true);

    try {
      final xFile = await controller.takePicture();
      await _processCapture(xFile.path, 'image/jpeg');
    } catch (e) {
      _showSnack('Capture failed: $e');
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  /// Gallery fallback — shown when camera permission is permanently denied.
  Future<void> _onPickFromGallery() async {
    final picker = ImagePicker();
    final xFile = await picker.pickImage(source: ImageSource.gallery);
    if (xFile == null) return;

    setState(() => _isBusy = true);
    try {
      await _processCapture(xFile.path, 'image/jpeg');
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _processCapture(String imagePath, String contentType) async {
    // Always enqueue first (guarantees offline resilience).
    final localId = await UploadQueueService.instance.enqueue(
      productId: widget.productId,
      imagePath: imagePath,
      imageContentType: contentType,
    );

    // Try immediate flush.
    final uploaded = await UploadQueueService.instance.flush();

    if (!mounted) return;

    if (uploaded > 0) {
      // Flush succeeded — find the scan_id assigned by the server.
      final box = UploadQueueService.instance;
      // The entry's remoteScanId is now set after a successful flush.
      // Re-read from Hive by localId to get the remoteScanId.
      final entry = Hive.box<PendingUpload>(kPendingUploadsBox).get(localId);
      final scanId = entry?.remoteScanId;

      if (scanId != null) {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => ScanStatusScreen(scanId: scanId),
          ),
        );
        return;
      }
    }

    // No connectivity or flush failed — show offline confirmation.
    _showSnack(
      'Saved offline. Will upload automatically when connected.',
      duration: const Duration(seconds: 4),
    );
  }

  void _showSnack(String message, {Duration? duration}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: duration ?? const Duration(seconds: 3),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Build
  // -------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: _isInitialised && _controller != null
          ? _buildViewfinder()
          : _buildNoCameraFallback(),
    );
  }

  Widget _buildViewfinder() {
    final controller = _controller!;
    return Stack(
      fit: StackFit.expand,
      children: [
        // Live preview fills the screen.
        CameraPreview(controller),

        // PDP framing overlay on top.
        CustomPaint(painter: const _PdpFrameOverlay()),

        // Controls bar at the bottom.
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: _buildControlsBar(),
        ),
      ],
    );
  }

  Widget _buildControlsBar() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 32),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [Colors.black87, Colors.transparent],
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Gallery fallback button.
          IconButton(
            onPressed: _isBusy ? null : _onPickFromGallery,
            icon: const Icon(Icons.photo_library_outlined),
            color: Colors.white70,
            iconSize: 32,
            tooltip: 'Pick from gallery',
          ),

          // Shutter button.
          GestureDetector(
            onTap: _isBusy ? null : _onShutter,
            child: Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 3),
                color: _isBusy ? Colors.white24 : Colors.white,
              ),
              child: _isBusy
                  ? const Center(
                      child: SizedBox(
                        width: 28,
                        height: 28,
                        child: CircularProgressIndicator(
                          color: Colors.black54,
                          strokeWidth: 2.5,
                        ),
                      ),
                    )
                  : const SizedBox.shrink(),
            ),
          ),

          // Pending uploads badge.
          _PendingBadge(
            count: UploadQueueService.instance.pendingCount,
          ),
        ],
      ),
    );
  }

  Widget _buildNoCameraFallback() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.camera_alt_outlined, color: Colors.white38, size: 64),
          const SizedBox(height: 16),
          const Text(
            'Camera unavailable',
            style: TextStyle(color: Colors.white60, fontSize: 16),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _onPickFromGallery,
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('Pick from Gallery'),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Pending uploads badge
// ---------------------------------------------------------------------------

class _PendingBadge extends StatelessWidget {
  const _PendingBadge({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        const Icon(Icons.cloud_upload_outlined, color: Colors.white70, size: 32),
        if (count > 0)
          Positioned(
            top: -4,
            right: -4,
            child: Container(
              padding: const EdgeInsets.all(3),
              decoration: const BoxDecoration(
                color: Colors.orangeAccent,
                shape: BoxShape.circle,
              ),
              child: Text(
                '$count',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
