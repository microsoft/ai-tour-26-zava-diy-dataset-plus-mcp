#!/usr/bin/env python3

import json
import os
from typing import Dict, List, Any
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from markdown_pdf import MarkdownPdf, Section
import tempfile
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
import logging
import click

load_dotenv()

# Configure Rich logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

class ZavaProductPageGenerator:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=os.getenv("GITHUB_TOKEN")
        )
        self.model = "gpt-4.1"
        self.console = console
        
        logger.info("Zava Product Page Generator initialized")
        
    def load_product_data(self, json_file: str) -> Dict:
        """Load product data from JSON file"""
        logger.info(f"Loading product data from {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info("Successfully loaded product data")
        return data
    
    def extract_products(self, data: Dict) -> List[Dict]:
        """Extract individual products from the nested JSON structure"""
        logger.info("Extracting products from JSON data...")
        products = []
        
        for main_category, category_data in data.get("main_categories", {}).items():
            for subcategory, items in category_data.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "name" in item:
                            product = item.copy()
                            product["main_category"] = main_category
                            product["subcategory"] = subcategory.replace("_", " ").title()
                            products.append(product)
        
        logger.info(f"Extracted {len(products)} products")
        return products
    
    async def generate_product_content(self, product: Dict) -> Dict[str, Any]:
        """Generate both product description and features in a single API call"""
        prompt = f"""
        Create compelling product content for a DIY/home improvement store called Zava.
        
        Product: {product.get('name', 'Unknown Product')}
        Category: {product.get('main_category', '')} - {product.get('subcategory', '')}
        Base Price: ${product.get('base_price', 'N/A')}
        SKU: {product.get('sku', 'N/A')}
        
        Please provide a JSON response with the following structure:
        {{
            "description": "A compelling 150-200 word product description that includes key features, specifications, use cases, and quality assurance. Professional but approachable tone.",
            "features": [
                "Feature 1 - Technical specification or quality feature",
                "Feature 2 - Practical benefit or professional application",
                "Feature 3 - Technical specification or quality feature",
                "Feature 4 - Practical benefit or professional application",
                "Feature 5 - Technical specification or quality feature",
                "Feature 6 - Practical benefit or professional application"
            ]
        }}
        
        Focus on:
        - Technical specifications and quality features
        - Practical benefits and professional applications
        - Brand positioning as a premium DIY store
        - Professional quality assurance
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            import json
            content = json.loads(response.choices[0].message.content.strip())
            return {
                "description": content.get("description", f"Premium quality {product.get('name', 'product')} perfect for your DIY projects."),
                "features": content.get("features", [
                    "Professional-grade construction",
                    "Durable materials for long-lasting use",
                    "Ergonomic design for comfort",
                    "Suitable for professional and DIY use",
                    "Backed by Zava quality guarantee"
                ])
            }
        except Exception as e:
            logger.error(f"Error generating content for {product.get('name', 'Unknown')}: {e}")
            return {
                "description": f"Premium quality {product.get('name', 'product')} perfect for your DIY projects. Professional-grade construction ensures reliable performance for both amateur and professional use.",
                "features": [
                    "Professional-grade construction",
                    "Durable materials for long-lasting use",
                    "Ergonomic design for comfort",
                    "Suitable for professional and DIY use",
                    "Backed by Zava quality guarantee"
                ]
            }
    
    def create_product_markdown(self, product: Dict, description: str, features: List[str]) -> str:
        """Generate markdown content for the product page"""
        # Find product image
        image_path = self.find_product_image(product)
        image_markdown = f"![{product.get('name', 'Product')}]({image_path})" if image_path and os.path.exists(image_path) else "*[Product Image]*"
        
        markdown_content = f"""
# ZAVA
## DIY & Home Improvement

---

# {product.get('name', 'Product Name')} - ${product.get('base_price', '0.00')}

**Category:** {product.get('main_category', '')} > {product.get('subcategory', '')}
**SKU:** {product.get('sku', 'N/A')}

## Product Image

{image_markdown}

## Product Description

{description}

## Key Features

{chr(10).join([f"• {feature}" for feature in features])}

## Specifications

| Specification | Value |
|--------------|-------|
| Product Name | {product.get('name', 'N/A')} |
| SKU | {product.get('sku', 'N/A')} |
| Category | {product.get('main_category', '')} - {product.get('subcategory', '')} |
| Base Price | ${product.get('base_price', '0.00')} |
| Brand | Zava |
| Warranty | Standard Manufacturer Warranty |

---

**ZAVA - Your Trusted Partner for DIY & Home Improvement**

*Quality Products • Expert Advice • Competitive Prices*
"""
        return markdown_content
    
    def create_product_pdf(self, product: Dict, description: str, features: List[str], output_dir: str):
        """Create PDF product page from markdown"""
        # Clean filename with SKU prefix
        sku = product.get('sku', 'NO_SKU')
        safe_name = "".join(c for c in product.get('name', 'product') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{sku}_{safe_name.replace(' ', '_')}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        # Generate markdown content
        markdown_content = self.create_product_markdown(product, description, features)
        
        try:
            # Create PDF converter
            pdf = MarkdownPdf(toc_level=2)
            
            # Add CSS styling
            custom_css = """
            body { 
                font-family: Arial, sans-serif; 
                line-height: 1.6;
                color: #333;
            }
            h1 { 
                color: #2C5530; 
                border-bottom: 2px solid #2C5530; 
                padding-bottom: 10px;
            }
            h2 { 
                color: #264653; 
                margin-top: 30px;
            }
            table { 
                border-collapse: collapse; 
                width: 100%; 
                margin: 20px 0;
            }
            th, td { 
                border: 1px solid #ddd; 
                padding: 12px; 
                text-align: left;
            }
            th { 
                background-color: #F1FAEE; 
                color: #264653; 
                font-weight: bold;
            }
            tr:nth-child(even) { 
                background-color: #f9f9f9;
            }
            hr { 
                border: 1px solid #2C5530; 
                margin: 30px 0;
            }
            em { 
                color: #666;
            }
            """
            
            # Create section from markdown content
            section = Section(markdown_content, toc=False, paper_size='A4')
            pdf.add_section(section, user_css=custom_css)
            
            # Save PDF
            pdf.save(filepath)
            
            logger.info(f"Generated PDF: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating PDF for {product.get('name', 'Unknown')}: {e}")
            # No cleanup needed for markdown-pdf
            return None
    
    def find_product_image(self, product: Dict) -> str:
        """Find product image file"""
        # Create a potential image filename based on product details
        name = product.get('name', '').lower()
        category = product.get('main_category', '').lower().replace(' ', '_').replace('&', '')
        subcategory = product.get('subcategory', '').lower().replace(' ', '_')
        
        # Look for images in the images directory
        images_dir = "images"
        if not os.path.exists(images_dir):
            return None
        
        # Try different naming patterns
        potential_names = [
            f"{category}_{subcategory}_{name.replace(' ', '_')}",
            f"{category}_{name.replace(' ', '_')}",
            name.replace(' ', '_')
        ]
        
        for base_name in potential_names:
            for ext in ['.png', '.jpg', '.jpeg']:
                for filename in os.listdir(images_dir):
                    if base_name in filename.lower() and filename.lower().endswith(ext):
                        return os.path.join(images_dir, filename)
        
        return None
    
    async def generate_all_product_pages(self, json_file: str, output_dir: str = "product_pages", max_products: int = None):
        """Generate PDF pages for all products"""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
        
        # Load and extract products
        data = self.load_product_data(json_file)
        products = self.extract_products(data)
        
        if max_products:
            products = products[:max_products]
            logger.info(f"Limited to first {max_products} products")
        
        # Show summary panel
        summary_panel = Panel(
            f"Processing [bold green]{len(products)}[/bold green] products\n"
            f"Output directory: [blue]{output_dir}[/blue]\n"
            f"Model: [cyan]{self.model}[/cyan]",
            title="[bold]Product Page Generation[/bold]",
            border_style="green"
        )
        console.print(summary_panel)
        
        # Process products with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing products...", total=len(products))
            
            for i, product in enumerate(products, 1):
                product_name = product.get('name', 'Unknown')
                progress.update(task, description=f"Processing: {product_name[:30]}...")
                
                try:
                    # Generate content using single API call
                    logger.info(f"Generating content for {product_name}")
                    content = await self.generate_product_content(product)
                    
                    # Create PDF
                    self.create_product_pdf(product, content["description"], content["features"], output_dir)
                    
                    # Small delay to be respectful to the API
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing product {product_name}: {e}")
                    continue
                finally:
                    progress.update(task, advance=1)
        
        # Show completion message
        completion_panel = Panel(
            f"[bold green]✓ Successfully generated {len(products)} product pages[/bold green]\n"
            f"Files saved to: [blue]{output_dir}[/blue]",
            title="[bold green]Generation Complete![/bold green]",
            border_style="green"
        )
        console.print(completion_panel)

@click.command()
@click.option('--input-file', '-i', default="data/database/product_data.json", 
              help='Path to the JSON file containing product data')
@click.option('--output-dir', '-o', default="product_pages", 
              help='Directory to save generated PDF files')
@click.option('--limit', '-l', type=int, default=None, 
              help='Maximum number of products to process (default: all)')
@click.option('--model', '-m', default="gpt-4.1", 
              help='OpenAI model to use for content generation')
@click.version_option(version='1.0.0', prog_name='Zava Product Page Generator')
def main(input_file: str, output_dir: str, limit: int, model: str):
    """
    Generate professional product pages for Zava DIY store.
    
    This tool uses GPT-4o to generate compelling product descriptions and features,
    then creates branded PDF product pages with rich formatting.
    """
    # Display startup banner
    startup_banner = Panel(
        Text("ZAVA Product Page Generator", style="bold magenta", justify="center") + "\n" +
        Text(f"Powered by {model} and Rich logging", style="dim", justify="center"),
        border_style="magenta",
        padding=(1, 2)
    )
    console.print(startup_banner)
    
    # Check if we have the GitHub token
    if not os.getenv("GITHUB_TOKEN"):
        logger.error("GITHUB_TOKEN not found in environment variables")
        logger.error("Please ensure your .env file contains the GitHub token")
        raise click.ClickException("Missing required environment variable: GITHUB_TOKEN")
    
    # Validate input file
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        raise click.ClickException(f"Input file not found: {input_file}")
    
    # Create generator with custom model
    generator = ZavaProductPageGenerator()
    generator.model = model
    
    # Log configuration
    logger.info("Configuration:")
    logger.info(f"  Input file: {input_file}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Product limit: {limit or 'unlimited'}")
    logger.info(f"  Model: {model}")
    
    # Run the generator
    asyncio.run(generator.generate_all_product_pages(input_file, output_dir, limit))

if __name__ == "__main__":
    main()