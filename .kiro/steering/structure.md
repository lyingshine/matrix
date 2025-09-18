# Project Structure

## File Organization
```
├── main.py           # Main application entry point and GUI logic
├── database.py       # Database operations and schema management
├── products.db       # SQLite database file (auto-generated)
├── README.md         # Project documentation
├── .gitignore        # Git ignore rules
└── __pycache__/      # Python bytecode cache
```

## Code Organization

### main.py
- **App class** - Main application window and UI management
- **ProductEditorWindow class** - Modal dialog for adding/editing products
- **Constants** - UI configuration, column mappings, pagination settings
- **Event handlers** - Search, import, delete, edit operations
- **Threading logic** - Non-blocking database operations

### database.py
- **DB_COLUMNS** - Canonical column order for database operations
- **Connection management** - SQLite connection handling
- **CRUD operations** - Create, read, update, delete functions
- **Search functionality** - Paginated search with count operations
- **Batch operations** - Efficient bulk import/update

## Key Conventions
- **Chinese UI text** - All user-facing text in Chinese
- **Threading pattern** - Database operations run in background threads
- **Pagination** - PAGE_SIZE = 50 for lazy loading
- **Error handling** - Try-catch with user-friendly error messages
- **State management** - Busy states prevent concurrent operations

## Database Schema
Primary table: `products`
- Indexed columns: `name`, `spec_name`, `product_id`, `sku`
- Primary key: `spec_id`
- Data types: TEXT for IDs, REAL for price, INTEGER for quantity