#!/bin/bash
# Elasticsearch Cleanup Utility Script
# =====================================
# Usage examples for the Elasticsearch embeddings cleanup tool

echo "🔍 Elasticsearch Embeddings Cleanup Tool"
echo "========================================="

# Check if script exists
if [ ! -f "simple_elasticsearch_cleaner.py" ]; then
    echo "❌ Error: simple_elasticsearch_cleaner.py not found"
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage examples:"
    echo ""
    echo "1. Get cluster information:"
    echo "   python simple_elasticsearch_cleaner.py --action info"
    echo ""
    echo "2. Clear all embeddings (DESTRUCTIVE):"
    echo "   python simple_elasticsearch_cleaner.py --action clear-all --confirm"
    echo ""
    echo "3. Clear specific index:"
    echo "   python simple_elasticsearch_cleaner.py --action clear-index --index documents --confirm"
    echo ""
    echo "4. Delete specific documents:"
    echo "   python simple_elasticsearch_cleaner.py --action clear-docs --doc-ids doc1 doc2 --index documents"
    echo ""
    echo "5. Use different Elasticsearch URL:"
    echo "   python simple_elasticsearch_cleaner.py --action info --es-url http://localhost:9200"
    echo ""
}

# Parse command line arguments
case "${1:-help}" in
    "info")
        echo "📊 Getting Elasticsearch cluster information..."
        python simple_elasticsearch_cleaner.py --action info
        ;;
    "clear-all")
        echo "⚠️  WARNING: This will delete ALL embeddings!"
        echo "Type 'yes' to confirm:"
        read -r confirmation
        if [ "$confirmation" = "yes" ]; then
            python simple_elasticsearch_cleaner.py --action clear-all --confirm
        else
            echo "❌ Operation cancelled"
        fi
        ;;
    "clear-index")
        if [ -z "$2" ]; then
            echo "❌ Error: Index name required"
            echo "Usage: $0 clear-index <index_name>"
            exit 1
        fi
        echo "⚠️  WARNING: This will delete all documents from index '$2'!"
        echo "Type 'yes' to confirm:"
        read -r confirmation
        if [ "$confirmation" = "yes" ]; then
            python simple_elasticsearch_cleaner.py --action clear-index --index "$2" --confirm
        else
            echo "❌ Operation cancelled"
        fi
        ;;
    "help"|*)
        show_usage
        ;;
esac