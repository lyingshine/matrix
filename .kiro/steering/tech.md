# Technology Stack

## Core Technologies
- **Python 3.x** - Main programming language
- **tkinter** - Base GUI framework
- **ttkbootstrap** - Modern themed tkinter widgets
- **SQLite** - Local database storage
- **pandas** - Excel file processing and data manipulation

## Key Dependencies
```python
import tkinter as tk
import ttkbootstrap as ttk
import pandas as pd
import sqlite3
import threading
```

## Database
- **SQLite** database (`products.db`)
- Single table architecture with indexed columns for performance
- Schema: `spec_id` (PRIMARY KEY), `sku`, `product_id`, `name`, `spec_name`, `price`, `quantity`, `shop`

## Common Commands
Since this is a standalone Python application:

```bash
# Run the application
python main.py

# Initialize database (handled automatically)
# Database file: products.db
```

## Architecture Patterns
- **Threading** for non-blocking database operations
- **Lazy loading** with pagination for large datasets
- **MVC-like separation** with database module
- **Event-driven GUI** with tkinter bindings