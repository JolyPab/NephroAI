import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../models/user.dart';
import '../../services/auth_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  User? _user;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final user = await AuthService.getMe();
      if (mounted) setState(() { _user = user; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceCard,
        title: const Text('Cerrar sesión'),
        content: const Text('¿Estás seguro de que quieres salir?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Salir', style: TextStyle(color: AppTheme.danger)),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    await AuthService.logout();
    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Perfil'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : _buildContent(),
    );
  }

  Widget _buildContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const SizedBox(height: 24),
          CircleAvatar(
            radius: 48,
            backgroundColor: AppTheme.primary.withAlpha(30),
            child: Text(
              _user?.displayName.substring(0, 1).toUpperCase() ?? '?',
              style: const TextStyle(fontSize: 36, color: AppTheme.primary, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            _user?.displayName ?? 'Usuario',
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
          ),
          Text(
            _user?.email ?? '',
            style: const TextStyle(color: AppTheme.textSecondary),
          ),
          if (_user?.isDoctor == true) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: AppTheme.primary.withAlpha(30),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Text('Médico', style: TextStyle(color: AppTheme.primary, fontSize: 13)),
            ),
          ],
          const SizedBox(height: 40),
          _MenuItem(
            icon: Icons.share_outlined,
            label: 'Compartir con médico',
            onTap: () => context.go('/share'),
          ),
          const SizedBox(height: 8),
          if (_user?.isDoctor == true)
            _MenuItem(
              icon: Icons.people_outline,
              label: 'Mis pacientes',
              onTap: () => context.go('/doctor/patients'),
            ),
          const SizedBox(height: 8),
          _MenuItem(
            icon: Icons.description_outlined,
            label: 'Mis documentos',
            onTap: () => context.go('/upload'),
          ),
          const SizedBox(height: 32),
          OutlinedButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout, color: AppTheme.danger),
            label: const Text('Cerrar sesión', style: TextStyle(color: AppTheme.danger)),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: AppTheme.danger),
              minimumSize: const Size(double.infinity, 50),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        ],
      ),
    );
  }
}

class _MenuItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _MenuItem({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surfaceCard,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            children: [
              Icon(icon, color: AppTheme.primary),
              const SizedBox(width: 12),
              Expanded(child: Text(label, style: const TextStyle(fontSize: 15))),
              const Icon(Icons.chevron_right, color: AppTheme.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}
