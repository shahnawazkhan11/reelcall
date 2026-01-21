import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

/// Home Screen - Main entry point of the app
/// Handles receiving shared URLs from other apps (Instagram)
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late StreamSubscription _intentSub;
  final TextEditingController _urlController = TextEditingController();
  String? _sharedUrl;

  @override
  void initState() {
    super.initState();
    _initShareIntent();
  }

  void _initShareIntent() {
    // Listen for shared content while app is in memory
    _intentSub = ReceiveSharingIntent.instance.getMediaStream().listen(
      (List<SharedMediaFile> value) {
        if (value.isNotEmpty) {
          _handleSharedContent(value.first.path);
        }
      },
      onError: (err) {
        debugPrint("Error receiving shared content: $err");
      },
    );

    // Get shared content when app is opened from share
    ReceiveSharingIntent.instance.getInitialMedia().then((List<SharedMediaFile> value) {
      if (value.isNotEmpty) {
        _handleSharedContent(value.first.path);
      }
      // Clear the intent after handling
      ReceiveSharingIntent.instance.reset();
    });
  }

  void _handleSharedContent(String content) {
    debugPrint("Received shared content: $content");
    
    // Check if it's an Instagram URL
    if (content.contains('instagram.com')) {
      setState(() {
        _sharedUrl = content;
        _urlController.text = content;
      });
      
      // Auto-navigate to processing screen
      _processUrl(content);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please share a valid Instagram reel URL'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _processUrl(String url) {
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a URL'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    context.push('/processing', extra: url);
  }

  @override
  void dispose() {
    _intentSub.cancel();
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ReelCall'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Logo/Icon
            Icon(
              Icons.movie_filter,
              size: 100,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 24),
            
            // Title
            Text(
              'Your Second Brain for Reels',
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            
            // Subtitle
            Text(
              'Share a reel from Instagram to extract, transcribe, and tag it automatically',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 48),
            
            // Manual URL input
            TextField(
              controller: _urlController,
              decoration: InputDecoration(
                hintText: 'Paste Instagram reel URL',
                prefixIcon: const Icon(Icons.link),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            
            // Process button
            ElevatedButton.icon(
              onPressed: () => _processUrl(_urlController.text),
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Process Reel'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 32),
            
            // Instructions
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'How to use:',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 8),
                  const Text('1. Open Instagram and find a reel'),
                  const Text('2. Tap Share → More → ReelCall'),
                  const Text('3. The app will process it automatically!'),
                ],
              ),
            ),
            
            if (_sharedUrl != null) ...[
              const SizedBox(height: 16),
              Text(
                'Last shared: $_sharedUrl',
                style: const TextStyle(color: Colors.grey, fontSize: 12),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
