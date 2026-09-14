import 'dart:async';

import 'package:flutter/material.dart';

import 'constants.dart';
import 'services/api_service.dart';

// ---------------------------------------------------------------------------
// Status model
// ---------------------------------------------------------------------------

/// Maps backend [Scan.status] values to display properties.
enum ScanStatus {
  queued,
  processing,
  done,
  needsReview,
  error;

  static ScanStatus fromString(String raw) => switch (raw) {
        'queued' => ScanStatus.queued,
        'processing' => ScanStatus.processing,
        'done' => ScanStatus.done,
        'needs_review' => ScanStatus.needsReview,
        'error' => ScanStatus.error,
        _ => ScanStatus.queued,
      };

  /// Human-readable label shown in the UI.
  String get label => switch (this) {
        ScanStatus.queued => 'Queued for processing…',
        ScanStatus.processing => 'Processing label…',
        ScanStatus.done => 'Analysis complete',
        ScanStatus.needsReview => 'Needs manual review',
        ScanStatus.error => 'Processing error',
      };

  Color get color => switch (this) {
        ScanStatus.queued => Colors.blue,
        ScanStatus.processing => Colors.orange,
        ScanStatus.done => Colors.green,
        ScanStatus.needsReview => Colors.amber,
        ScanStatus.error => Colors.red,
      };

  IconData get icon => switch (this) {
        ScanStatus.queued => Icons.hourglass_top_outlined,
        ScanStatus.processing => Icons.settings_outlined,
        ScanStatus.done => Icons.check_circle_outline,
        ScanStatus.needsReview => Icons.warning_amber_outlined,
        ScanStatus.error => Icons.error_outline,
      };

  /// Whether the pipeline is still running (keep polling).
  bool get isTerminal =>
      this == ScanStatus.done ||
      this == ScanStatus.needsReview ||
      this == ScanStatus.error;

  /// Progress value for [LinearProgressIndicator]; null = indeterminate.
  double? get progress => switch (this) {
        ScanStatus.queued => 0.15,
        ScanStatus.processing => null, // indeterminate
        ScanStatus.done => 1.0,
        ScanStatus.needsReview => 0.85,
        ScanStatus.error => 1.0,
      };
}

// ---------------------------------------------------------------------------
// Pipeline steps (for the step-list visual)
// ---------------------------------------------------------------------------

const _pipelineSteps = [
  (label: 'Uploaded', statuses: {ScanStatus.queued, ScanStatus.processing, ScanStatus.done, ScanStatus.needsReview}),
  (label: 'Preprocessing', statuses: {ScanStatus.processing, ScanStatus.done, ScanStatus.needsReview}),
  (label: 'OCR', statuses: {ScanStatus.done, ScanStatus.needsReview}),
  (label: 'Field Classification', statuses: {ScanStatus.done}),
  (label: 'Rule Validation', statuses: {ScanStatus.done}),
  (label: 'Report Generated', statuses: {ScanStatus.done}),
];

// ---------------------------------------------------------------------------
// ScanStatusScreen
// ---------------------------------------------------------------------------

/// Polls [GET /scans/{scanId}/status] every [kStatusPollIntervalSec] seconds
/// and renders a progress UI.
///
/// Navigates to a [DeclarationReviewScreen] placeholder on [ScanStatus.done].
/// Full Declaration Review is implemented in Phase 11.
class ScanStatusScreen extends StatefulWidget {
  const ScanStatusScreen({super.key, required this.scanId});

  final String scanId;

  @override
  State<ScanStatusScreen> createState() => _ScanStatusScreenState();
}

class _ScanStatusScreenState extends State<ScanStatusScreen> {
  ScanStatus _status = ScanStatus.queued;
  String? _errorMessage;
  Timer? _pollTimer;
  bool _isPolling = false;

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  // -------------------------------------------------------------------------
  // Polling
  // -------------------------------------------------------------------------

  void _startPolling() {
    // Fire immediately, then every kStatusPollIntervalSec seconds.
    _poll();
    _pollTimer = Timer.periodic(
      Duration(seconds: kStatusPollIntervalSec),
      (_) => _poll(),
    );
  }

  Future<void> _poll() async {
    if (_isPolling) return;
    _isPolling = true;

    try {
      final data = await ApiService.instance.getScanStatus(widget.scanId);
      final newStatus = ScanStatus.fromString(data['status'] as String? ?? 'queued');

      if (mounted) {
        setState(() {
          _status = newStatus;
          _errorMessage = null;
        });
      }

      if (newStatus.isTerminal) {
        _pollTimer?.cancel();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _errorMessage = 'Could not reach server: $e');
      }
      // Keep polling on transient network errors — the timer continues.
    } finally {
      _isPolling = false;
    }
  }

  // -------------------------------------------------------------------------
  // Build
  // -------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Status'),
        elevation: 0,
        backgroundColor: Theme.of(context).colorScheme.surface,
        foregroundColor: Theme.of(context).colorScheme.onSurface,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Scan ID chip
              _ScanIdChip(scanId: widget.scanId),
              const SizedBox(height: 32),

              // Status card
              _StatusCard(status: _status, errorMessage: _errorMessage),
              const SizedBox(height: 32),

              // Pipeline progress list
              _PipelineStepList(currentStatus: _status),
              const SizedBox(height: 40),

              // Action button (terminal states)
              if (_status.isTerminal) _buildActionButton(context),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionButton(BuildContext context) {
    if (_status == ScanStatus.done) {
      return SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: () {
            // Phase 11: navigate to DeclarationReviewScreen.
            // Stub for Phase 3.
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Declaration review is available in the web app (Phase 3). '
                  'Full mobile review UI coming in Phase 11.',
                ),
                duration: Duration(seconds: 5),
              ),
            );
          },
          icon: const Icon(Icons.article_outlined),
          label: const Text('View Results'),
        ),
      );
    }

    if (_status == ScanStatus.needsReview) {
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.camera_alt_outlined),
          label: const Text('Re-capture Label'),
        ),
      );
    }

    if (_status == ScanStatus.error) {
      return SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.refresh),
          label: const Text('Go Back & Retry'),
          style: FilledButton.styleFrom(
            backgroundColor: Colors.red,
          ),
        ),
      );
    }

    return const SizedBox.shrink();
  }
}

// ---------------------------------------------------------------------------
// Widgets
// ---------------------------------------------------------------------------

class _ScanIdChip extends StatelessWidget {
  const _ScanIdChip({required this.scanId});
  final String scanId;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Icon(Icons.qr_code_2, size: 16, color: Colors.grey),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            scanId,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey,
                  fontFamily: 'monospace',
                ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.status, this.errorMessage});
  final ScanStatus status;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: status.color.withOpacity(0.4)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(status.icon, color: status.color, size: 28),
                const SizedBox(width: 12),
                Text(
                  status.label,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: status.color,
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: status.progress,
                backgroundColor: status.color.withOpacity(0.15),
                valueColor: AlwaysStoppedAnimation<Color>(status.color),
                minHeight: 6,
              ),
            ),
            if (errorMessage != null) ...[
              const SizedBox(height: 12),
              Text(
                errorMessage!,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Colors.red.shade300),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _PipelineStepList extends StatelessWidget {
  const _PipelineStepList({required this.currentStatus});
  final ScanStatus currentStatus;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Pipeline Progress',
          style: Theme.of(context)
              .textTheme
              .labelMedium
              ?.copyWith(color: Colors.grey, letterSpacing: 0.8),
        ),
        const SizedBox(height: 12),
        ...List.generate(_pipelineSteps.length, (i) {
          final step = _pipelineSteps[i];
          final isDone = step.statuses.contains(currentStatus);
          final isLast = i == _pipelineSteps.length - 1;
          return _StepRow(
            label: step.label,
            isDone: isDone,
            isLast: isLast,
          );
        }),
      ],
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.label,
    required this.isDone,
    required this.isLast,
  });
  final String label;
  final bool isDone;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final color = isDone ? Colors.green : Colors.grey.shade300;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 32,
            child: Column(
              children: [
                Container(
                  width: 18,
                  height: 18,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isDone ? Colors.green : Colors.grey.shade200,
                    border: Border.all(color: color, width: 2),
                  ),
                  child: isDone
                      ? const Icon(Icons.check, color: Colors.white, size: 10)
                      : null,
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: isDone ? Colors.green.shade200 : Colors.grey.shade200,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Padding(
            padding: const EdgeInsets.only(top: 1, bottom: 16),
            child: Text(
              label,
              style: TextStyle(
                color: isDone ? Colors.black87 : Colors.grey,
                fontWeight: isDone ? FontWeight.w500 : FontWeight.normal,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
