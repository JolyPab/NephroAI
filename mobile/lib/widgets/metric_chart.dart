import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/series.dart';

class MetricChart extends StatelessWidget {
  final SeriesData seriesData;

  const MetricChart({super.key, required this.seriesData});

  @override
  Widget build(BuildContext context) {
    final points = seriesData.points
        .where((p) => p.y != null && p.dateTime != null)
        .toList()
      ..sort((a, b) => a.dateTime!.compareTo(b.dateTime!));

    if (points.isEmpty) {
      return const Center(
        child: Text('Sin datos numéricos', style: TextStyle(color: AppTheme.textSecondary)),
      );
    }

    final spots = points.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.y!);
    }).toList();

    final minY = spots.map((s) => s.y).reduce((a, b) => a < b ? a : b);
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final padding = (maxY - minY) * 0.2 + 1;

    return LineChart(
      LineChartData(
        minY: minY - padding,
        maxY: maxY + padding,
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            curveSmoothness: 0.3,
            color: AppTheme.primary,
            barWidth: 2.5,
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, barData, index) => FlDotCirclePainter(
                radius: 4,
                color: AppTheme.primary,
                strokeWidth: 2,
                strokeColor: Colors.white,
              ),
            ),
            belowBarData: BarAreaData(
              show: true,
              color: AppTheme.primary.withAlpha(40),
            ),
          ),
        ],
        extraLinesData: ExtraLinesData(
          horizontalLines: [
            if (seriesData.refLow != null)
              HorizontalLine(
                y: seriesData.refLow!,
                color: AppTheme.warning.withAlpha(150),
                strokeWidth: 1,
                dashArray: [5, 5],
                label: HorizontalLineLabel(
                  show: true,
                  labelResolver: (_) => 'Min',
                  style: const TextStyle(color: AppTheme.warning, fontSize: 10),
                ),
              ),
            if (seriesData.refHigh != null)
              HorizontalLine(
                y: seriesData.refHigh!,
                color: AppTheme.warning.withAlpha(150),
                strokeWidth: 1,
                dashArray: [5, 5],
                label: HorizontalLineLabel(
                  show: true,
                  labelResolver: (_) => 'Max',
                  style: const TextStyle(color: AppTheme.warning, fontSize: 10),
                ),
              ),
          ],
        ),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (_) => FlLine(
            color: AppTheme.border,
            strokeWidth: 1,
          ),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: spots.length > 6 ? (spots.length / 5).ceilToDouble() : 1,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx >= 0 && idx < points.length) {
                  final dt = points[idx].dateTime!;
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      '${dt.month}/${dt.year.toString().substring(2)}',
                      style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary),
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 42,
              getTitlesWidget: (value, meta) => Text(
                value.toStringAsFixed(1),
                style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary),
              ),
            ),
          ),
        ),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => AppTheme.surfaceCard,
            getTooltipItems: (spots) => spots.map((s) {
              final idx = s.spotIndex;
              final point = points[idx];
              final dt = point.dateTime!;
              final dateStr =
                  '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
              return LineTooltipItem(
                '${s.y.toStringAsFixed(2)} ${seriesData.unit ?? ''}\n$dateStr',
                const TextStyle(color: AppTheme.textPrimary, fontSize: 12),
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}
