import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../models/document.dart';
import '../../services/v2_service.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  List<Document> _documents = [];
  bool _loadingDocs = true;
  bool _uploading = false;
  String? _uploadStatus;
  bool _uploadSuccess = false;

  @override
  void initState() {
    super.initState();
    _loadDocuments();
  }

  Future<void> _loadDocuments() async {
    try {
      final docs = await V2Service.getDocuments();
      if (mounted) setState(() { _documents = docs; _loadingDocs = false; });
    } catch (_) {
      if (mounted) setState(() => _loadingDocs = false);
    }
  }

  Future<void> _pickAndUpload() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );
    if (result == null || result.files.single.path == null) return;

    final file = result.files.single;
    setState(() {
      _uploading = true;
      _uploadStatus = 'Subiendo ${file.name}...';
      _uploadSuccess = false;
    });

    try {
      final res = await V2Service.uploadDocument(file.path!, file.name);
      final isDuplicate = res.containsKey('duplicate') && res['duplicate'] == true;
      if (mounted) {
        setState(() {
          _uploading = false;
          _uploadSuccess = true;
          _uploadStatus = isDuplicate
              ? 'Documento duplicado — ya existe en tu historial'
              : 'Documento procesado: ${res['num_metrics'] ?? '?'} métricas extraídas';
        });
        await _loadDocuments();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _uploading = false;
          _uploadSuccess = false;
          _uploadStatus = 'Error: ${e.toString().replaceAll('DioException', '').trim()}';
        });
      }
    }
  }

  Future<void> _delete(String id) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceCard,
        title: const Text('Eliminar documento'),
        content: const Text('¿Eliminar este documento y todas sus métricas?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Eliminar', style: TextStyle(color: AppTheme.danger)),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await V2Service.deleteDocument(id);
      await _loadDocuments();
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
        title: const Text('Subir resultados'),
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
            // Upload card
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.surfaceCard,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
              ),
              child: Column(
                children: [
                  Icon(
                    _uploadSuccess ? Icons.check_circle_outline : Icons.upload_file_outlined,
                    size: 64,
                    color: _uploadSuccess ? AppTheme.success : AppTheme.primary,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Sube tu PDF de laboratorio',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'La IA extraerá automáticamente todos los analitos',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppTheme.textSecondary),
                  ),
                  if (_uploadStatus != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: _uploadSuccess
                            ? AppTheme.success.withAlpha(30)
                            : AppTheme.danger.withAlpha(30),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _uploadStatus!,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: _uploadSuccess ? AppTheme.success : AppTheme.danger,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: _uploading ? null : _pickAndUpload,
                    icon: _uploading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Icon(Icons.add),
                    label: Text(_uploading ? 'Procesando...' : 'Seleccionar PDF'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            // Documents list
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Documentos subidos',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh_outlined, size: 20),
                  onPressed: _loadDocuments,
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_loadingDocs)
              const Center(child: CircularProgressIndicator(color: AppTheme.primary))
            else if (_documents.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No hay documentos todavía',
                    style: TextStyle(color: AppTheme.textSecondary),
                  ),
                ),
              )
            else
              ..._documents.map((doc) => _DocTile(doc: doc, onDelete: () => _delete(doc.id))),
          ],
        ),
      ),
    );
  }
}

class _DocTile extends StatelessWidget {
  final Document doc;
  final VoidCallback onDelete;
  const _DocTile({required this.doc, required this.onDelete});

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
          const Icon(Icons.description_outlined, color: AppTheme.primary, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  doc.displayName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                Text(
                  '${doc.displayDate} · ${doc.numMetrics} métricas',
                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, color: AppTheme.danger, size: 20),
            onPressed: onDelete,
          ),
        ],
      ),
    );
  }
}
