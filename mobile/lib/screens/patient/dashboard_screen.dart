import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../models/analyte.dart';
import '../../services/auth_service.dart';
import '../../services/v2_service.dart';
import '../../widgets/analyte_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<Analyte> _analytes = [];
  List<Analyte> _filtered = [];
  bool _loading = true;
  String? _error;
  String _search = '';
  String? _userName;
  int _navIndex = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait([
        V2Service.getAnalytes(),
        AuthService.getMe(),
      ]);
      if (mounted) {
        setState(() {
          _analytes = results[0] as List<Analyte>;
          _filtered = _analytes;
          _userName = (results[1] as dynamic).displayName;
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

  void _onSearch(String q) {
    setState(() {
      _search = q;
      _filtered = q.isEmpty
          ? _analytes
          : _analytes
              .where((a) =>
                  a.displayName.toLowerCase().contains(q.toLowerCase()))
              .toList();
    });
  }

  String? get _latestDate {
    final dates = _analytes
        .where((a) => a.lastDate != null)
        .map((a) => a.lastDate!)
        .toList();
    if (dates.isEmpty) return null;
    dates.sort();
    return _formatDate(dates.last);
  }

  List<Analyte> get _keyMetrics =>
      _analytes.where((a) => a.lastValueNumeric != null).take(3).toList();

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
            Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppTheme.textSecondary)),
            const SizedBox(height: 24),
            ElevatedButton(onPressed: _load, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    final numericCount = _analytes.where((a) => a.lastValueNumeric != null).length;
    final latestDate = _latestDate;
    final keyMetrics = _keyMetrics;

    return SafeArea(
      child: RefreshIndicator(
        color: AppTheme.primary,
        onRefresh: _load,
        child: CustomScrollView(
          slivers: [
            // ── Header ──────────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 20, 16, 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'NephroAI',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.primary,
                          ),
                        ),
                        Text(
                          _userName != null && _userName!.isNotEmpty
                              ? '¡Bienvenido, $_userName!'
                              : '¡Bienvenido!',
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh_outlined),
                      onPressed: () {
                        setState(() => _loading = true);
                        _load();
                      },
                    ),
                  ],
                ),
              ),
            ),

            // ── Summary card ─────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                child: Container(
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color.fromRGBO(37, 99, 235, 0.35)),
                  ),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.check_circle_outline, color: AppTheme.success, size: 18),
                          const SizedBox(width: 8),
                          const Text(
                            'Tus últimos resultados',
                            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          _statItem('SEGUIDAS', '$numericCount'),
                          const SizedBox(width: 32),
                          if (latestDate != null) ...[
                            _statItem('MÁS RECIENTE', latestDate),
                            const SizedBox(width: 32),
                          ],
                          _statItem('TOTAL', '${_analytes.length}'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // ── Métricas clave ────────────────────────────────────────
            if (keyMetrics.isNotEmpty) ...[
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(20, 20, 20, 10),
                  child: Text(
                    'Métricas clave',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: SizedBox(
                  height: 130,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: keyMetrics.length,
                    itemBuilder: (ctx, i) => _metricCard(keyMetrics[i]),
                  ),
                ),
              ),
            ],

            // ── Acciones rápidas ──────────────────────────────────────
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.fromLTRB(20, 20, 20, 10),
                child: Text(
                  'Acciones rápidas',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    Expanded(
                      child: _actionBtn(
                        Icons.upload_file_outlined,
                        'Subir nuevo PDF',
                        () => context.go('/upload'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _actionBtn(
                        Icons.chat_outlined,
                        'Preguntar a IA',
                        () => context.go('/chat'),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // ── Mis análisis header ───────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
                child: Row(
                  children: [
                    const Text(
                      'Mis análisis',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const Spacer(),
                    Text(
                      '${_analytes.length} analitos',
                      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                    ),
                  ],
                ),
              ),
            ),

            // ── Search ────────────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: TextField(
                  onChanged: _onSearch,
                  decoration: const InputDecoration(
                    hintText: 'Buscar analito...',
                    prefixIcon: Icon(Icons.search, color: AppTheme.textSecondary),
                  ),
                ),
              ),
            ),

            // ── Analyte list ──────────────────────────────────────────
            if (_filtered.isEmpty)
              const SliverToBoxAdapter(
                child: Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text(
                      'No hay analitos todavía.\nSube un PDF de laboratorio.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppTheme.textSecondary),
                    ),
                  ),
                ),
              )
            else
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (ctx, i) => AnalyteCard(
                    analyte: _filtered[i],
                    onTap: () => context.go(
                      '/series?key=${Uri.encodeComponent(_filtered[i].analyteKey)}&name=${Uri.encodeComponent(_filtered[i].displayName)}',
                    ),
                  ),
                  childCount: _filtered.length,
                ),
              ),

            const SliverToBoxAdapter(child: SizedBox(height: 16)),
          ],
        ),
      ),
    );
  }

  Widget _statItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            color: AppTheme.textSecondary,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Widget _metricCard(Analyte a) {
    return GestureDetector(
      onTap: () => context.go(
        '/series?key=${Uri.encodeComponent(a.analyteKey)}&name=${Uri.encodeComponent(a.displayName)}',
      ),
      child: Container(
        width: 155,
        margin: const EdgeInsets.only(right: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              a.displayName,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
            ),
            const SizedBox(height: 6),
            Text(
              a.displayValue,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.bold,
                color: AppTheme.primary,
              ),
            ),
            const Spacer(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (a.lastDate != null)
                  Text(
                    _formatDate(a.lastDate!),
                    style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary),
                  ),
                const Text(
                  'Ver →',
                  style: TextStyle(fontSize: 11, color: AppTheme.primary),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _actionBtn(IconData icon, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          children: [
            Icon(icon, color: AppTheme.primary, size: 22),
            const SizedBox(height: 5),
            Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
          ],
        ),
      ),
    );
  }

  Widget _buildNav() {
    return BottomNavigationBar(
      currentIndex: _navIndex,
      onTap: (i) {
        setState(() => _navIndex = i);
        switch (i) {
          case 0:
            break;
          case 1:
            context.go('/upload');
            break;
          case 2:
            context.go('/graficas');
            break;
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
