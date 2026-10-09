import 'package:http/browser_client.dart';
import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

http.Client createBrowserClient() => BrowserClient()..withCredentials = true;
String readBrowserCookies() => web.document.cookie;
