import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'package:lmpc_mobile/main.dart';

void main() {
  setUpAll(() async {
    // Initialise Hive in a temp directory for tests.
    await Hive.initFlutter();
  });

  testWidgets('Phase3Launcher renders product-ID field', (WidgetTester tester) async {
    await tester.pumpWidget(const LmpcApp());

    // The launcher screen must show the UUID input field.
    expect(find.byType(TextFormField), findsOneWidget);
    expect(find.text('Open Camera'), findsOneWidget);
  });
}
