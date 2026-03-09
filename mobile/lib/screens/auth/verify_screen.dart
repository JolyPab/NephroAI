import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme.dart';
import '../../services/auth_service.dart';

class VerifyScreen extends StatefulWidget {
  final String email;
  const VerifyScreen({super.key, required this.email});

  @override
  State<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends State<VerifyScreen> {
  final _codeCtrl = TextEditingController();
  bool _loading = false;
  bool _resending = false;

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    final code = _codeCtrl.text.trim();
    if (code.length != 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingresa el código de 6 dígitos')),
      );
      return;
    }
    setState(() => _loading = true);
    try {
      await AuthService.verifyEmail(widget.email, code);
      // After verify, log in directly
      if (mounted) context.go('/login');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AuthService.extractErrorMessage(e)),
            backgroundColor: AppTheme.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resend() async {
    setState(() => _resending = true);
    try {
      await AuthService.resendCode(widget.email);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Código reenviado'), backgroundColor: AppTheme.success),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AuthService.extractErrorMessage(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Verificar correo')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 24),
              const Icon(Icons.mark_email_read_outlined, size: 64, color: AppTheme.primary),
              const SizedBox(height: 24),
              const Text(
                'Revisa tu correo',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                'Enviamos un código de 6 dígitos a ${widget.email}',
                style: const TextStyle(color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 32),
              TextFormField(
                controller: _codeCtrl,
                keyboardType: TextInputType.number,
                maxLength: 6,
                style: const TextStyle(fontSize: 24, letterSpacing: 8),
                textAlign: TextAlign.center,
                decoration: const InputDecoration(
                  labelText: 'Código de verificación',
                  counterText: '',
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _loading ? null : _verify,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                      )
                    : const Text('Verificar'),
              ),
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: _resending ? null : _resend,
                  child: Text(_resending ? 'Reenviando...' : 'Reenviar código'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
