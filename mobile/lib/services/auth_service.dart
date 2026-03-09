import 'package:dio/dio.dart';
import '../core/api_client.dart';
import '../core/storage.dart';
import '../models/user.dart';

class AuthService {
  static final _dio = ApiClient.instance;

  static Future<String> login(String email, String password) async {
    final res = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
    });
    final token = (res.data['accessToken'] ?? res.data['access_token']) as String;
    await Storage.saveToken(token);
    return token;
  }

  static Future<void> register(String email, String password, String name) async {
    await _dio.post('/auth/register', data: {
      'email': email,
      'password': password,
      'name': name,
    });
  }

  static Future<void> verifyEmail(String email, String code) async {
    await _dio.post('/auth/verify-email', data: {
      'email': email,
      'code': code,
    });
  }

  static Future<void> resendCode(String email) async {
    await _dio.post('/auth/resend-email-code', data: {'email': email});
  }

  static Future<User> getMe() async {
    final res = await _dio.get('/auth/me');
    return User.fromJson(res.data as Map<String, dynamic>);
  }

  static Future<void> logout() async {
    await Storage.clearToken();
  }

  static String extractErrorMessage(dynamic error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map) {
        return data['detail']?.toString() ?? 'Error desconocido';
      }
    }
    return error.toString();
  }
}
