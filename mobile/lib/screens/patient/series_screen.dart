import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../models/series.dart';
import '../../services/v2_service.dart';
import '../../widgets/metric_chart.dart';

class SeriesScreen extends StatefulWidget {
  final String analyteKey;
  final String analyteName;

  const SeriesScreen({super.key, required this.analyteKey, required this.analyteName});

  @override
  State<SeriesScreen> createState() => _SeriesScreenState();
}

class _SeriesScreenState extends State<SeriesScreen> {
  SeriesData? _data;
  bool _loading = true;
  String? _error;
  int _days = 365;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await V2Service.getSeries(widget.analyteKey, days: _days);
      if (mounted) setState(() { _data = data; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.analyteName, overflow: TextOverflow.ellipsis),
        actions: [
          PopupMenuButton<int>(
            icon: const Icon(Icons.calendar_today_outlined),
            onSelected: (v) { _days = v; _load(); },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 90, child: Text('3 meses')),
              PopupMenuItem(value: 180, child: Text('6 meses')),
              PopupMenuItem(value: 365, child: Text('1 año')),
              PopupMenuItem(value: 730, child: Text('2 años')),
              PopupMenuItem(value: 9999, child: Text('Todo el historial')),
            ],
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!, style: const TextStyle(color: AppTheme.danger)),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _load, child: const Text('Reintentar')),
                    ],
                  ),
                )
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final data = _data!;
    final numericPoints = data.points.where((p) => p.y != null).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Expanded(
                child: _StatCard(
                  label: 'Registros',
                  value: '${data.points.length}',
                ),
              ),
              const SizedBox(width: 12),
              if (data.unit != null)
                Expanded(
                  child: _StatCard(label: 'Unidad', value: data.unit!),
                ),
              if (data.refLow != null || data.refHigh != null) ...[
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    label: 'Referencia',
                    value: '${data.refLow?.toStringAsFixed(1) ?? '?'} – ${data.refHigh?.toStringAsFixed(1) ?? '?'}',
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 20),
          // Chart
          if (numericPoints.isNotEmpty) ...[
            const Text(
              'Evolución temporal',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 240,
              child: MetricChart(seriesData: data),
            ),
          ],
          const SizedBox(height: 24),
          // History table
          const Text(
            'Historial',
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
          ),
          const SizedBox(height: 12),
          ...data.points.reversed.map((p) => _PointTile(point: p, unit: data.unit)),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  const _StatCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
        ],
      ),
    );
  }
}

class _PointTile extends StatelessWidget {
  final SeriesPoint point;
  final String? unit;
  const _PointTile({required this.point, this.unit});

  @override
  Widget build(BuildContext context) {
    final value = point.y != null
        ? '${point.y!.toStringAsFixed(2)} ${unit ?? ''}'
        : point.text ?? '—';

    return Container(
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
              value,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
            ),
          ),
          Text(
            _formatDate(point.t),
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  String _formatDate(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }
}
