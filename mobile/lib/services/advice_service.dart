import '../core/api_client.dart';
import '../models/advice.dart';

class AdviceService {
  static final _dio = ApiClient.instance;

  static Future<AdviceResponse> ask(
    String question, {
    List<String>? metricNames,
    int days = 180,
    String language = 'es',
  }) async {
    final body = <String, dynamic>{
      'question': question,
      'days': days,
      'language': language,
    };
    if (metricNames != null && metricNames.isNotEmpty) {
      body['metricNames'] = metricNames;
    }
    final res = await _dio.post('/advice', data: body);
    return AdviceResponse.fromJson(res.data as Map<String, dynamic>);
  }
}
