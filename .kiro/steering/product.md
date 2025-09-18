# Product Overview

This is a **Product Information Management System** (商品信息管理系统) built for managing e-commerce product data.

## Core Features
- Product catalog management with SKU, pricing, and inventory tracking
- Excel import/export functionality for bulk operations
- Search and filtering capabilities
- Multi-shop product management
- Real-time data validation and filtering

## Target Users
- E-commerce managers
- Inventory specialists
- Product catalog administrators

## Key Business Logic
- Products are uniquely identified by `spec_id` (规格ID)
- System supports multi-shop environments
- Import process includes data validation against invalid IDs and enabled SKU codes
- Lazy loading for performance with large datasets