# Zava DIY Dataset Plus MCP

A comprehensive demonstration project featuring a realistic PostgreSQL dataset for **Zava DIY**, a fictional home improvement retail company, combined with three specialized Model Context Protocol (MCP) servers. This project showcases advanced retail analytics, AI-powered product search capabilities, and secure multi-store data access patterns.

## Project Overview

This project provides:

- **🏪 Realistic Retail Dataset**: A complete PostgreSQL database with 50,000+ customers, 400+ products, 200,000+ transactions, and AI-ready vector embeddings
- **🔍 Customer Sales MCP Servers**: Two intelligent product search servers - basic name-based search and advanced semantic search with AI
- **📊 Sales Analysis MCP Server**: Comprehensive sales database access for AI-powered analytics and insights
- **🔒 Row Level Security**: Multi-tenant security ensuring store managers only access their store's data
- **🚀 AI/ML Ready**: Vector embeddings for product similarity search and recommendation systems

The dataset simulates **Zava DIY**, a Washington State-based home improvement retailer with 8 locations (7 physical stores + online), complete with seasonal variations, realistic customer behavior patterns, and comprehensive product catalog covering tools, lumber, electrical, plumbing, and garden supplies.

## How to Use This Project

Fork this repository to get started with the Zava DIY dataset and MCP servers. The project is designed to be used in a development container for easy setup and includes scripts for deploying Azure resources if you want to integrate with Azure AI services. Then make it your own by customizing the dataset, MCP servers, or building new applications on top of the provided infrastructure..

## Contributions

Contributions are welcome! If you have ideas for improvements, new features, or bug fixes, please open an issue or submit a pull request.

## Prerequisites

Before getting started, ensure you have:

- **Docker Desktop** installed and running
- **Visual Studio Code** with the Dev Containers extension
- **Git** for cloning the repository

## Getting Started

### Opening the Project in a Dev Container

1. **Clone the repository**:
   ```bash
   git clone https://github.com/gloveboxes/ai-tour-26-zava-diy-dataset-plus-mcp.git
   cd ai-tour-26-zava-diy-dataset-plus-mcp
   ```

   > **Note**: If you plan to use the data generation tools, uncomment `# -r data/requirements.txt` in the `requirements-dev.txt` file in the root folder of the repo before opening the dev container. This adds additional libraries required for data generation but will increase the dev container setup time.

2. **Open in VS Code**:
   ```bash
   code .
   ```

3. **Reopen in Container**:
   - When prompted by VS Code, click "Reopen in Container"
   - Or use the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and select "Dev Containers: Reopen in Container"
   - Or click the green button in the bottom-left corner and select "Reopen in Container"

4. **Wait for Setup**:
   - The dev container will build automatically with all dependencies pre-installed
   - This includes PostgreSQL with pgvector extension, Python environment, and all required packages

The dev container provides a complete development environment with:
- PostgreSQL database with pgvector extension
- Python 3.x with all required packages
- Azure CLI for cloud deployments

### Deploying Azure Resources (Optional)

If you want to use Azure AI services with this project, you can deploy the required Azure resources:

> **Note**: You'll need to be logged in to Azure CLI (`az login`) and have appropriate permissions to create resources in your subscription.

```bash
cd infra && ./deploy.sh
```

The deployment script will:
- Create an Azure AI Foundry workspace
- Deploy both **gpt-4o-mini** and **text-embedding-3-small** models
- Configure environment variables in `src/python/workshop/.env`

### Authenticating with Azure

If you plan to use the Azure AI models with this project, you'll need to authenticate with Azure first. Use the following command:

```bash
az login --use-device-code
```

This will display output similar to:
```
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code JGNL9Q4HW to authenticate.
```

Follow these steps:
1. Copy the device code (e.g., `JGNL9Q4HW`)
1. Open a web browser and navigate to https://microsoft.com/devicelogin
2. Paste the device code (e.g., `JGNL9Q4HW`)
3. Complete the authentication process in your browser
4. Return to your terminal to confirm successful authentication

Once authenticated, you can proceed use the Azure AI models in your applications and MCP servers.

## MCP Servers

This project includes three specialized Model Context Protocol servers designed for different retail scenarios:

### 🔍 Customer Sales MCP Servers

**Purpose**: Intelligent product search and customer assistance

The Customer Sales collection provides two specialized servers with different capabilities:

#### Basic Customer Sales Server (`customer_sales.py`)
**Key Features**:
- Product search by name with fuzzy matching
- Store-specific product availability through Row Level Security
- Real-time inventory levels and stock information
- Traditional name-based product search
- Optimized for simple product lookups

#### Semantic Search Customer Sales Server (`customer_sales_semantic_search.py`)
**Key Features**:
- AI-powered semantic product search using Azure OpenAI
- Natural language product discovery with text-embedding-3-small
- Vector similarity matching with pgvector
- Store-specific product availability through Row Level Security
- Real-time inventory levels and stock information
- Relevance scoring for intelligent product matching

**Use Cases**:
- Customer service applications helping customers find products
- Store associate tools for inventory lookup
- E-commerce product search and recommendations
- AI chatbots for customer product inquiries
- Natural language product discovery

📖 **[Read the Customer Sales MCP Servers Documentation](src/python/mcp_server/customer_sales/README.md)**

### 📊 Sales Analysis MCP Server

**Purpose**: Comprehensive sales database access and analytics

**Key Features**:
- Multi-table schema access for complete database insights
- Secure PostgreSQL query execution with Row Level Security
- Access to customers, orders, inventory, and product data
- Time-series analysis with UTC date utilities
- Store manager access control and data isolation

**Use Cases**:
- Sales performance analysis and reporting
- Business intelligence and data analytics
- Store manager dashboards and insights
- AI-powered business decision support
- Customer behavior and trend analysis

📖 **[Read the Sales Analysis MCP Server Documentation](src/python/mcp_server/sales_analysis/README.md)**

### Security Model

All three servers implement **Row Level Security (RLS)** ensuring:
- **Store managers** only access their store's data
- **Customer service reps** see store-specific product availability
- **Data isolation** between different store locations
- **Global admin access** for corporate-level analysis

## Dataset Overview

The Zava DIY PostgreSQL database provides a comprehensive retail ecosystem with realistic data patterns:

### 📊 Dataset Scale

| Component | Count | Description |
|-----------|-------|-------------|
| **Customers** | 50,000+ | Realistic demographic profiles across Washington State |
| **Products** | 400+ | Complete DIY home improvement catalog |
| **Stores** | 8 | Physical + online locations across Washington State |
| **Order Items** | 200,000+ | Detailed line items with pricing and quantities |
| **Inventory Records** | 3,000+ | Store-specific stock levels |
| **Vector Embeddings** | 400+ | AI-powered product similarity search |

### 🏪 Store Locations

- **High-Traffic Stores**: Seattle, Bellevue, Online
- **Regional Stores**: Tacoma, Spokane
- **Specialty Markets**: Everett, Redmond, Kirkland
- **Geographic Distribution**: Realistic Washington State market penetration

### 📦 Product Categories

The dataset includes the following product categories with all available products:

- **Electrical**: AFCI Breaker 15-Amp, AFCI Outlet 15-Amp, Armored Cable BX 12-2, Ceiling Box with Bracket, Color-Coded Tape Set, Dimmer Switch LED, Double Pole Breaker 30A, EMT Conduit 1/2-inch, Flexible Conduit 1/2-inch, Friction Tape, GFCI Breaker 20-Amp, GFCI Outlet 20-Amp, Grease Cap Wire Nuts, Heavy Duty Cord 100ft, High-Temp Electrical Tape, Indoor Extension Cord 25ft, Junction Box 4x4, LED Flush Mount Ceiling, Large Wire Nuts, Liquid-Tight Conduit, Motion Sensor Switch, Multi-Outlet Power Strip, Old Work Box, Outdoor Extension Cord 50ft, Outdoor Flood Light LED, Outlet Box Single Gang, PVC Conduit 3/4-inch, Pendant Light Kitchen, Push-In Connectors, Retractable Cord Reel, Rigid Conduit 1-inch, Romex Wire 12-2 250ft, Romex Wire 14-2 250ft, Self-Fusing Silicone Tape, Single Pole Breaker 15A, Single Pole Breaker 20A, Single Pole Switch, Standard Outlet 15-Amp, THHN Wire 12 AWG, Three-Way Switch, Timer Switch, Track Lighting Kit, Twist-On Connectors, USB Outlet with Charging, Underground Wire 12-2, Vanity Light 3-Bulb, Vinyl Electrical Tape, Weather Resistant Outlet, Weatherproof Box, Wire Nut Assortment

- **Garden & Outdoor**: All-Purpose Fertilizer 50lb, Anvil Pruners Heavy Duty, Cactus Potting Mix, Cedar Mulch 3 Cu Ft, Ceramic Planter 12-inch, Drinking Water Safe Hose, Expandable Hose 100-foot, Flower Seed Mix Wildflower, Garden Hose 50-foot, Garden Rake Steel Tines, Garden Soil Enriched, Garden Spade Long Handle, Grass Seed Sun & Shade, Hanging Basket Planter, Hardwood Mulch 2 Cu Ft, Heavy Duty Hose 75-foot, Herb Garden Seed Set, Impact Sprinkler, In-Ground Sprinkler Head, LED Flood Light 30W, Landscape Spotlight Kit, Lawn Fertilizer Spring, Misting Sprinkler Kit, Organic Compost 40lb, Organic Heirloom Seeds, Oscillating Sprinkler, Plastic Planter Set, Pole Saw Pruner 8-foot, Potting Mix Premium 40lb, Rotary Sprinkler 3-Arm, Rubber Mulch Black, Seed Starting Mix, Self-Watering Planter, Slow Release Granules, Soaker Hose 25-foot, Solar Deck Light Set, Solar Path Light Set, Straw Mulch Bale, String Lights 48-foot, Tomato Plant Food, Topsoil Screened 40lb, Vegetable Seed Starter Kit, Wooden Barrel Planter

- **Hand Tools**: Adjustable Wrench 10-inch, Ball Peen Hammer 12oz, Ball-End Hex Set, Combination Wrench Set SAE, Coping Saw, Digital Caliper 6-inch, Finishing Hammer 13oz, Flathead Screwdriver Set, Folding Rule 6-foot, Insulated Screwdriver Set, Level 24-inch, Lineman's Pliers 9-inch, Locking Pliers 10-inch, Long Arm Hex Set, Metric Hex Key Set, Metric Wrench Set, Needle-Nose Pliers 6-inch, Phillips Screwdriver Set, Pipe Wrench Set, Precision Screwdriver Kit, Professional Claw Hammer 16oz, Ratcheting Screwdriver, Riffler File Set, SAE Hex Key Set, Sledge Hammer 3lb, Speed Square 7-inch, T-Handle Hex Set, Tape Measure 25-foot, Torque Wrench 1/2-drive, Wire Stripping Pliers, Wood Rasp Set

- **Hardware**: Angle Bracket 4-inch, Barrel Latch 4-inch, Brad Nails 18-gauge, Butt Hinge 3-1/2 inch, Cabinet Knob Set Brushed Nickel, Cabinet Lock Cam Type, Cabinet Pull 4-inch Centers, Carriage Bolt Set, Chain Lock Door Security, Common Nail Assortment, Concealed Cabinet Hinge, Countertop Support Bracket, Deadbolt Lock Keyed, Deck Screws 2-1/2 inch, Door Handle Lever Set, Door Knob Lock Set, Drawer Pull 5-inch, Drywall Screws 1-5/8 inch, Eye Bolts Assorted, Fender Washer Kit, Finish Nails 2-inch, Fixed Caster 3-inch, Flat Washer Assortment SAE, Floating Shelf Bracket, Furniture Caster Set, Hex Bolt Kit Grade 5, Hook and Eye Latch, L-Bracket Galvanized, Lag Bolts 1/2 x 6-inch, Lock Washer Set, Locking Caster Set, Machine Screws Kit, Masonry Nails, Metric Washer Assortment, Padlock Set Keyed Alike, Piano Hinge 2-foot, Pneumatic Caster 4-inch, Roofing Nails 1-1/4 inch, Rubber Washer Set, Security Hasp 6-inch, Self-Tapping Screws, Shelf Bracket 8-inch, Slide Bolt Latch, Spring Hinge Self-Closing, Strap Hinge Heavy Duty, Swivel Caster 2-inch, T-Handle Cabinet Hardware, Thumb Latch Galvanized, Toggle Bolt Set, Wood Screw Assortment

- **Lumber & Building Materials**: Advantech Subflooring, Baseboard Molding 8ft, Birch Plywood 4x8x1/2, Blown-In Insulation R-30, CDX Plywood 4x8x3/4, Cedar 2x4x8, Cedar Board 1x8x10, Cedar Post 6x6x8, Chair Rail Molding, Crack Resistant Mix, Crown Molding Pine 8ft, Deck Post 6x6x10, Douglas Fir 2x6x10, Durock Cement Board, Exterior Cement Board, Fast-Set Concrete 50lb, Fiberglass Batts R-13, Fire Resistant Drywall, Foam Board Insulation, Hardiebacker 3x5x1/4, High Strength Mix 80lb, Lightweight Drywall 4x8, MDF Trim Board 1x4, Marine Plywood 4x8x3/4, Moisture Resistant Drywall, OSB Sheathing 4x8x7/16, OSB Siding Panel, OSB Subflooring 4x8x3/4, PT Landscape Timber, PT Post 4x4x8, PVC Trim Board 1x6, Permabase Board 4x8, Pine Board 1x4x8, Pine Stud 2x4x8, Poplar Board 1x6x8, Pressure Treated 2x4x8, Pressure Treated Plywood, Quarter Round 8ft, Quikrete Mix 80lb, Ready Mix Concrete 60lb, Reflective Insulation, Round Fence Post 8ft, Soundproof Drywall 4x8, Spray Foam Kit, Standard Drywall 4x8x1/2, Treated 2x8x12 Joist, Window Casing Set, WonderBoard Lite, ZIP System Sheathing

- **Paint & Finishes**: Aerosol Primer Spray, Angled Brush Set, Artist Detail Brush Set, Canvas Drop Cloth 9x12, Canvas Runner 4x15, Clear Polyurethane Satin, Deck and Fence Stain, Disposable Paint Tray Set, Drywall Primer, Elastomeric Exterior Paint, Extension Pole 4-foot, Exterior Acrylic Paint, Exterior Latex Paint Satin, Exterior Primer-Paint Combo, Floor Polyurethane, Foam Brush Set, Gel Stain, Gloss Polyurethane, Gloss Spray Paint, Interior Eggshell Paint, Interior Semi-Gloss Paint, Masonry Primer, Matte Finish Spray Paint, Metal Paint Tray 9-inch, Metal Primer, Microfiber Roller Covers, Mini Roller Kit 4-inch, Nap Roller Cover Set, Natural Bristle Brush Set, Oil-Based Polyurethane, Oil-Based Wood Stain, One-Coat Interior Paint, Paint Bucket Grid, Paint Spray Gun, Paint Tray Liner Set, Paper Drop Cloth, Plastic Drop Cloth, Pre-Taped Masking Film, Premium Interior Latex Flat, Roller Frame 9-inch, Rolling Tray with Grid, Rust Prevention Spray, Semi-Transparent Deck Stain, Solid Color Deck Stain, Stain-Blocking Primer, Synthetic Brush Set, Textured Spray Paint, Universal Bonding Primer, Water-Based Polyurethane, Water-Based Wood Stain, Zero VOC Interior Paint

- **Plumbing**: Angle Stop Valve, Ball Valve 1/2-inch, Bathroom Lavatory Faucet, Check Valve 1-inch, Compression Fittings, Copper Fitting Kit, Copper Pipe 1-inch Type L, Copper Pipe 1/2-inch Type L, Copper Pipe 3/4-inch Type L, Drain Cleaning Chemical, Drain Snake 25-foot, Fiberglass Pipe Insulation, Fill Valve Assembly, Flexible PVC Pipe, Foam Pipe Insulation 1/2, Gate Valve 3/4-inch, Heavy Duty Teflon Tape, Hydro Jet Drain Cleaner, Kitchen Sink Faucet, Outdoor Spigot Faucet, PTFE Thread Tape White, PVC Elbow Assortment, PVC Pipe 1-1/2 inch x 10ft, PVC Pipe 2-inch x 10ft, PVC Pipe 3-inch x 10ft, PVC Pipe 4-inch x 10ft, PVC Tee Fitting Set, Pink Plumber's Tape, Pipe Dope Stick, Pipe Heat Tape, Pipe Insulation 3/4-inch, Pipe Insulation Tape, Pipe Joint Compound, Pipe Thread Sealant Paste, Plumber's Grease, Plumber's Putty 14oz, Plunger Set, Pre-Insulated Copper Pipe, Pressure Relief Valve, Push-Fit Connectors, Shower Faucet Trim Kit, Silicone Plumber's Putty, Soft Copper Coil 1/2-inch, Toilet Auger, Toilet Flapper Universal, Toilet Repair Kit Complete, Toilet Seat Standard, Toilet Wax Ring, Utility Sink Faucet, Yellow Gas Line Tape

- **Power Tools**: Angle Grinder 4-1/2 inch, Barrel Grip Jigsaw, Basic Miter Saw 10-inch, Belt Sander 3x21 inch, Benchtop Drill Press, Brushless Impact Driver, Circular Saw 7-1/4 inch, Compact Belt Sander 3x18, Compact Impact Driver, Compact Recip Saw, Compound Miter Saw 10-inch, Cordless Angle Grinder, Cordless Circular Saw 6-1/2, Cordless Drill 18V Li-Ion, Cordless Jigsaw 20V, Cordless Miter Saw 10-inch, Cordless Recip Saw 18V, Cordless Router 18V, Cut-Off Tool 3-inch, Drywall Sander, File Belt Sander, Fixed Base Router 1-3/4 HP, Hammer Drill 1/2-inch, Heavy Duty Jigsaw, Impact Drill 20V, Impact Driver 18V, Impact Wrench 1/2-inch, Large Angle Grinder 7-inch, Mini Circular Saw 4-1/2, Miter Saw Stand, Mouse Sander, Multi-Tool Oscillating, Orbital Sander 1/4 Sheet, Palm Sander, Plunge Router 2-1/4 HP, Random Orbit Sander 5-inch, Reciprocating Saw Corded, Right Angle Drill, Right Angle Impact, Router Table Combo, Scrolling Jigsaw, Sliding Miter Saw 12-inch, Stationary Belt Sander, Track Saw, Trim Router 1 HP, Variable Speed Belt Sander, Variable Speed Grinder, Variable Speed Jigsaw, Worm Drive Saw

- **Storage & Organization**: Adjustable Height Workbench, Base Cabinet with Drawers, Ceiling Hook Kit, Ceiling Storage Rack 4x8, Ceiling Track System, Chemical Storage Cabinet, Clear Storage Bin 27-Quart, Corner Shelf Unit, Craft Storage Drawers, Desktop Organizer Drawers, Folding Workbench Portable, Garage Ceiling Hoist, Garage Workbench Kit, Gym Style Locker Bank, Heavy Duty Rack System, Heavy Duty Tote 35-Gallon, Heavy Duty Wall Hook Set, Heavy Duty Workbench 6-foot, Large Drawer Unit 10-Drawer, Magnetic Tool Holder, Metal Locker 2-Door, Metal Pegboard Gray, Metal Storage Cabinet 72-inch, Metal Tool Cabinet, Mobile Work Cart, Modular Cabinet System, Overhead Storage Platform, Pegboard Hook Set 50-piece, Pegboard Panel 4x8, Pegboard Storage Bins, Pegboard Tool Holder Set, Personal Storage Locker, Plastic Tool Box Set, Portable Tool Box 20-inch, Retractable Hose Hanger, Rolling Drawer Cart, Rolling Tool Chest 26-inch, Rubber Coated Hooks, Safety Net for Storage, Small Parts Organizer, Stackable Bin Set, Stackable Drawer Set, Steel Shelving 5-Tier, Tool Bag Canvas 18-inch, Wall Mount Cabinet, Weatherproof Storage Box, Wire Mesh Locker, Wire Shelving Chrome, Wooden Locker Bench, Wooden Storage Shelves

### 🌡️ Seasonal Patterns

The dataset includes realistic seasonal variations:
- **Spring Surge**: Paint and garden products peak in March-May
- **Summer Construction**: Power tools and lumber peak in June-August
- **Fall Preparation**: Hardware and storage products increase
- **Winter Maintenance**: Hand tools and indoor projects

### 💰 Financial Modeling

- **Consistent 33% gross margin** across all products
- **Year-over-year growth patterns** (2020-2026)
- **Store performance variations** based on market size
- **Seasonal revenue fluctuations** aligned with product demand

📖 **[Read the Complete Dataset Documentation](data/database/README.md)**

## Project Structure

```
ai-tour-26-zava-diy-dataset-plus-mcp/
├── .devcontainer/              # Dev container configuration
├── .github/                    # GitHub workflows and templates
├── .vscode/                    # VS Code settings and MCP configuration
├── data/                       # Database files and data generation
│   ├── database/               # Database generator scripts and utilities
│   ├── raft-generator/         # RAFT dataset generation tools
│   ├── requirements.txt        # Data generation dependencies
│   └── zava_retail_*.backup    # Database backup files
├── docs/                       # Documentation and workshop guides
│   ├── docs/                   # MkDocs documentation content
│   ├── mkdocs.yml             # Documentation configuration
│   └── requirements.txt       # Documentation dependencies
├── images/                     # Product images for the dataset
├── infra/                      # Azure Infrastructure as Code (Bicep)
│   ├── deploy.ps1             # PowerShell deployment script
│   ├── deploy.sh              # Bash deployment script
│   ├── foundry-*.bicep        # Azure AI Foundry templates
│   ├── main.bicep             # Main infrastructure template
│   └── main.parameters.json   # Infrastructure parameters
├── media/                      # Media files and assets
├── scripts/                    # Utility scripts
│   └── init-db.sh             # Database initialization script
├── src/
│   ├── python/
│   │   ├── mcp_server/         # Model Context Protocol servers
│   │   │   ├── customer_sales/ # Customer product search MCP server
│   │   │   └── sales_analysis/ # Sales analytics MCP server
│   │   ├── web_app/           # Web application demos
│   │   └── requirements.txt   # Python dependencies
│   └── shared/                # Shared utilities and resources
├── .env.example               # Environment variables template
├── docker-compose.yml         # Multi-service development environment
├── pyproject.toml            # Python project configuration
├── requirements-dev.txt      # Development dependencies
└── README.md                 # This file
```

### Key Components

- **🐳 Dev Container**: Complete development environment with PostgreSQL, Python, and all dependencies
- **🔧 MCP Servers**: Three specialized servers for product search (basic and semantic) and sales analysis
- **🗄️ Database Generator**: Creates realistic retail data with seasonal patterns
- **📱 Web Applications**: Demo applications showcasing the dataset and MCP servers
- **🏗️ Infrastructure**: Azure deployment templates and configurations
- **📚 Documentation**: Comprehensive guides and API documentation

## Zava Web Chat Client

This project includes a **Zava Web Chat Client** - a complete web application with HTML/CSS/JavaScript assets for building a basic web client interface. The web client provides a foundation for creating customer-facing chat applications that can integrate with the MCP servers for product search and sales assistance.

**Key Features**:

- **Web Application**: Pre-built Python web app for chat functionality (located in `src/python/web_app/`)
- **Frontend Assets**: Complete HTML/CSS/JavaScript components for web interface (located in `src/shared/static/`)
- **Integration Ready**: Designed to work with the project's MCP servers
- **Customizable**: Basic client that you can wire up and customize for your project

You'll need to wire up the web client to your specific project requirements and configure it to work with your chosen MCP servers and AI models.

## Getting Started with the Project

1. **Set up the dev container** (see instructions above)
2. **Generate the database** using the data generator
3. **Start the MCP servers** using VS Code tasks or directly
4. **Explore the dataset** using the provided sample queries
5. **Build applications** using the MCP servers for AI-powered retail experiences

This project serves as both a learning resource and a foundation for building sophisticated retail AI applications with realistic data patterns and secure multi-tenant access controls.