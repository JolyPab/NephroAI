class AdviceMetric {
  final String name;
  final double value;
  final String? unit;
  final String dateIso;

  AdviceMetric({
    required this.name,
    required this.value,
    this.unit,
    required this.dateIso,
  });

  factory AdviceMetric.fromJson(Map<String, dynamic> json) => AdviceMetric(
        name: json['name'] as String,
        value: (json['value'] as num).toDouble(),
        unit: json['unit'] as String?,
        dateIso: json['dateISO'] as String? ?? '',
      );
}

class AdviceResponse {
  final String answer;
  final List<AdviceMetric> usedMetrics;

  AdviceResponse({required this.answer, required this.usedMetrics});

  factory AdviceResponse.fromJson(Map<String, dynamic> json) => AdviceResponse(
        answer: json['answer'] as String,
        usedMetrics: (json['usedMetrics'] as List<dynamic>? ?? [])
            .map((m) => AdviceMetric.fromJson(m as Map<String, dynamic>))
            .toList(),
      );
}

class ChatMessage {
  final String text;
  final bool isUser;
  final List<AdviceMetric> metrics;

  ChatMessage({required this.text, required this.isUser, this.metrics = const []});
}
