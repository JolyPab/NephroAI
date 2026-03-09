import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../services/v2_service.dart';

class DoctorPatientsScreen extends StatefulWidget {
  const DoctorPatientsScreen({super.key});

  @override
  State<DoctorPatientsScreen> createState() => _DoctorPatientsScreenState();
}

class _DoctorPatientsScreenState extends State<DoctorPatientsScreen> {
  List<Map<String, dynamic>> _patients = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final patients = await V2Service.getDoctorPatients();
      if (mounted) setState(() { _patients = patients; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mis pacientes'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        actions: [
          IconButton(icon: const Icon(Icons.refresh_outlined), onPressed: _load),
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
              : _patients.isEmpty
                  ? const Center(
                      child: Text(
                        'No tienes pacientes asignados todavía',
                        style: TextStyle(color: AppTheme.textSecondary),
                      ),
                    )
                  : RefreshIndicator(
                      color: AppTheme.primary,
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _patients.length,
                        itemBuilder: (ctx, i) {
                          final p = _patients[i];
                          final name = p['display_name']?.toString() ?? p['email']?.toString() ?? 'Paciente';
                          final email = p['email']?.toString() ?? '';
                          final lastDate = p['latest_analysis_date']?.toString();
                          return Card(
                            margin: const EdgeInsets.only(bottom: 10),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () => context.go(
                                '/doctor/patient/${p['patient_id']}?name=${Uri.encodeComponent(name)}',
                              ),
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Row(
                                  children: [
                                    CircleAvatar(
                                      backgroundColor: AppTheme.primary.withAlpha(30),
                                      child: Text(
                                        name.substring(0, 1).toUpperCase(),
                                        style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700),
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
                                          Text(email, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                                          if (lastDate != null)
                                            Text(
                                              'Último análisis: ${_fmt(lastDate)}',
                                              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11),
                                            ),
                                        ],
                                      ),
                                    ),
                                    const Icon(Icons.chevron_right, color: AppTheme.textSecondary),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }

  String _fmt(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
    } catch (_) {
      return iso;
    }
  }
}
