class Analyte {
  final String analyteKey;
  final String? rawName;
  final double? lastValueNumeric;
  final String? lastValueText;
  final String? lastDate;
  final String? unit;

  Analyte({
    required this.analyteKey,
    this.rawName,
    this.lastValueNumeric,
    this.lastValueText,
    this.lastDate,
    this.unit,
  });

  factory Analyte.fromJson(Map<String, dynamic> json) => Analyte(
        analyteKey: json['analyte_key'] as String,
        rawName: json['raw_name'] as String?,
        lastValueNumeric: (json['last_value_numeric'] as num?)?.toDouble(),
        lastValueText: json['last_value_text'] as String?,
        lastDate: json['last_date'] as String?,
        unit: json['unit'] as String?,
      );

  String get displayName {
    if (rawName != null && rawName!.isNotEmpty) return rawName!;
    return analyteKey.replaceAll('__', ' ').replaceAll('_', ' ');
  }

  String get displayValue {
    if (lastValueNumeric != null) {
      final formatted = lastValueNumeric! % 1 == 0
          ? lastValueNumeric!.toInt().toString()
          : lastValueNumeric!.toStringAsFixed(2);
      return unit != null ? '$formatted $unit' : formatted;
    }
    return lastValueText ?? '—';
  }
}
