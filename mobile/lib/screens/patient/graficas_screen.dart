import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../models/analyte.dart';
import '../../services/v2_service.dart';
import '../../widgets/analyte_card.dart';

class GraficasScreen extends StatefulWidget {
  const GraficasScreen({super.key});

  @override
  State<GraficasScreen> createState() => _GraficasScreenState();
}

class _GraficasScreenState extends State<GraficasScreen> {
  List<Analyte> _analytes = [];
  List<Analyte> _filtered = [];
  bool _loading = true;
  String? _error;
  bool _onlyNumeric = true;
  final int _navIndex = 2;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final analytes = await V2Service.getAnalytes();
      if (mounted) {
        setState(() {
          _analytes = analytes;
          _applyFilter();
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  void _applyFilter({String search = ''}) {
    var list = _onlyNumeric
        ? _analytes.where((a) => a.lastValueNumeric != null).toList()
        : _analytes;
    if (search.isNotEmpty) {
      list = list
          .where((a) => a.displayName.toLowerCase().contains(search.toLowerCase()))
          .toList();
    }
    _filtered = list;
  }

  void _onSearch(String q) {
    setState(() => _applyFilter(search: q));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Tendencias de métricas'),
            Text(
              'Elige una métrica para ver su tendencia',
              style: TextStyle(fontSize: 11, color: AppTheme.textSecondary),
            ),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : _error != null
              ? _buildError()
              : _buildContent(),
      bottomNavigationBar: _buildNav(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: AppTheme.danger),
            const SizedBox(height: 16),
            Text(_error!, textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textSecondary)),
            const SizedBox(height: 24),
            ElevatedButton(onPressed: _load, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    return Column(
      children: [
        // Search + filter bar
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: TextField(
            onChanged: _onSearch,
            decoration: const InputDecoration(
              hintText: 'Buscar métrica...',
              prefixIcon: Icon(Icons.search, color: AppTheme.textSecondary),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
          child: Row(
            children: [
              _filterChip('Solo numéricas', _onlyNumeric, () {
                setState(() {
                  _onlyNumeric = !_onlyNumeric;
                  _applyFilter();
                });
              }),
              const SizedBox(width: 8),
              Text(
                '${_filtered.length} métricas',
                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
              ),
            ],
          ),
        ),
        // Analyte list
        if (_filtered.isEmpty)
          const Expanded(
            child: Center(
              child: Text(
                'No hay métricas.\nSube un PDF para comenzar.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppTheme.textSecondary),
              ),
            ),
          )
        else
          Expanded(
            child: RefreshIndicator(
              color: AppTheme.primary,
              onRefresh: _load,
              child: ListView.builder(
                itemCount: _filtered.length,
                itemBuilder: (ctx, i) {
                  final a = _filtered[i];
                  return AnalyteCard(
                    analyte: a,
                    onTap: () => context.go(
                      '/series?key=${Uri.encodeComponent(a.analyteKey)}&name=${Uri.encodeComponent(a.displayName)}',
                    ),
                  );
                },
              ),
            ),
          ),
      ],
    );
  }

  Widget _filterChip(String label, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: active ? AppTheme.primary : AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: active ? AppTheme.primary : AppTheme.border),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: active ? Colors.white : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildNav() {
    return BottomNavigationBar(
      currentIndex: _navIndex,
      onTap: (i) {
        switch (i) {
          case 0:
            context.go('/dashboard');
            break;
          case 1:
            context.go('/upload');
            break;
          case 2:
            break; // already here
          case 3:
            context.go('/chat');
            break;
          case 4:
            context.go('/profile');
            break;
        }
      },
      items: const [
        BottomNavigationBarItem(icon: Icon(Icons.home_outlined), label: 'Inicio'),
        BottomNavigationBarItem(icon: Icon(Icons.upload_file_outlined), label: 'Subir'),
        BottomNavigationBarItem(icon: Icon(Icons.bar_chart_outlined), label: 'Graficas'),
        BottomNavigationBarItem(icon: Icon(Icons.chat_outlined), label: 'IA Chat'),
        BottomNavigationBarItem(icon: Icon(Icons.person_outline), label: 'Perfil'),
      ],
    );
  }
}
