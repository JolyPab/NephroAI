import 'package:dio/dio.dart';
import '../core/api_client.dart';
import '../models/analyte.dart';
import '../models/series.dart';
import '../models/document.dart';

class V2Service {
  static final _dio = ApiClient.instance;

  static Future<List<Analyte>> getAnalytes() async {
    final res = await _dio.get('/v2/analytes');
    final list = res.data as List<dynamic>;
    return list.map((e) => Analyte.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<SeriesData> getSeries(String analyteKey, {int days = 365}) async {
    final res = await _dio.get('/v2/series', queryParameters: {
      'analyte_key': analyteKey,
      'days': days,
    });
    return SeriesData.fromJson(res.data as Map<String, dynamic>);
  }

  static Future<List<Document>> getDocuments() async {
    final res = await _dio.get('/v2/documents');
    final list = res.data as List<dynamic>;
    return list.map((e) => Document.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<Map<String, dynamic>> uploadDocument(String filePath, String filename) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: filename),
    });
    final res = await _dio.post(
      '/v2/documents',
      data: formData,
      options: Options(
        contentType: 'multipart/form-data',
        receiveTimeout: const Duration(minutes: 3),
      ),
    );
    return res.data as Map<String, dynamic>;
  }

  static Future<void> deleteDocument(String id) async {
    await _dio.delete('/v2/documents/$id');
  }

  // Doctor endpoints
  static Future<List<Map<String, dynamic>>> getDoctorPatients() async {
    final res = await _dio.get('/v2/doctor/patients');
    return (res.data as List<dynamic>).cast<Map<String, dynamic>>();
  }

  static Future<List<Analyte>> getDoctorPatientAnalytes(int patientId) async {
    final res = await _dio.get('/v2/doctor/patients/$patientId/analytes');
    final list = res.data as List<dynamic>;
    return list.map((e) => Analyte.fromJson(e as Map<String, dynamic>)).toList();
  }

  static Future<SeriesData> getDoctorPatientSeries(int patientId, String analyteKey) async {
    final res = await _dio.get('/v2/doctor/patients/$patientId/series',
        queryParameters: {'analyte_key': analyteKey});
    return SeriesData.fromJson(res.data as Map<String, dynamic>);
  }

  // Share
  static Future<void> grantAccess(String doctorEmail) async {
    await _dio.post('/share/grant', data: {'doctor_email': doctorEmail});
  }

  static Future<List<Map<String, dynamic>>> getGrants() async {
    final res = await _dio.get('/share/grants');
    return (res.data as List<dynamic>).cast<Map<String, dynamic>>();
  }

  static Future<void> revokeGrant(String doctorEmail) async {
    await _dio.delete('/share/revoke/$doctorEmail');
  }
}
