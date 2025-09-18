import sqlite3

# The order of columns used throughout the database logic
DB_COLUMNS = [
    'sku', 'product_id', 'spec_id', 'name', 
    'spec_name', 'price', 'quantity', 'shop'
]

def get_db_connection():
    """Creates a connection to the database."""
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the products table and indexes if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Using TEXT for all IDs as they might be non-numeric
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            spec_id TEXT PRIMARY KEY,
            sku TEXT,
            product_id TEXT,
            name TEXT NOT NULL,
            spec_name TEXT,
            price REAL,
            quantity INTEGER,
            shop TEXT
        )
    ''')
    # Add indexes to speed up searching
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON products (name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_name ON products (spec_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_id ON products (product_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sku ON products (sku)') # Add index for sku
    
    conn.commit()
    conn.close()

def add_product_batch(products):
    """Adds or replaces a batch of products, returning stats on the operation."""
    if not products:
        return {'added': 0, 'updated': 0}

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM products')
    initial_row_count = cursor.fetchone()[0]

    placeholders = ', '.join(['?'] * len(DB_COLUMNS))
    sql = f'''INSERT OR REPLACE INTO products ({", ".join(DB_COLUMNS)}) 
             VALUES ({placeholders})'''
    cursor.executemany(sql, products)
    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM products')
    final_row_count = cursor.fetchone()[0]
    conn.close()

    net_rows_added = final_row_count - initial_row_count
    rows_processed = len(products)
    
    rows_updated = max(0, rows_processed - net_rows_added)

    return {'added': net_rows_added, 'updated': rows_updated}

def get_all_products(limit=50, offset=0):
    """Retrieves a paginated list of all products from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT {", ".join(DB_COLUMNS)} FROM products ORDER BY shop, name LIMIT ? OFFSET ?', (limit, offset))
    products = cursor.fetchall()
    conn.close()
    return products

def get_all_products_count():
    """Gets the total count of products."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM products')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def search_products(query, limit=50, offset=0):
    """Searches for products by SKU or name with pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f'%{query}%'
    sql = f'''SELECT {", ".join(DB_COLUMNS)} FROM products 
             WHERE sku LIKE ? OR name LIKE ? OR spec_name LIKE ? OR product_id LIKE ?
             ORDER BY shop, name LIMIT ? OFFSET ?'''
    cursor.execute(sql, (search_term, search_term, search_term, search_term, limit, offset))
    products = cursor.fetchall()
    conn.close()
    return products

def search_products_count(query):
    """Gets the total count of products for a search query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f'%{query}%'
    sql = f'''SELECT COUNT(*) FROM products 
             WHERE sku LIKE ? OR name LIKE ? OR spec_name LIKE ? OR product_id LIKE ?'''
    cursor.execute(sql, (search_term, search_term, search_term, search_term))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_product_by_spec_id(spec_id):
    """Deletes a product from the database by spec_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE spec_id = ?', (spec_id,))
    conn.commit()
    conn.close()

def get_product_by_spec_id(spec_id):
    """Retrieves a single product by its spec_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT {", ".join(DB_COLUMNS)} FROM products WHERE spec_id = ?', (spec_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def add_product(product_data):
    """Adds a new product to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        placeholders = ', '.join(['?'] * len(DB_COLUMNS))
        sql = f'''INSERT INTO products ({", ".join(DB_COLUMNS)}) 
                 VALUES ({placeholders})'''
        # Ensure data is in the correct order
        ordered_data = [product_data.get(col) for col in DB_COLUMNS]
        cursor.execute(sql, ordered_data)
        conn.commit()
    finally:
        conn.close()

def update_product(product_data):
    """Updates an existing product."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_cols = [col for col in DB_COLUMNS if col != 'spec_id']
    set_clause = ", ".join([f"{col} = ?" for col in update_cols])
    sql = f'UPDATE products SET {set_clause} WHERE spec_id = ?'
    
    # Ensure data is in the correct order for SET clause, with spec_id at the end for WHERE
    ordered_values = [product_data.get(col) for col in update_cols] + [product_data.get('spec_id')]
    
    cursor.execute(sql, ordered_values)
    conn.commit()
    conn.close()