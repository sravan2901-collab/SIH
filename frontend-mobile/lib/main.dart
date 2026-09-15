import 'package:flutter/material.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'camera_screen.dart';
import 'upload_queue.dart';

/// Entry point.
///
/// Initialises Hive, registers the background upload-flush task via
/// Workmanager, then launches the app.
///
/// Phase 3 scope: the home screen is [CameraScreen] with a hard-coded
/// product_id placeholder. In Phase 11 this is replaced by a login
/// screen → product selection → camera flow.
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialise Hive offline store.
  await Hive.initFlutter();
  await UploadQueueService.init();

  // Register the periodic background upload-flush task.
  await registerUploadFlushTask();

  runApp(const LmpcApp());
}

class LmpcApp extends StatelessWidget {
  const LmpcApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LMPC Inspector',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1565C0), // LMPC brand blue
        ),
        useMaterial3: true,
      ),
      // Phase 3: go straight to camera.
      // Phase 11 will add: LoginScreen → ProductSelectScreen → CameraScreen.
      home: const _Phase3Launcher(),
    );
  }
}

/// Temporary launcher for Phase 3 demo.
/// Presents a product-ID input so a tester can paste any valid product_id
/// from the backend before opening the camera.
class _Phase3Launcher extends StatefulWidget {
  const _Phase3Launcher();

  @override
  State<_Phase3Launcher> createState() => _Phase3LauncherState();
}

class _Phase3LauncherState extends State<_Phase3Launcher> {
  final _ctrl = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _launch() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CameraScreen(productId: _ctrl.text.trim()),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('LMPC Inspector — Phase 3')),
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.qr_code_scanner, size: 64, color: Color(0xFF1565C0)),
              const SizedBox(height: 32),
              TextFormField(
                controller: _ctrl,
                decoration: const InputDecoration(
                  labelText: 'Product ID (UUID)',
                  hintText: 'Paste product_id from backend',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.inventory_2_outlined),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) {
                    return 'Product ID is required';
                  }
                  final uuidPattern = RegExp(
                    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                    caseSensitive: false,
                  );
                  if (!uuidPattern.hasMatch(v.trim())) {
                    return 'Must be a valid UUID';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _launch,
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Open Camera'),
                ),
              ),
              const SizedBox(height: 48),
              Text(
                'Phase 11 will replace this screen with a full\n'
                'login → product select → camera flow.',
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
