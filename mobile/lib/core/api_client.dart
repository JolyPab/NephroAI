import 'package:dio/dio.dart';
import 'constants.dart';
import 'storage.dart';

class ApiClient {
  static final Dio _dio = _createDio();

  static Dio _createDio() {
    final dio = Dio(BaseOptions(
      baseUrl: kApiBaseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json'},
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await Storage.getToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        handler.next(error);
      },
    ));

    return dio;
  }

  static Dio get instance => _dio;
}
