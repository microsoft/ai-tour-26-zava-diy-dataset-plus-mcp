"""
Safety Data Sheets and Compliance Document Generator - GPT-4.1 Enhanced Version

Generates realistic safety documentation for hardware products using GitHub Models GPT-4.1:
- Material Safety Data Sheets (SDS/MSDS)
- Product compliance certificates
- Installation safety guidelines
- Environmental impact statements
"""

import logging
import os
import random
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import asyncpg
from dotenv import load_dotenv
from openai import AsyncOpenAI
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rich.logging import RichHandler
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text

# Load environment variables from .env file
load_dotenv()

# Setup rich console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger("safety_docs_generator")

# GitHub Models API Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
endpoint = os.getenv("OPENAI_ENDPOINT", "https://models.github.ai/inference")
model = os.getenv("OPENAI_MODEL", "openai/gpt-4.1")

client = AsyncOpenAI(
    base_url=endpoint,
    api_key=GITHUB_TOKEN,
)

SDS_TEMPLATE = """
# SAFETY DATA SHEET
## {product_name}
### Product Code: {sku}
### Revision Date: {revision_date}
### SDS Number: SDS-{sds_number}

---

## 1. IDENTIFICATION
**Product Name:** {product_name}
**Product Code:** {sku}
**Manufacturer:** Zava Hardware & Garden Supply
**Emergency Contact:** 1-800-EMERGENCY (24 hours)
**Recommended Use:** {recommended_use}
**Restrictions:** {restrictions}

## 2. HAZARD(S) IDENTIFICATION
**Classification:** {hazard_classification}
**Signal Word:** {signal_word}
**Hazard Statements:**
{hazard_statements}

**Precautionary Statements:**
{precautionary_statements}

## 3. COMPOSITION/INFORMATION ON INGREDIENTS
{composition_info}

## 4. FIRST-AID MEASURES
**Inhalation:** {first_aid_inhalation}
**Eye Contact:** {first_aid_eyes}
**Skin Contact:** {first_aid_skin}
**Ingestion:** {first_aid_ingestion}

**Most Important Symptoms:** {symptoms}
**Medical Attention:** {medical_attention}

## 5. FIRE-FIGHTING MEASURES
**Suitable Extinguishing Media:** {extinguishing_media}
**Specific Hazards:** {fire_hazards}
**Protective Equipment:** {firefighter_protection}

## 6. ACCIDENTAL RELEASE MEASURES
**Personal Precautions:** {personal_precautions}
**Environmental Precautions:** {environmental_precautions}
**Cleanup Methods:** {cleanup_methods}

## 7. HANDLING AND STORAGE
**Handling:** {handling_precautions}
**Storage:** {storage_conditions}
**Incompatible Materials:** {incompatible_materials}

## 8. EXPOSURE CONTROLS/PERSONAL PROTECTION
**Control Parameters:** {exposure_limits}
**Personal Protective Equipment:**
- Eyes: {eye_protection}
- Hands: {hand_protection}
- Respiratory: {respiratory_protection}
- Body: {body_protection}

## 9. PHYSICAL AND CHEMICAL PROPERTIES
**Appearance:** {appearance}
**Odor:** {odor}
**pH:** {ph_value}
**Melting Point:** {melting_point}
**Flash Point:** {flash_point}
**Density:** {density}

## 10. STABILITY AND REACTIVITY
**Chemical Stability:** {stability}
**Possibility of Hazardous Reactions:** {hazardous_reactions}
**Conditions to Avoid:** {conditions_avoid}
**Incompatible Materials:** {incompatible_detailed}
**Hazardous Decomposition:** {decomposition_products}

## 11. TOXICOLOGICAL INFORMATION
**Acute Toxicity:** {acute_toxicity}
**Chronic Effects:** {chronic_effects}
**Carcinogenicity:** {carcinogenicity}

## 12. ECOLOGICAL INFORMATION
**Ecotoxicity:** {ecotoxicity}
**Biodegradability:** {biodegradability}
**Environmental Impact:** {environmental_impact}

## 13. DISPOSAL CONSIDERATIONS
**Disposal Methods:** {disposal_methods}
**Contaminated Packaging:** {packaging_disposal}

## 14. TRANSPORT INFORMATION
**UN Number:** {un_number}
**Shipping Name:** {shipping_name}
**Transport Class:** {transport_class}
**Packing Group:** {packing_group}

## 15. REGULATORY INFORMATION
**OSHA:** {osha_status}
**EPA:** {epa_status}
**State Regulations:** {state_regulations}

## 16. OTHER INFORMATION
**Prepared By:** Zava Safety Department
**Revision Date:** {revision_date}
**Version:** {version}
**Disclaimer:** This information is provided in good faith but no warranty is made as to its accuracy.

---
*This SDS complies with OSHA's Hazard Communication Standard (29 CFR 1910.1200)*
"""

COMPLIANCE_TEMPLATE = """
# PRODUCT COMPLIANCE CERTIFICATE
## {product_name}

### Certificate Number: CERT-{cert_number}
### Issue Date: {issue_date}
### Valid Until: {expiry_date}

---

## PRODUCT INFORMATION
**Product Name:** {product_name}
**Model/SKU:** {sku}
**Manufacturer:** Zava Hardware & Garden Supply
**Manufacturing Date:** {manufacturing_date}
**Batch/Lot Number:** {batch_number}

## COMPLIANCE STANDARDS

### Safety Standards
{safety_standards}

### Performance Standards
{performance_standards}

### Environmental Standards
{environmental_standards}

## TEST RESULTS
{test_results}

## CERTIFYING AUTHORITY
**Laboratory:** {testing_lab}
**Certificate Issued By:** {certifier_name}
**Signature:** [Digital Signature]
**License Number:** {license_number}

## VALIDITY
This certificate is valid for products manufactured between {valid_from} and {valid_until}.
Subject to periodic surveillance audits.

---
*This certificate demonstrates compliance with applicable safety and performance standards.*
"""

async def call_github_models_api(prompt: str, max_tokens: int = 1000) -> str:
    """Call GitHub Models GPT-4.1 API to generate content using OpenAI client"""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set")
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical writer specializing in safety documentation for hardware and construction products. Generate realistic but fictional safety data that follows industry standards and regulations. Include specific technical details, measurements, and procedures that would be found in professional safety documentation."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error calling GitHub Models API: {e}")
        return "Error generating content - using fallback"

async def generate_sds_content_gpt4(product: Dict, category: str) -> Dict[str, str]:
    """Generate realistic SDS content using GPT-4.1 with Zava-specific quirks and domain knowledge"""
    
    base_prompt = f"""
    Generate realistic Safety Data Sheet (SDS) content for a {category} product called "{product['name']}" (SKU: {product['sku']}) from Zava Hardware & Garden Supply.

    Zava is known for:
    - Environmentally enhanced products with unique eco-friendly technologies
    - Products that have quirky but beneficial characteristics 
    - Enhanced performance features that exceed industry standards
    - Regional optimization for Pacific Northwest conditions
    - Innovative materials and formulations

    Product category: {category}
    Product name: {product['name']}
    SKU: {product['sku']}

    Generate content for these SDS sections (provide ONLY the content, no section headers):
    """
    
    # Generate each section separately to get more detailed content
    sections = {
        "recommended_use": f"Recommended use and restrictions for {product['name']} in {category} applications:",
        "restrictions": f"Usage restrictions and limitations for {product['name']}:",
        "hazard_classification": f"Hazard classification for {product['name']} ({category} product):",
        "signal_word": f"Appropriate signal word (DANGER, WARNING, or CAUTION) for {product['name']}:",
        "hazard_statements": f"Specific hazard statements for {product['name']} following GHS format:",
        "precautionary_statements": f"Precautionary statements for safe handling of {product['name']}:",
        "composition_info": f"Composition and ingredient information for {product['name']}:",
        "first_aid_inhalation": f"First aid measures for inhalation exposure to {product['name']}:",
        "first_aid_eyes": f"First aid measures for eye contact with {product['name']}:",
        "first_aid_skin": f"First aid measures for skin contact with {product['name']}:",
        "first_aid_ingestion": f"First aid measures for accidental ingestion of {product['name']}:",
        "symptoms": f"Most important symptoms and effects of {product['name']} exposure:",
        "medical_attention": f"Medical attention guidance for {product['name']} exposure:",
        "extinguishing_media": f"Suitable fire extinguishing media for {product['name']}:",
        "fire_hazards": f"Specific fire hazards when {product['name']} burns:",
        "firefighter_protection": f"Protective equipment for firefighters dealing with {product['name']} fires:",
        "personal_precautions": f"Personal precautions for {product['name']} spill cleanup:",
        "environmental_precautions": f"Environmental precautions for {product['name']} spills:",
        "cleanup_methods": f"Methods for cleaning up {product['name']} spills:",
        "handling_precautions": f"Safe handling precautions for {product['name']}:",
        "storage_conditions": f"Proper storage conditions for {product['name']}:",
        "incompatible_materials": f"Materials incompatible with {product['name']}:"
    }
    
    generated_content = {}
    
    for key, prompt in sections.items():
        content = await call_github_models_api(base_prompt + prompt, max_tokens=200)
        generated_content[key] = content
        await asyncio.sleep(0.1)  # Rate limiting
    
    # Generate remaining sections in batches
    physical_prompt = f"""
    Generate physical and chemical properties for {product['name']} ({category}):
    - Appearance and color
    - Odor description
    - pH value
    - Melting point
    - Flash point
    - Density
    Provide realistic technical values.
    """
    physical_content = await call_github_models_api(physical_prompt, max_tokens=300)
    
    # Parse physical properties
    physical_lines = physical_content.split('\n')
    generated_content.update({
        "appearance": "Varies by product specification",
        "odor": "Characteristic odor", 
        "ph_value": "Not applicable",
        "melting_point": "Not applicable",
        "flash_point": ">93°C (>200°F)",
        "density": "See product specification"
    })
    
    # Try to extract specific values from GPT response
    for line in physical_lines:
        if "appearance" in line.lower() or "color" in line.lower():
            generated_content["appearance"] = line.split(':', 1)[-1].strip()
        elif "odor" in line.lower():
            generated_content["odor"] = line.split(':', 1)[-1].strip()
        elif "ph" in line.lower():
            generated_content["ph_value"] = line.split(':', 1)[-1].strip()
        elif "melting" in line.lower():
            generated_content["melting_point"] = line.split(':', 1)[-1].strip()
        elif "flash" in line.lower():
            generated_content["flash_point"] = line.split(':', 1)[-1].strip()
        elif "density" in line.lower():
            generated_content["density"] = line.split(':', 1)[-1].strip()
    
    # Generate remaining content
    remaining_sections = {
        "exposure_limits": f"Exposure limits and control parameters for {product['name']}:",
        "eye_protection": f"Eye protection recommendations for {product['name']}:",
        "hand_protection": f"Hand protection recommendations for {product['name']}:",
        "respiratory_protection": f"Respiratory protection for {product['name']}:",
        "body_protection": f"Body protection recommendations for {product['name']}:",
        "stability": f"Chemical stability information for {product['name']}:",
        "hazardous_reactions": f"Hazardous reaction possibilities for {product['name']}:",
        "conditions_avoid": f"Conditions to avoid with {product['name']}:",
        "incompatible_detailed": f"Detailed incompatible materials for {product['name']}:",
        "decomposition_products": f"Hazardous decomposition products of {product['name']}:",
        "acute_toxicity": f"Acute toxicity information for {product['name']}:",
        "chronic_effects": f"Chronic health effects of {product['name']}:",
        "carcinogenicity": f"Carcinogenicity classification for {product['name']}:",
        "ecotoxicity": f"Environmental toxicity of {product['name']}:",
        "biodegradability": f"Biodegradability of {product['name']}:",
        "environmental_impact": f"Environmental impact of {product['name']}:",
        "disposal_methods": f"Proper disposal methods for {product['name']}:",
        "packaging_disposal": f"Disposal of contaminated {product['name']} packaging:",
        "un_number": f"UN number for shipping {product['name']} (or 'Not regulated'):",
        "shipping_name": f"Proper shipping name for {product['name']}:",
        "transport_class": f"Transport hazard class for {product['name']}:",
        "packing_group": f"Packing group for {product['name']}:",
        "osha_status": f"OSHA compliance status for {product['name']}:",
        "epa_status": f"EPA regulatory status for {product['name']}:",
        "state_regulations": f"State regulatory compliance for {product['name']}:"
    }
    
    for key, prompt in remaining_sections.items():
        content = await call_github_models_api(base_prompt + prompt, max_tokens=150)
        generated_content[key] = content
        await asyncio.sleep(0.1)  # Rate limiting
    
    return generated_content

async def generate_compliance_content_gpt4(product: Dict, category: str) -> Dict[str, str]:
    """Generate compliance certificate content using GPT-4.1 with Zava-specific quirks"""
    
    prompt = f"""
    Generate a realistic compliance certificate for {product['name']} (SKU: {product['sku']}) from Zava Hardware & Garden Supply.

    Product category: {category}
    
    Generate content for:
    1. Safety standards compliance (specific standards with checkmarks)
    2. Performance standards compliance  
    3. Environmental standards compliance
    4. Test results with specific measurements
    5. Testing laboratory name (make it sound official)
    6. Certifier name with credentials
    7. License number
    
    Make it realistic but fictional. Include Zava-specific enhancements and eco-friendly certifications.
    """
    
    content = await call_github_models_api(prompt, max_tokens=800)
    
    # Parse the generated content into structured format
    lines = content.split('\n')
    
    # Generate dates
    from datetime import datetime, timedelta
    valid_from = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    valid_until = (datetime.now() + timedelta(days=545)).strftime('%Y-%m-%d')
    
    return {
        "safety_standards": content,  # Use full content for now
        "performance_standards": "Generated performance standards...",
        "environmental_standards": "Generated environmental standards...",
        "test_results": "Generated test results...",
        "testing_lab": "Zava Advanced Materials Laboratory",
        "certifier_name": "Dr. Marina Coastwell, P.E., Zava Chief Materials Scientist",
        "license_number": f"ZAV-LAB-{random.randint(1000, 9999)}",
        "valid_from": valid_from,
        "valid_until": valid_until
    }

async def generate_zava_quirks_document_gpt4(product: Dict, category: str) -> str:
    """Generate Zava-specific installation quirks and tips using GPT-4.1"""
    
    prompt = f"""
    Generate quirky but realistic installation notes for {product['name']} (SKU: {product['sku']}) from Zava Hardware & Garden Supply.

    Zava products are known for having unusual but beneficial characteristics like:
    - Self-healing properties
    - Color-changing indicators
    - Enhanced performance in specific conditions
    - Eco-friendly surprises
    - Smart adaptive behaviors

    Product category: {category}

    Create installation quirks and tips that sound professional but include these unique Zava characteristics. Include:
    - Specific installation conditions or requirements
    - Unusual but normal behaviors the product exhibits
    - Performance enhancements
    - Troubleshooting for "quirky" behaviors
    - Customer support contact info

    Format as a professional technical document.
    """
    
    quirks_content = await call_github_models_api(prompt, max_tokens=600)
    
    return f"""# ZAVA INSTALLATION QUIRKS & TIPS
## {product['name']} - SKU: {product['sku']}

### IMPORTANT ZAVA-SPECIFIC NOTES
{quirks_content}

### ZAVA CUSTOMER SUPPORT
For questions about unusual but normal Zava behaviors:
📞 1-800-ZAVA-QUIRK (1-800-928-2-7847)
🌐 support.zava.com/quirks-explained
📧 quirks@zava.com

*Remember: If it seems too good to be true with Zava, it's probably just our enhanced technology working as designed!*
---
Document Version: ZQ-{random.randint(100, 999)}
Last Updated: {datetime.now().strftime('%Y-%m-%d')}
"""

async def generate_environmental_statement_gpt4(product: Dict, category: str) -> str:
    """Generate Zava environmental impact statement using GPT-4.1"""
    
    prompt = f"""
    Generate an environmental impact statement for {product['name']} (SKU: {product['sku']}) from Zava Hardware & Garden Supply.

    Include:
    - Carbon impact metrics (carbon negative/positive)
    - Water stewardship information
    - Biodiversity support
    - Lifecycle management
    - EcoShield technology benefits
    - Supply chain sustainability
    - Third-party certifications
    - Environmental awards
    - Lifecycle assessment summary

    Make it sound professional and environmentally progressive, with specific metrics and certifications.
    Product category: {category}
    """
    
    env_content = await call_github_models_api(prompt, max_tokens=800)
    
    return f"""# ENVIRONMENTAL IMPACT STATEMENT
## {product['name']} - SKU: {product['sku']}

{env_content}

---
*This statement reflects Zava's commitment to environmental stewardship and our belief that exceptional performance and environmental responsibility are not mutually exclusive.*

Environmental Impact Verified By: Pacific Northwest Sustainability Institute
Verification Date: {(datetime.now() - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d')}
Document ID: EIS-{random.randint(1000, 9999)}
"""

def markdown_to_pdf_paragraphs(markdown_text: str, styles) -> List:
    """Convert markdown text to ReportLab paragraphs"""
    paragraphs = []
    lines = markdown_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            paragraphs.append(Spacer(1, 6))
            continue
            
        # Handle headers
        if line.startswith('# '):
            text = line[2:].strip()
            paragraphs.append(Paragraph(text, styles['Title']))
            paragraphs.append(Spacer(1, 12))
        elif line.startswith('## '):
            text = line[3:].strip()
            paragraphs.append(Paragraph(text, styles['Heading1']))
            paragraphs.append(Spacer(1, 6))
        elif line.startswith('### '):
            text = line[4:].strip()
            paragraphs.append(Paragraph(text, styles['Heading2']))
            paragraphs.append(Spacer(1, 4))
        elif line.startswith('**') and line.endswith('**'):
            text = line[2:-2].strip()
            paragraphs.append(Paragraph(f'<b>{text}</b>', styles['Normal']))
        elif line.startswith('- ') or line.startswith('• '):
            text = line[2:].strip()
            paragraphs.append(Paragraph(f'• {text}', styles['Normal']))
        elif line.startswith('*') and line.endswith('*'):
            text = line[1:-1].strip()
            paragraphs.append(Paragraph(f'<i>{text}</i>', styles['Normal']))
        elif line.startswith('---'):
            paragraphs.append(Spacer(1, 6))
        else:
            # Handle bold inline formatting
            if '**' in line:
                # Simple bold replacement
                line = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
            paragraphs.append(Paragraph(line, styles['Normal']))
    
    return paragraphs

def create_pdf_document(content: str, filename: str, output_dir: str = "/workspace/manuals") -> str:
    """Create a PDF document from markdown content"""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Full path for the PDF
    pdf_path = Path(output_dir) / filename
    
    # Create the PDF document
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Get styles and create custom ones
    styles = getSampleStyleSheet()
    
    # Create custom styles that won't conflict
    title_style = ParagraphStyle(
        'ZavaTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'ZavaHeader',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkred,
        leftIndent=0
    )
    
    subheader_style = ParagraphStyle(
        'ZavaSubHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.darkgreen,
        leftIndent=0
    )
    
    # Add custom styles to stylesheet
    styles.add(title_style)
    styles.add(header_style)
    styles.add(subheader_style)
    
    # Build content
    content_paragraphs = []
    
    # Add Zava header
    header_text = f"""
    <para align=center>
    <font size=18 color="darkblue"><b>ZAVA HARDWARE & GARDEN SUPPLY</b></font><br/>
    <font size=12 color="gray">Professional Grade • Environmentally Enhanced • Contractor Trusted</font>
    </para>
    """
    content_paragraphs.append(Paragraph(header_text, styles['Normal']))
    content_paragraphs.append(Spacer(1, 20))
    
    # Convert markdown content to paragraphs using original styles
    content_paragraphs.extend(markdown_to_pdf_paragraphs(content, styles))
    
    # Add footer
    footer_text = f"""
    <para align=center>
    <font size=8 color="gray">
    Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    Zava Hardware & Garden Supply | 
    www.zava.com | 
    1-800-ZAVA-HELP
    </font>
    </para>
    """
    content_paragraphs.append(Spacer(1, 20))
    content_paragraphs.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(content_paragraphs)
    
    return str(pdf_path)

async def generate_safety_documents(conn: asyncpg.Connection, max_products: Optional[int] = None) -> None:
    """Generate safety documentation for products as PDF files using GPT-4.1"""
    
    # Get ALL products for safety documentation
    if max_products:
        products = await conn.fetch("""
            SELECT p.product_id, p.sku, p.product_name as name, 
                   c.category_name as category, pt.type_name as type
            FROM retail.products p
            JOIN retail.categories c ON p.category_id = c.category_id
            JOIN retail.product_types pt ON p.type_id = pt.type_id
            ORDER BY p.product_id
            LIMIT $1
        """, max_products)
    else:
        products = await conn.fetch("""
            SELECT p.product_id, p.sku, p.product_name as name, 
                   c.category_name as category, pt.type_name as type
            FROM retail.products p
            JOIN retail.categories c ON p.category_id = c.category_id
            JOIN retail.product_types pt ON p.type_id = pt.type_id
            ORDER BY p.product_id
        """)
    
    console.print(Panel.fit(
        f"[bold blue]🔬 Safety Document Generation[/bold blue]\n"
        f"Generating safety documents for [bold]{len(products)}[/bold] products using GPT-4.1",
        border_style="blue"
    ))
    
    pdf_count = 0
    created_files = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Processing products...", total=len(products))
        
        for product in products:
            product_dict = dict(product)
            sku = product['sku'].replace('/', '_').replace(' ', '_')  # Sanitize SKU for filename
            
            progress.update(task, description=f"Processing [bold]{product['name']}[/bold] ({product['sku']})")
            
            try:
                # Generate SDS with GPT-4.1
                sds_content = await generate_sds_content_gpt4(product_dict, product['category'])
                sds_document = SDS_TEMPLATE.format(
                    product_name=product['name'],
                    sku=product['sku'],
                    revision_date=(datetime.now() - timedelta(days=random.randint(30, 730))).strftime('%Y-%m-%d'),
                    sds_number=f"{random.randint(1000, 9999)}",
                    version="1.0",
                    **sds_content
                )
                
                # Create SDS PDF
                sds_filename = f"{sku}_SDS_GPT4.pdf"
                sds_path = create_pdf_document(sds_document, sds_filename, "/workspace/manuals")
                created_files.append(sds_path)
                pdf_count += 1
                
                # Generate compliance certificate with GPT-4.1
                compliance_content = await generate_compliance_content_gpt4(product_dict, product['category'])
                compliance_document = COMPLIANCE_TEMPLATE.format(
                    product_name=product['name'],
                    sku=product['sku'],
                    cert_number=f"{random.randint(10000, 99999)}",
                    issue_date=(datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d'),
                    expiry_date=(datetime.now() + timedelta(days=730)).strftime('%Y-%m-%d'),
                    manufacturing_date=(datetime.now() - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d'),
                    batch_number=f"LOT-{random.randint(100000, 999999)}",
                    **compliance_content
                )
                
                # Create Compliance PDF
                compliance_filename = f"{sku}_COMPLIANCE_GPT4.pdf"
                compliance_path = create_pdf_document(compliance_document, compliance_filename, "/workspace/manuals")
                created_files.append(compliance_path)
                pdf_count += 1
                
                # Generate Zava-specific installation quirks document with GPT-4.1
                if random.random() < 0.4:  # 40% of products get quirks document
                    quirks_document = await generate_zava_quirks_document_gpt4(product_dict, product['category'])
                    quirks_filename = f"{sku}_QUIRKS_GPT4.pdf"
                    quirks_path = create_pdf_document(quirks_document, quirks_filename, "/workspace/manuals")
                    created_files.append(quirks_path)
                    pdf_count += 1
                
                # Generate environmental impact statement with GPT-4.1 for some products
                if random.random() < 0.3:  # 30% get environmental statements
                    env_document = await generate_environmental_statement_gpt4(product_dict, product['category'])
                    env_filename = f"{sku}_ENVIRONMENTAL_GPT4.pdf"
                    env_path = create_pdf_document(env_document, env_filename, "/workspace/manuals")
                    created_files.append(env_path)
                    pdf_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing [bold]{product['name']}[/bold]: {e}")
                continue
            
            progress.advance(task)
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)
    
    # Final summary
    console.print(Panel.fit(
        f"[bold green]✅ Generation Complete![/bold green]\n"
        f"Created [bold]{pdf_count}[/bold] PDF files using GPT-4.1\n"
        f"Files saved in: [bold]/workspace/manuals/[/bold] directory",
        border_style="green"
    ))
    
    # Show some sample filenames
    if created_files:
        console.print("\n[bold]📁 Sample files created:[/bold]")
        for file_path in created_files[:10]:  # Show first 10 files
            console.print(f"  • {Path(file_path).name}")
        if len(created_files) > 10:
            console.print(f"  ... and [bold]{len(created_files) - 10}[/bold] more files")

async def main() -> None:
    """Main function to generate safety documents as PDFs using GPT-4.1"""
    try:
        # Display startup banner
        console.print(Panel.fit(
            "[bold blue]🏗️ Zava Safety Document Generator[/bold blue]\n"
            "[dim]GPT-4.1 Enhanced Version[/dim]",
            border_style="blue"
        ))
        
        if not GITHUB_TOKEN:
            console.print("[bold red]❌ Error:[/bold red] GITHUB_TOKEN environment variable must be set to use GitHub Models API")
            raise ValueError("GITHUB_TOKEN environment variable must be set to use GitHub Models API")
            
        POSTGRES_CONFIG = {
            'host': 'db',
            'port': 5432,
            'user': 'postgres',
            'password': 'P@ssw0rd!',
            'database': 'zava'
        }
        
        with console.status("[bold blue]Connecting to PostgreSQL...") as status:
            conn = await asyncpg.connect(**POSTGRES_CONFIG)
        console.print("✅ [bold green]Connected to PostgreSQL[/bold green] for safety document generation")
        
        # Generate for a limited number of products initially (to test API limits)
        await generate_safety_documents(conn, max_products=5)  # Start with 5 products
        
        # Show directory contents
        manuals_path = Path("/workspace/manuals")
        if manuals_path.exists():
            pdf_files = list(manuals_path.glob("*GPT4*.pdf"))
            
            # Group by document type
            sds_files = [f for f in pdf_files if "_SDS_GPT4.pdf" in f.name]
            compliance_files = [f for f in pdf_files if "_COMPLIANCE_GPT4.pdf" in f.name]
            quirks_files = [f for f in pdf_files if "_QUIRKS_GPT4.pdf" in f.name]
            env_files = [f for f in pdf_files if "_ENVIRONMENTAL_GPT4.pdf" in f.name]
            
            console.print(Panel(
                f"[bold]📊 Document Type Breakdown:[/bold]\n\n"
                f"🧪 Safety Data Sheets: [bold]{len(sds_files)}[/bold] files\n"
                f"📋 Compliance Certificates: [bold]{len(compliance_files)}[/bold] files\n"
                f"🔧 Installation Quirks: [bold]{len(quirks_files)}[/bold] files\n"
                f"🌱 Environmental Statements: [bold]{len(env_files)}[/bold] files\n\n"
                f"[bold]Total: {len(pdf_files)} GPT-4.1 generated files[/bold]",
                title="📁 Results Summary",
                border_style="cyan"
            ))
        
        await conn.close()
        console.print("✅ [bold green]Database connection closed[/bold green]")
        
    except Exception as e:
        logger.error(f"Error in safety document generation: {e}")
        console.print(f"[bold red]❌ Generation failed:[/bold red] {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())