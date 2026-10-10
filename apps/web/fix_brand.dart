import 'dart:io';

void main() {
  final file = File('test/brand_and_preferences_test.dart');
  var content = file.readAsStringSync();
  
  content = content.replaceAll(
    "pastel(const Color(0xFF5F85C2), brightness, .92)",
    "const Color(0xFF121212)"
  );
  
  content = content.replaceAll(
    "pastel(const Color(0xFF5F85C2), brightness, .8)",
    "const Color(0xFF1E1E1E)"
  );
  
  file.writeAsStringSync(content);
}
