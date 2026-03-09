import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'core/storage.dart';
import 'core/theme.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/auth/verify_screen.dart';
import 'screens/patient/dashboard_screen.dart';
import 'screens/patient/series_screen.dart';
import 'screens/patient/upload_screen.dart';
import 'screens/patient/chat_screen.dart';
import 'screens/patient/profile_screen.dart';
import 'screens/patient/graficas_screen.dart';
import 'screens/patient/share_screen.dart';
import 'screens/doctor/patients_screen.dart';
import 'screens/doctor/patient_detail_screen.dart';

final _router = GoRouter(
  initialLocation: '/login',
  redirect: (context, state) async {
    final hasToken = await Storage.hasToken();
    final isAuthRoute = state.matchedLocation.startsWith('/login') ||
        state.matchedLocation.startsWith('/register') ||
        state.matchedLocation.startsWith('/verify');

    if (!hasToken && !isAuthRoute) return '/login';
    if (hasToken && state.matchedLocation == '/login') return '/dashboard';
    return null;
  },
  routes: [
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
    GoRoute(
      path: '/verify',
      builder: (_, state) => VerifyScreen(
        email: state.uri.queryParameters['email'] ?? '',
      ),
    ),
    GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
    GoRoute(
      path: '/series',
      builder: (_, state) => SeriesScreen(
        analyteKey: state.uri.queryParameters['key'] ?? '',
        analyteName: state.uri.queryParameters['name'] ?? 'Analito',
      ),
    ),
    GoRoute(path: '/graficas', builder: (_, __) => const GraficasScreen()),
    GoRoute(path: '/upload', builder: (_, __) => const UploadScreen()),
    GoRoute(path: '/chat', builder: (_, __) => const ChatScreen()),
    GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
    GoRoute(path: '/share', builder: (_, __) => const ShareScreen()),
    GoRoute(path: '/doctor/patients', builder: (_, __) => const DoctorPatientsScreen()),
    GoRoute(
      path: '/doctor/patient/:id',
      builder: (_, state) => DoctorPatientDetailScreen(
        patientId: int.tryParse(state.pathParameters['id'] ?? '0') ?? 0,
        patientName: state.uri.queryParameters['name'] ?? 'Paciente',
      ),
    ),
  ],
);

class NephroAIApp extends StatelessWidget {
  const NephroAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'NephroAI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark,
      routerConfig: _router,
    );
  }
}
