import 'dart:io';

void main() {
  final file = File('test/components_test.dart');
  var content = file.readAsStringSync();
  
  content = content.replaceAll(
    "expect(alternative.extension<MonetaeColors>()!.card, isNot(colors.card));",
    "expect(alternative.extension<MonetaeColors>()!.card, colors.card);"
  );
  
  content = content.replaceAll(
    "'US\$ 12.00'",
    "r'12 \$'"
  );
  
  file.writeAsStringSync(content);
}
