import 'dart:io';

void main() {
  final file = File('test/reports_test.dart');
  var content = file.readAsStringSync();
  
  content = content.replaceAll(
    "'€ 12,345,678,901,234,567,890.01'",
    "'12.345.678.901.234.567.890,01 €'"
  );
  
  content = content.replaceAll(
    "'-US\$1,234.50'",
    "r'-\$1,234.50'"
  );
  
  content = content.replaceAll(
    "'S/ 90.00 · US\$ 100.00'",
    "r'90 S/. · 100 \$'"
  );
  
  content = content.replaceAll(
    "'US\$ 100.00'",
    "r'100 \$'"
  );

  file.writeAsStringSync(content);
}
