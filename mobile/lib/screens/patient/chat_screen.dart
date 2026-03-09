import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../models/advice.dart';
import '../../services/advice_service.dart';
import '../../services/auth_service.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _loading = false;

  static const _quickQuestions = [
    '¿Cuáles son mis valores fuera de rango?',
    '¿Cómo han evolucionado mis análisis?',
    '¿Qué debo comentar con mi médico?',
    'Resume mi estado de salud actual',
  ];

  @override
  void dispose() {
    _controller.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send(String question) async {
    if (question.trim().isEmpty || _loading) return;
    setState(() {
      _messages.add(ChatMessage(text: question, isUser: true));
      _loading = true;
    });
    _controller.clear();
    _scrollToBottom();

    try {
      final res = await AdviceService.ask(question.trim());
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(
            text: res.answer,
            isUser: false,
            metrics: res.usedMetrics,
          ));
          _loading = false;
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add(ChatMessage(
            text: 'Error: ${AuthService.extractErrorMessage(e)}',
            isUser: false,
          ));
          _loading = false;
        });
        _scrollToBottom();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat IA'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty ? _buildWelcome() : _buildMessages(),
          ),
          _buildInput(),
        ],
      ),
    );
  }

  Widget _buildWelcome() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 24),
          const Center(
            child: Icon(Icons.smart_toy_outlined, size: 64, color: AppTheme.primary),
          ),
          const SizedBox(height: 16),
          const Center(
            child: Text(
              'Asistente de Laboratorio IA',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(height: 8),
          const Center(
            child: Text(
              'Pregunta sobre tus análisis de laboratorio',
              style: TextStyle(color: AppTheme.textSecondary),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 32),
          const Text(
            'Preguntas frecuentes',
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
          ),
          const SizedBox(height: 12),
          ..._quickQuestions.map((q) => GestureDetector(
                onTap: () => _send(q),
                child: Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceCard,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    children: [
                      Expanded(child: Text(q, style: const TextStyle(fontSize: 14))),
                      const Icon(Icons.arrow_forward_ios, size: 14, color: AppTheme.textSecondary),
                    ],
                  ),
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildMessages() {
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.all(16),
      itemCount: _messages.length + (_loading ? 1 : 0),
      itemBuilder: (ctx, i) {
        if (i == _messages.length && _loading) {
          return _BubbleLoading();
        }
        final msg = _messages[i];
        return msg.isUser ? _UserBubble(msg) : _AiBubble(msg);
      },
    );
  }

  Widget _buildInput() {
    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceCard,
        border: Border(top: BorderSide(color: AppTheme.border)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              maxLines: null,
              textInputAction: TextInputAction.send,
              onSubmitted: _send,
              decoration: const InputDecoration(
                hintText: 'Escribe tu pregunta...',
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                fillColor: Colors.transparent,
              ),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: () => _send(_controller.text),
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: AppTheme.primary,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}

class _UserBubble extends StatelessWidget {
  final ChatMessage msg;
  const _UserBubble(this.msg);

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12, left: 60),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.primary,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(msg.text, style: const TextStyle(color: Colors.white)),
      ),
    );
  }
}

class _AiBubble extends StatelessWidget {
  final ChatMessage msg;
  const _AiBubble(this.msg);

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12, right: 60),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(msg.text, style: const TextStyle(fontSize: 14, height: 1.5)),
            if (msg.metrics.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Divider(color: AppTheme.border, height: 1),
              const SizedBox(height: 8),
              Text(
                'Métricas usadas (${msg.metrics.length})',
                style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
              ),
              ...msg.metrics.take(3).map((m) => Text(
                    '• ${m.name}: ${m.value.toStringAsFixed(2)} ${m.unit ?? ''}',
                    style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                  )),
            ],
          ],
        ),
      ),
    );
  }
}

class _BubbleLoading extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surfaceCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.border),
        ),
        child: const SizedBox(
          height: 16,
          width: 40,
          child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
        ),
      ),
    );
  }
}
