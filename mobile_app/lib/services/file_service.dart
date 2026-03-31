import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';

class FileService {
  Future<String?> pickFile({List<String>? allowedExtensions}) async {
    final result = await FilePicker.platform.pickFiles(
      type: allowedExtensions != null ? FileType.custom : FileType.any,
      allowedExtensions: allowedExtensions,
    );
    return result?.files.single.path;
  }

  Future<List<FileSystemEntity>> listDirectory(String path) async {
    final dir = Directory(path);
    if (!dir.existsSync()) return [];
    return dir.listSync().toList();
  }

  Future<String> getAppDocumentsPath() async {
    final dir = await getApplicationDocumentsDirectory();
    return dir.path;
  }

  Future<String> getTempPath() async {
    final dir = await getTemporaryDirectory();
    return dir.path;
  }

  Future<bool> fileExists(String path) async {
    return File(path).exists();
  }

  Future<void> deleteFile(String path) async {
    final file = File(path);
    if (await file.exists()) {
      await file.delete();
    }
  }
}
