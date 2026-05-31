import 'dart:convert';
import 'package:http/http.dart' as http;

/// API Service for communicating with the ReelCall backend
class ApiService {
  // ngrok tunnel — run: ngrok http 8000, then paste your HTTPS URL below
  static const String baseUrl = 'https://molehill-floral-lethargy.ngrok-free.dev';
  
  /// Process an Instagram reel URL
  /// Returns the processed data including transcript, summary, tags, and category
  static Future<Map<String, dynamic>> processReel(String url) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/process'),
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: jsonEncode({'url': url}),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Failed to process reel');
      }
    } catch (e) {
      if (e is http.ClientException) {
        throw Exception('Could not connect to server. Make sure the backend is running.');
      }
      rethrow;
    }
  }

  /// Get all saved reels with optional filters
  static Future<Map<String, dynamic>> getReels({
    int page = 1,
    int perPage = 20,
    String? category,
    String? tag,
    String? search,
  }) async {
    try {
      final queryParams = <String, String>{
        'page': page.toString(),
        'per_page': perPage.toString(),
      };
      if (category != null) queryParams['category'] = category;
      if (tag != null) queryParams['tag'] = tag;
      if (search != null) queryParams['search'] = search;

      final uri = Uri.parse('$baseUrl/reels').replace(queryParameters: queryParams);
      
      final response = await http.get(
        uri,
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Failed to fetch reels');
      }
    } catch (e) {
      if (e is http.ClientException) {
        throw Exception('Could not connect to server.');
      }
      rethrow;
    }
  }

  /// Get a single reel by ID
  static Future<Map<String, dynamic>> getReel(String id) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/reels/$id'),
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Reel not found');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Delete a reel by ID
  static Future<void> deleteReel(String id) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/reels/$id'),
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to delete reel');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Get all tags with counts
  static Future<List<Map<String, dynamic>>> getTags() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/tags'),
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['tags']);
      } else {
        throw Exception('Failed to fetch tags');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Get all categories with counts
  static Future<List<Map<String, dynamic>>> getCategories() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/categories'),
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(data['categories']);
      } else {
        throw Exception('Failed to fetch categories');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Health check to verify backend is running
  static Future<bool> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health'),
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Chat with your saved reels using RAG
  static Future<Map<String, dynamic>> chat(String question, {int topK = 5}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat'),
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: jsonEncode({
          'question': question,
          'top_k': topK,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['detail'] ?? 'Failed to get answer');
      }
    } catch (e) {
      if (e is http.ClientException) {
        throw Exception('Could not connect to server.');
      }
      rethrow;
    }
  }

  /// Backfill embeddings for all existing reels
  static Future<Map<String, dynamic>> backfillEmbeddings() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/reels/backfill-embeddings'),
        headers: {
          'ngrok-skip-browser-warning': 'true',
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to backfill embeddings');
      }
    } catch (e) {
      rethrow;
    }
  }
}
