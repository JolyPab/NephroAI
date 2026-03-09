class SeriesPoint {
  final String? t;
  final double? y;
  final String? text;
  final String? evidence;

  SeriesPoint({this.t, this.y, this.text, this.evidence});

  factory SeriesPoint.fromJson(Map<String, dynamic> json) => SeriesPoint(
        t: json['t'] as String?,
        y: (json['y'] as num?)?.toDouble(),
        text: json['text'] as String?,
        evidence: json['evidence'] as String?,
      );

  DateTime? get dateTime => t != null ? DateTime.tryParse(t!) : null;
}

class SeriesData {
  final String analyteKey;
  final String? rawName;
  final String seriesType;
  final String? unit;
  final Map<String, dynamic>? reference;
  final List<SeriesPoint> points;

  SeriesData({
    required this.analyteKey,
    this.rawName,
    required this.seriesType,
    this.unit,
    this.reference,
    required this.points,
  });

  factory SeriesData.fromJson(Map<String, dynamic> json) => SeriesData(
        analyteKey: json['analyte_key'] as String,
        rawName: json['raw_name'] as String?,
        seriesType: json['series_type'] as String? ?? 'numeric',
        unit: json['unit'] as String?,
        reference: json['reference'] as Map<String, dynamic>?,
        points: (json['points'] as List<dynamic>? ?? [])
            .map((p) => SeriesPoint.fromJson(p as Map<String, dynamic>))
            .toList(),
      );

  double? get refLow {
    if (reference == null) return null;
    final v = reference!['low'] ?? reference!['min'];
    return (v as num?)?.toDouble();
  }

  double? get refHigh {
    if (reference == null) return null;
    final v = reference!['high'] ?? reference!['max'];
    return (v as num?)?.toDouble();
  }
}
