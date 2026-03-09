import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../services/v2_service.dart';

class ShareScreen extends StatefulWidget {
  const ShareScreen({super.key});

  @override
  State<ShareScreen> createState() => _ShareScreenState();
}

class _ShareScreenState extends State<ShareScreen> {
  final _emailCtrl = TextEditingController();
  List<Map<String, dynamic>> _grants = [];
  bool _loading = false;
  bool _granting = false;

  @override
  void initState() {
    super.initState();
    _loadGrants();
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadGrants() async {
    setState(() => _loading = true);
    try {
      final grants = await V2Service.getGrants();
      if (mounted) setState(() { _grants = grants; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _grant() async {
    final email = _emailCtrl.text.trim();
    if (email.isEmpty) return;
    setState(() => _granting = true);
    try {
      await V2Service.grantAccess(email);
      _emailCtrl.clear();
      await _loadGrants();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Acceso concedido'),
            backgroundColor: AppTheme.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.danger),
        );
      }
    } finally {
      if (mounted) setState(() => _granting = false);
    }
  }

  Future<void> _revoke(String doctorEmail) async {
    try {
      await V2Service.revokeGrant(doctorEmail);
      await _loadGrants();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Acceso revocado')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.danger),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Compartir con médico'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Conceder acceso',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
            const SizedBox(height: 8),
            const Text(
              'Ingresa el correo de tu médico para compartir tus análisis',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Correo del médico',
                prefixIcon: Icon(Icons.email_outlined, color: AppTheme.textSecondary),
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: _granting ? null : _grant,
              icon: _granting
                  ? const SizedBox(width: 16, height: 16,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.share_outlined),
              label: const Text('Conceder acceso'),
            ),
            const SizedBox(height: 32),
            const Text(
              'Médicos con acceso',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
            const SizedBox(height: 12),
            if (_loading)
              const Center(child: CircularProgressIndicator(color: AppTheme.primary))
            else if (_grants.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No has compartido con ningún médico todavía',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppTheme.textSecondary),
                  ),
                ),
              )
            else
              ..._grants.map((g) => _GrantTile(
                    grant: g,
                    onRevoke: () => _revoke(g['doctor_email']?.toString() ?? ''),
                  )),
          ],
        ),
      ),
    );
  }
}

class _GrantTile extends StatelessWidget {
  final Map<String, dynamic> grant;
  final VoidCallback onRevoke;
  const _GrantTile({required this.grant, required this.onRevoke});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.medical_services_outlined, color: AppTheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  grant['doctor_name']?.toString() ?? grant['doctor_email']?.toString() ?? '—',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                if (grant['doctor_email'] != null)
                  Text(
                    grant['doctor_email'].toString(),
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                  ),
              ],
            ),
          ),
          TextButton(
            onPressed: onRevoke,
            child: const Text('Revocar', style: TextStyle(color: AppTheme.danger)),
          ),
        ],
      ),
    );
  }
}
