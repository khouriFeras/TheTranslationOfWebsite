# Shopify Product Translation Tool

A comprehensive Python utility for exporting Shopify products and preparing them for translation. This tool fetches product data from Shopify Admin GraphQL API, adds language markers, and exports results in multiple formats (JSON, CSV, XLSX) for easy translation workflow.

## 🚀 Features

- **Product Export**: Fetch all products or specific products by handle, ID, or tag
- **Multi-format Export**: Export to JSON, CSV, and XLSX formats
- **Translation Ready**: Add target language markers for translation workflow
- **OpenAI Integration**: Optional AI-powered translation capabilities
- **Collection Support**: Export products from specific collections
- **Translation Upload**: Upload translated content back to Shopify

## 📋 Prerequisites

- Python 3.9 or higher
- Shopify Admin API access token with appropriate scopes:
  - `read_products` - to fetch product data
  - `write_translations` - to upload translations

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/shopify-product-translation-tool.git
   cd shopify-product-translation-tool
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your Shopify credentials
   ```

## ⚙️ Configuration

Create a `.env` file in the project root with your Shopify credentials:

```env
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_XXXXXXXXXXXXXXXX
SHOPIFY_API_VERSION=2025-07
TARGET_LANGUAGE=en
ORIGINAL_LANGUAGE=ar
OUTPUT_DIR=exports
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SHOPIFY_STORE_DOMAIN` | Your Shopify store domain (without https://) | `jafarshop.myshopify.com` |
| `SHOPIFY_ADMIN_ACCESS_TOKEN` | Admin API access token | `shpat_XXXXXXXXXXXXXXXX` |
| `SHOPIFY_API_VERSION` | Shopify API version | `2025-07` |
| `TARGET_LANGUAGE` | Target language for translations | `en` |
| `ORIGINAL_LANGUAGE` | Original language of products | `ar` |
| `OUTPUT_DIR` | Output directory for exports | `exports` |

## 🚀 Usage

### 1. Export All Products
```bash
python scripts/fetch_products.py all
```

### 2. Export Single Product
```bash
# By handle
python scripts/fetch_products.py single --handle your-product-handle

# By ID
python scripts/fetch_products.py single --id 123456789
```

### 3. Export Products by Tag
```bash
python scripts/fetch_products.py tag --name "tagname"
```

### 4. Export Collection Products
```bash
# By collection handle
python scripts/fetch_products.py collection --handle my-collection

# By collection title
python scripts/fetch_products.py collection --title "My Collection"

# By collection ID
python scripts/fetch_products.py collection --id gid://shopify/Collection/123456789
```

### 5. Convert Formats
```bash
# JSON to XLSX
python scripts/json_to_xlsx.py exports/products_with_lang.json exports/products_with_lang.xlsx
```

### 6. Upload Translations
```bash
# From JSON
python scripts/register_translations.py exports/products_with_lang.json

# From CSV
python scripts/register_translations.py exports/products_with_lang.csv
```

### 7. AI Translation (Optional)
```bash
# Setup OpenAI API key first
python scripts/setup_openai.py

# Translate products
python scripts/translate_openai.py exports/products_with_lang.json
```

## 📁 Output Files

The tool generates several output files in the `exports/` directory:

- `products_raw.json` - Raw product data from Shopify
- `products_with_lang.json` - Products with language markers
- `products_with_lang.csv` - CSV format for easy editing
- `products_with_lang.xlsx` - Excel format for translation teams

## 🔧 Scripts Overview

| Script | Purpose |
|--------|---------|
| `fetch_products.py` | Unified script for all product fetching methods |
| `json_to_xlsx.py` | Convert JSON to Excel format |
| `register_translations.py` | Upload translations to Shopify |
| `translate_openai.py` | AI-powered translation using OpenAI |

## 🐛 Troubleshooting

### Common Issues

**401 Unauthorized Error**
- Verify your `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_ACCESS_TOKEN`
- Ensure the token has the required scopes

**DNS Resolution Error**
- Make sure `SHOPIFY_STORE_DOMAIN` contains only the domain (e.g., `store.myshopify.com`)
- Don't include `https://` or `/admin` in the domain

**Translation Not Visible**
- Ensure the product is published
- Check that the target language is added and published in Shopify Settings → Languages

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for Shopify merchants who need efficient product translation workflows
- Uses Shopify Admin GraphQL API for optimal performance
- Integrates with OpenAI for AI-powered translations