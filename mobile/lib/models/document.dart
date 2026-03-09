class Document {
  final String id;
  final String? sourceFilename;
  final String? analysisDate;
  final String? createdAt;
  final int numMetrics;

  Document({
    required this.id,
    this.sourceFilename,
    this.analysisDate,
    this.createdAt,
    required this.numMetrics,
  });

  factory Document.fromJson(Map<String, dynamic> json) => Document(
        id: json['id'] as String,
        sourceFilename: json['source_filename'] as String?,
        analysisDate: json['analysis_date'] as String?,
        createdAt: json['created_at'] as String?,
        numMetrics: json['num_metrics'] as int? ?? 0,
      );

  String get displayName => sourceFilename ?? 'Documento $id';

  String get displayDate {
    final dateStr = analysisDate ?? createdAt;
    if (dateStr == null) return '';
    try {
      final dt = DateTime.parse(dateStr);
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
    } catch (_) {
      return dateStr;
    }
  }
}
