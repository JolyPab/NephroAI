import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../models/analyte.dart';
import '../../models/series.dart';
import '../../services/v2_service.dart';
import '../../widgets/analyte_card.dart';
import '../../widgets/metric_chart.dart';

class DoctorPatientDetailScreen extends StatefulWidget {
  final int patientId;
  final String patientName;

  const DoctorPatientDetailScreen({
    super.key,
    required this.patientId,
    required this.patientName,
  });

  @override
  State<DoctorPatientDetailScreen> createState() => _DoctorPatientDetailScreenState();
}

class _DoctorPatientDetailScreenState extends State<DoctorPatientDetailScreen> {
  List<Analyte> _analytes = [];
  bool _loading = true;
  Analyte? _selected;
  SeriesData? _seriesData;
  bool _loadingSeries = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final analytes = await V2Service.getDoctorPatientAnalytes(widget.patientId);
      if (mounted) setState(() { _analytes = analytes; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadSeries(Analyte analyte) async {
    setState(() { _selected = analyte; _loadingSeries = true; _seriesData = null; });
    try {
      final s = await V2Service.getDoctorPatientSeries(widget.patientId, analyte.analyteKey);
      if (mounted) setState(() { _seriesData = s; _loadingSeries = false; });
    } catch (_) {
      if (mounted) setState(() => _loadingSeries = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.patientName),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/doctor/patients'),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : Row(
              children: [
                // Analytes list (left pane on large screens, full on mobile)
                SizedBox(
                  width: MediaQuery.of(context).size.width < 600
                      ? double.infinity
                      : 320,
                  child: _buildAnalytesList(),
                ),
              ],
            ),
    );
  }

  Widget _buildAnalytesList() {
    if (_selected != null && MediaQuery.of(context).size.width < 600) {
      return _buildSeriesView();
    }
    return Column(
      children: [
        if (_analytes.isEmpty)
          const Expanded(
            child: Center(
              child: Text(
                'No hay analitos para este paciente',
                style: TextStyle(color: AppTheme.textSecondary),
              ),
            ),
          )
        else
          Expanded(
            child: ListView.builder(
              itemCount: _analytes.length,
              itemBuilder: (ctx, i) => AnalyteCard(
                analyte: _analytes[i],
                onTap: () => _loadSeries(_analytes[i]),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildSeriesView() {
    return Scaffold(
      appBar: AppBar(
        title: Text(_selected!.displayName, overflow: TextOverflow.ellipsis),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => setState(() { _selected = null; _seriesData = null; }),
        ),
      ),
      body: _loadingSeries
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : _seriesData == null
              ? const Center(child: Text('Error cargando datos'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      if (_seriesData!.points.any((p) => p.y != null))
                        SizedBox(
                          height: 240,
                          child: MetricChart(seriesData: _seriesData!),
                        ),
                      const SizedBox(height: 16),
                      ..._seriesData!.points.reversed.map((p) => Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceCard,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppTheme.border),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    p.y != null
                                        ? '${p.y!.toStringAsFixed(2)} ${_seriesData!.unit ?? ''}'
                                        : p.text ?? '—',
                                    style: const TextStyle(fontWeight: FontWeight.w600),
                                  ),
                                ),
                                Text(
                                  _fmt(p.t),
                                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                                ),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),
    );
  }

  String _fmt(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }
}
