import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants.dart';

/// Thin wrapper around [Dio] that:
///   * reads the JWT from secure storage and attaches it as `Authorization: Bearer …`,
///   * serialises `POST /scans/upload` as `multipart/form-data`,
///   * deserialises `GET /scans/{scanId}/status` to a plain [Map].
///
/// Phase 3 scope only — login, declaration review and report download
/// are Phase 11 additions.
class ApiService {
  ApiService._();
  static final ApiService instance = ApiService._();

  final _storage = const FlutterSecureStorage();

  Dio get _dio => Dio(
        BaseOptions(
          baseUrl: kApiBaseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 30),
        ),
      );

  /// Returns `null` when no token is stored (user not logged in).
  Future<String?> _token() => _storage.read(key: 'lmpc_token');

  Future<Options> _authOptions() async {
    final token = await _token();
    return Options(
      headers: token != null ? {'Authorization': 'Bearer $token'} : {},
    );
  }

  // ---------------------------------------------------------------------------
  // Phase 3 endpoints
  // ---------------------------------------------------------------------------

  /// Upload a raw image for a given product.
  ///
  /// Returns the full [ScanReadDto] map (keys: scan_id, product_id,
  /// uploaded_by, raw_image_path, capture_timestamp, status,
  /// preprocessed_image_path).
  ///
  /// Throws [DioException] on network or HTTP errors — callers should catch
  /// and decide whether to enqueue for offline retry.
  Future<Map<String, dynamic>> uploadScan({
    required String productId,
    required File imageFile,
    String? contentType,
  }) async {
    final opts = await _authOptions();
    final formData = FormData.fromMap({
      'product_id': productId,
      'file': await MultipartFile.fromFile(
        imageFile.path,
        filename: imageFile.path.split(Platform.pathSeparator).last,
        contentType: DioMediaType.parse(contentType ?? 'image/jpeg'),
      ),
    });
    final response = await _dio.post<Map<String, dynamic>>(
      '/scans/upload',
      data: formData,
      options: opts,
    );
    return response.data!;
  }

  /// Returns `{scan_id: String, status: String}`.
  Future<Map<String, dynamic>> getScanStatus(String scanId) async {
    final opts = await _authOptions();
    final response = await _dio.get<Map<String, dynamic>>(
      '/scans/$scanId/status',
      options: opts,
    );
    return response.data!;
  }

  // ---------------------------------------------------------------------------
  // Phase 1 — Auth (minimal stubs; full implementation is Phase 11)
  // ---------------------------------------------------------------------------

  /// Stores the returned JWT in [FlutterSecureStorage].
  /// Throws [DioException] on wrong credentials (401).
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'email': email, 'password': password},
      options: Options(headers: {'Content-Type': 'application/json'}),
    );
    final data = response.data!;
    await _storage.write(key: 'lmpc_token', value: data['access_token'] as String);
    await _storage.write(key: 'lmpc_role', value: data['role'] as String);
    return data;
  }

  Future<void> logout() async {
    await _storage.deleteAll();
  }
}
