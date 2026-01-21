import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';

/// Library Screen - Shows all saved reels
class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  List<Map<String, dynamic>> _reels = [];
  List<Map<String, dynamic>> _categories = [];
  bool _isLoading = true;
  String? _error;
  String? _selectedCategory;
  String? _selectedTag;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Load reels and categories in parallel
      final reelsResponse = await ApiService.getReels(
        category: _selectedCategory,
        tag: _selectedTag,
        search: _searchController.text.isEmpty ? null : _searchController.text,
      );
      final categoriesResponse = await ApiService.getCategories();

      setState(() {
        _reels = List<Map<String, dynamic>>.from(reelsResponse['reels'] ?? []);
        _categories = categoriesResponse;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _deleteReel(String id) async {
    try {
      await ApiService.deleteReel(id);
      _loadData();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Reel deleted')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete: $e')),
        );
      }
    }
  }

  void _onCategorySelected(String? category) {
    setState(() {
      _selectedCategory = category;
      _selectedTag = null;
    });
    _loadData();
  }

  void _onTagSelected(String tag) {
    setState(() {
      _selectedTag = tag;
      _selectedCategory = null;
    });
    _loadData();
  }

  void _clearFilters() {
    setState(() {
      _selectedCategory = null;
      _selectedTag = null;
      _searchController.clear();
    });
    _loadData();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Reels'),
        actions: [
          if (_selectedCategory != null || _selectedTag != null || _searchController.text.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: _clearFilters,
              tooltip: 'Clear filters',
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search reels...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _loadData();
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
              ),
              onSubmitted: (_) => _loadData(),
            ),
          ),

          // Category chips
          if (_categories.isNotEmpty)
            SizedBox(
              height: 50,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: const Text('All'),
                      selected: _selectedCategory == null && _selectedTag == null,
                      onSelected: (_) => _clearFilters(),
                    ),
                  ),
                  ..._categories.map((cat) => Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text('${cat['name']} (${cat['count']})'),
                      selected: _selectedCategory == cat['name'],
                      onSelected: (_) => _onCategorySelected(cat['name']),
                    ),
                  )),
                ],
              ),
            ),

          const SizedBox(height: 8),

          // Active filter indicator
          if (_selectedTag != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Chip(
                label: Text('Tag: $_selectedTag'),
                onDeleted: _clearFilters,
                deleteIcon: const Icon(Icons.close, size: 18),
              ),
            ),

          // Reels list
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red[300]),
            const SizedBox(height: 16),
            Text('Error: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_reels.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.movie_filter_outlined, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              _selectedCategory != null || _selectedTag != null
                  ? 'No reels found with this filter'
                  : 'No reels saved yet',
              style: TextStyle(color: Colors.grey[400]),
            ),
            const SizedBox(height: 8),
            Text(
              'Share a reel from Instagram to get started!',
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _reels.length,
        itemBuilder: (context, index) {
          final reel = _reels[index];
          return _ReelCard(
            reel: reel,
            onTap: () => context.push('/result', extra: reel),
            onDelete: () => _showDeleteDialog(reel),
            onTagTap: _onTagSelected,
          );
        },
      ),
    );
  }

  void _showDeleteDialog(Map<String, dynamic> reel) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Reel?'),
        content: Text('Delete "${reel['summary']?.substring(0, 50) ?? 'this reel'}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _deleteReel(reel['id']);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

class _ReelCard extends StatelessWidget {
  final Map<String, dynamic> reel;
  final VoidCallback onTap;
  final VoidCallback onDelete;
  final Function(String) onTagTap;

  const _ReelCard({
    required this.reel,
    required this.onTap,
    required this.onDelete,
    required this.onTagTap,
  });

  @override
  Widget build(BuildContext context) {
    final tags = List<String>.from(reel['tags'] ?? []);
    final category = reel['category'] as String?;
    final summary = reel['summary'] as String? ?? 'No summary';
    final createdAt = reel['created_at'] as String?;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row with category and delete button
              Row(
                children: [
                  if (category != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primaryContainer,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        category,
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context).colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  const Spacer(),
                  if (createdAt != null)
                    Text(
                      _formatDate(createdAt),
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey[500],
                      ),
                    ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline, size: 20),
                    onPressed: onDelete,
                    color: Colors.grey[500],
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Summary
              Text(
                summary,
                style: Theme.of(context).textTheme.bodyMedium,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 12),

              // Tags
              if (tags.isNotEmpty)
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: tags.take(4).map((tag) => InkWell(
                    onTap: () => onTagTap(tag),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        tag,
                        style: const TextStyle(fontSize: 11),
                      ),
                    ),
                  )).toList(),
                ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDate(String isoDate) {
    try {
      final date = DateTime.parse(isoDate);
      final now = DateTime.now();
      final diff = now.difference(date);

      if (diff.inDays == 0) {
        return 'Today';
      } else if (diff.inDays == 1) {
        return 'Yesterday';
      } else if (diff.inDays < 7) {
        return '${diff.inDays} days ago';
      } else {
        return '${date.day}/${date.month}/${date.year}';
      }
    } catch (e) {
      return '';
    }
  }
}
