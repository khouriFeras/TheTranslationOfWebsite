# Contributing to Shopify Product Translation Tool

Thank you for your interest in contributing to this project! This document provides guidelines and information for contributors.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/shopify-product-translation-tool.git
   cd shopify-product-translation-tool
   ```
3. **Set up the development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## 🔧 Development Setup

### Prerequisites
- Python 3.9 or higher
- Git
- A Shopify store for testing (or use Shopify's development store)

### Environment Variables
Create a `.env` file for testing:
```env
SHOPIFY_STORE_DOMAIN=your-test-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=your_test_token
SHOPIFY_API_VERSION=2025-07
TARGET_LANGUAGE=en
ORIGINAL_LANGUAGE=ar
OUTPUT_DIR=exports
```

## 📝 How to Contribute

### 1. Choose an Issue
- Look for issues labeled `good first issue` for beginners
- Check the issue tracker for bugs or feature requests
- Comment on the issue to let others know you're working on it

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Make Changes
- Write clean, readable code
- Follow the existing code style
- Add comments for complex logic
- Update documentation if needed

### 4. Test Your Changes
```bash
# Test the main functionality
python scripts/fetch_products.py

# Test specific scripts
python scripts/fetch_single_product.py handle test-product
```

### 5. Commit Changes
```bash
git add .
git commit -m "Add: brief description of changes"
```

### 6. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## 📋 Code Style Guidelines

### Python Code
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions small and focused

### Example:
```python
def fetch_product_by_handle(handle: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single product by its handle.
    
    Args:
        handle: The product handle to search for
        
    Returns:
        Product data dictionary or None if not found
    """
    # Implementation here
    pass
```

### Commit Messages
Use clear, descriptive commit messages:
- `Add: new feature description`
- `Fix: bug description`
- `Update: what was updated`
- `Remove: what was removed`
- `Docs: documentation changes`

## 🧪 Testing

### Manual Testing
1. Test with a small Shopify store
2. Verify all export formats work correctly
3. Test error handling with invalid credentials
4. Test translation upload functionality

### Test Scenarios
- [ ] Export all products
- [ ] Export single product by handle
- [ ] Export single product by ID
- [ ] Export single product by tag
- [ ] Convert JSON to CSV
- [ ] Convert JSON to XLSX
- [ ] Upload translations
- [ ] Error handling for invalid credentials
- [ ] Error handling for network issues

## 🐛 Reporting Bugs

When reporting bugs, please include:
1. **Environment details**: Python version, OS, etc.
2. **Steps to reproduce**: Clear, numbered steps
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Error messages**: Full error traceback if any
6. **Screenshots**: If applicable

## 💡 Suggesting Features

When suggesting features:
1. **Check existing issues** first
2. **Describe the problem** you're trying to solve
3. **Explain your proposed solution**
4. **Provide use cases** and examples
5. **Consider implementation complexity**

## 📚 Documentation

- Update README.md for user-facing changes
- Update CONTRIBUTING.md for process changes
- Add docstrings to new functions
- Update inline comments for complex logic

## 🔍 Code Review Process

1. **Automated checks** must pass
2. **At least one reviewer** must approve
3. **All conversations** must be resolved
4. **No merge conflicts** should exist

### Review Checklist
- [ ] Code follows style guidelines
- [ ] Functions have proper docstrings
- [ ] Error handling is appropriate
- [ ] No hardcoded credentials
- [ ] Documentation is updated
- [ ] Tests pass (if applicable)

## 🎯 Areas for Contribution

### High Priority
- Error handling improvements
- Performance optimizations
- Additional export formats
- Better logging and debugging

### Medium Priority
- GUI interface
- Batch processing improvements
- Additional translation services
- Configuration validation

### Low Priority
- Additional output formats
- Advanced filtering options
- Integration with other platforms

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Email**: [Your email here]

## 🙏 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to make this tool better for the Shopify community!
