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

load_dotenv()

class ZavaProductPageGenerator:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=os.getenv("GITHUB_TOKEN")
        )
        self.model = "gpt-4o"
        
        # Zava brand colors
        self.brand_colors = {
            'primary': HexColor("#2C5530"),    # Forest Green
            'secondary': HexColor("#F4A261"),   # Warm Orange
            'accent': HexColor("#E76F51"),      # Coral Red
            'neutral': HexColor("#264653"),     # Dark Green
            'light': HexColor("#F1FAEE")        # Off White
        }
        
    def load_product_data(self, json_file: str) -> Dict:
        """Load product data from JSON file"""
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_products(self, data: Dict) -> List[Dict]:
        """Extract individual products from the nested JSON structure"""
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
            print(f"Error generating description for {product.get('name', 'Unknown')}: {e}")
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
            print(f"Error generating features for {product.get('name', 'Unknown')}: {e}")
            return [
                "Professional-grade construction",
                "Durable materials for long-lasting use",
                "Ergonomic design for comfort",
                "Suitable for professional and DIY use",
                "Backed by Zava quality guarantee"
            ]
    
    def create_product_pdf(self, product: Dict, description: str, features: List[str], output_dir: str):
        """Create PDF product page"""
        # Clean filename
        safe_name = "".join(c for c in product.get('name', 'product') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_name.replace(' ', '_')}.pdf"
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
                print(f"Could not load image {image_path}: {e}")
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
        print(f"Generated PDF: {filepath}")
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
        
        # Load and extract products
        print("Loading product data...")
        data = self.load_product_data(json_file)
        products = self.extract_products(data)
        
        if max_products:
            products = products[:max_products]
        
        print(f"Found {len(products)} products to process")
        
        # Process products
        for i, product in enumerate(products, 1):
            print(f"Processing {i}/{len(products)}: {product.get('name', 'Unknown')}")
            
            try:
                # Generate content using GPT-4o
                description = await self.generate_product_description(product)
                features = await self.generate_features_list(product)
                
                # Create PDF
                self.create_product_pdf(product, description, features, output_dir)
                
                # Small delay to be respectful to the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing product {product.get('name', 'Unknown')}: {e}")
                continue
        
        print(f"\nCompleted! Generated {len(products)} product pages in '{output_dir}' directory")

async def main():
    generator = ZavaProductPageGenerator()
    
    # Check if we have the GitHub token
    if not os.getenv("GITHUB_TOKEN"):
        print("Error: GITHUB_TOKEN not found in environment variables")
        print("Please ensure your .env file contains the GitHub token")
        sys.exit(1)
    
    json_file = "data/database/product_data.json"
    
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found")
        sys.exit(1)
    
    # For demo purposes, limit to 5 products
    max_products = 5
    print(f"Generating product pages for first {max_products} products...")
    
    await generator.generate_all_product_pages(json_file, max_products=max_products)

if __name__ == "__main__":
    asyncio.run(main())