#!/usr/bin/env python3

import json
import os
import sys
from typing import Dict, List, Any
from pathlib import Path
import asyncio
from openai import AsyncOpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from io import BytesIO
import base64
from PIL import Image as PILImage
import requests
from dotenv import load_dotenv
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
        
        # Zava brand colors
        self.brand_colors = {
            'primary': HexColor("#2C5530"),    # Forest Green
            'secondary': HexColor("#F4A261"),   # Warm Orange
            'accent': HexColor("#E76F51"),      # Coral Red
            'neutral': HexColor("#264653"),     # Dark Green
            'light': HexColor("#F1FAEE")        # Off White
        }
        
        logger.info("Zava Product Page Generator initialized")
        
    def load_product_data(self, json_file: str) -> Dict:
        """Load product data from JSON file"""
        logger.info(f"Loading product data from [bold blue]{json_file}[/bold blue]")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded product data")
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
        
        logger.info(f"Extracted [bold green]{len(products)}[/bold green] products")
        return products
    
    async def generate_product_description(self, product: Dict) -> str:
        """Generate detailed product description using GPT-4o"""
        prompt = f"""
        Create a compelling product description for a DIY/home improvement store called Zava. 
        
        Product: {product.get('name', 'Unknown Product')}
        Category: {product.get('main_category', '')} - {product.get('subcategory', '')}
        Base Price: ${product.get('base_price', 'N/A')}
        SKU: {product.get('sku', 'N/A')}
        
        Write a professional product description that includes:
        1. Key features and benefits
        2. Specifications and technical details
        3. Ideal use cases
        4. Professional quality assurance
        5. Brand positioning as a premium DIY store
        
        Keep it between 150-200 words, professional but approachable.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating description for [red]{product.get('name', 'Unknown')}[/red]: {e}")
            return f"Premium quality {product.get('name', 'product')} perfect for your DIY projects. Professional-grade construction ensures reliable performance for both amateur and professional use."
    
    async def generate_features_list(self, product: Dict) -> List[str]:
        """Generate key features list using GPT-4o"""
        prompt = f"""
        Create 5-7 key bullet points for this product:
        
        Product: {product.get('name', 'Unknown Product')}
        Category: {product.get('main_category', '')} - {product.get('subcategory', '')}
        
        Focus on:
        - Technical specifications
        - Quality features
        - Practical benefits
        - Professional applications
        
        Return only the bullet points, one per line, without bullet symbols.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.6
            )
            features = response.choices[0].message.content.strip().split('\n')
            return [f.strip() for f in features if f.strip()]
        except Exception as e:
            logger.error(f"Error generating features for [red]{product.get('name', 'Unknown')}[/red]: {e}")
            return [
                "Professional-grade construction",
                "Durable materials for long-lasting use",
                "Ergonomic design for comfort",
                "Suitable for professional and DIY use",
                "Backed by Zava quality guarantee"
            ]
    
    def create_product_pdf(self, product: Dict, description: str, features: List[str], output_dir: str):
        """Create PDF product page"""
        # Clean filename with SKU prefix
        sku = product.get('sku', 'NO_SKU')
        safe_name = "".join(c for c in product.get('name', 'product') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{sku}_{safe_name.replace(' ', '_')}.pdf"
        filepath = os.path.join(output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Create styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=self.brand_colors['primary'],
            alignment=TA_LEFT
        )
        
        brand_style = ParagraphStyle(
            'Brand',
            parent=styles['Normal'],
            fontSize=36,
            textColor=self.brand_colors['primary'],
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=self.brand_colors['neutral'],
            spaceAfter=10
        )
        
        price_style = ParagraphStyle(
            'Price',
            parent=styles['Normal'],
            fontSize=20,
            textColor=self.brand_colors['accent'],
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        )
        
        # Build PDF content
        story = []
        
        # Header with brand
        story.append(Paragraph("ZAVA", brand_style))
        story.append(Paragraph("DIY & Home Improvement", 
                              ParagraphStyle('Tagline', parent=styles['Normal'], 
                                           fontSize=12, alignment=TA_CENTER,
                                           textColor=self.brand_colors['neutral'])))
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=2, color=self.brand_colors['primary']))
        story.append(Spacer(1, 20))
        
        # Product title and price
        header_data = [
            [Paragraph(product.get('name', 'Product Name'), title_style),
             Paragraph(f"${product.get('base_price', '0.00')}", price_style)]
        ]
        
        header_table = Table(header_data, colWidths=[4*inch, 2*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        
        # Category and SKU
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>Category:</b> {product.get('main_category', '')} > {product.get('subcategory', '')}", 
                              styles['Normal']))
        story.append(Paragraph(f"<b>SKU:</b> {product.get('sku', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Product image placeholder
        story.append(Paragraph("Product Image", subtitle_style))
        
        # Try to find and include product image
        image_path = self.find_product_image(product)
        if image_path and os.path.exists(image_path):
            try:
                img = Image(image_path, width=3*inch, height=3*inch)
                story.append(img)
            except Exception as e:
                logger.warning(f"Could not load image [yellow]{image_path}[/yellow]: {e}")
                story.append(Paragraph("[Product Image]", 
                                     ParagraphStyle('ImagePlaceholder', parent=styles['Normal'],
                                                  alignment=TA_CENTER, fontSize=12,
                                                  textColor=colors.grey)))
        else:
            story.append(Paragraph("[Product Image]", 
                                 ParagraphStyle('ImagePlaceholder', parent=styles['Normal'],
                                              alignment=TA_CENTER, fontSize=12,
                                              textColor=colors.grey)))
        
        story.append(Spacer(1, 20))
        
        # Product description
        story.append(Paragraph("Product Description", subtitle_style))
        story.append(Paragraph(description, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Key features
        story.append(Paragraph("Key Features", subtitle_style))
        for feature in features:
            story.append(Paragraph(f"• {feature}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Specifications table
        story.append(Paragraph("Specifications", subtitle_style))
        spec_data = [
            ['Product Name', product.get('name', 'N/A')],
            ['SKU', product.get('sku', 'N/A')],
            ['Category', f"{product.get('main_category', '')} - {product.get('subcategory', '')}"],
            ['Base Price', f"${product.get('base_price', '0.00')}"],
            ['Brand', 'Zava'],
            ['Warranty', 'Standard Manufacturer Warranty']
        ]
        
        spec_table = Table(spec_data, colWidths=[2*inch, 3*inch])
        spec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.brand_colors['light']),
            ('TEXTCOLOR', (0, 0), (0, -1), self.brand_colors['neutral']),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, self.brand_colors['light']]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(spec_table)
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(HRFlowable(width="100%", thickness=1, color=self.brand_colors['primary']))
        story.append(Spacer(1, 10))
        story.append(Paragraph("ZAVA - Your Trusted Partner for DIY & Home Improvement", 
                              ParagraphStyle('Footer', parent=styles['Normal'], 
                                           fontSize=10, alignment=TA_CENTER,
                                           textColor=self.brand_colors['neutral'])))
        story.append(Paragraph("Quality Products • Expert Advice • Competitive Prices", 
                              ParagraphStyle('Footer2', parent=styles['Normal'], 
                                           fontSize=8, alignment=TA_CENTER,
                                           textColor=self.brand_colors['neutral'])))
        
        # Build PDF
        doc.build(story)
        logger.info(f"Generated PDF: [bold green]{filepath}[/bold green]")
        return filepath
    
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
        logger.info(f"Created output directory: [bold blue]{output_dir}[/bold blue]")
        
        # Load and extract products
        data = self.load_product_data(json_file)
        products = self.extract_products(data)
        
        if max_products:
            products = products[:max_products]
            logger.info(f"Limited to first [bold yellow]{max_products}[/bold yellow] products")
        
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
                    # Generate content using GPT-4o
                    logger.info(f"Generating content for [bold]{product_name}[/bold]")
                    description = await self.generate_product_description(product)
                    features = await self.generate_features_list(product)
                    
                    # Create PDF
                    self.create_product_pdf(product, description, features, output_dir)
                    
                    # Small delay to be respectful to the API
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing product [red]{product_name}[/red]: {e}")
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
        logger.error("[red]GITHUB_TOKEN not found in environment variables[/red]")
        logger.error("Please ensure your .env file contains the GitHub token")
        raise click.ClickException("Missing required environment variable: GITHUB_TOKEN")
    
    # Validate input file
    if not os.path.exists(input_file):
        logger.error(f"[red]Input file not found: {input_file}[/red]")
        raise click.ClickException(f"Input file not found: {input_file}")
    
    # Create generator with custom model
    generator = ZavaProductPageGenerator()
    generator.model = model
    
    # Log configuration
    logger.info(f"Configuration:")
    logger.info(f"  Input file: [blue]{input_file}[/blue]")
    logger.info(f"  Output directory: [blue]{output_dir}[/blue]")
    logger.info(f"  Product limit: [yellow]{limit or 'unlimited'}[/yellow]")
    logger.info(f"  Model: [cyan]{model}[/cyan]")
    
    # Run the generator
    asyncio.run(generator.generate_all_product_pages(input_file, output_dir, limit))

if __name__ == "__main__":
    main()