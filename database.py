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
    """Initializes the database and creates the products table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Using TEXT for all IDs as they might be non-numeric
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            product_id TEXT,
            spec_id TEXT,
            name TEXT NOT NULL,
            spec_name TEXT,
            price REAL,
            quantity INTEGER,
            shop TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_product_batch(products):
    """Adds or replaces a batch of products in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ', '.join(['?'] * len(DB_COLUMNS))
    sql = f'''INSERT OR REPLACE INTO products ({", ".join(DB_COLUMNS)}) 
             VALUES ({placeholders})'''
    cursor.executemany(sql, products)
    conn.commit()
    conn.close()

def get_all_products():
    """Retrieves all products from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT {", ".join(DB_COLUMNS)} FROM products ORDER BY shop, name')
    products = cursor.fetchall()
    conn.close()
    return products

def search_products(query):
    """Searches for products by SKU or name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f'%{query}%'
    # Search across more fields for better usability
    sql = f'''SELECT {", ".join(DB_COLUMNS)} FROM products 
             WHERE sku LIKE ? OR name LIKE ? OR spec_name LIKE ? OR product_id LIKE ?
             ORDER BY shop, name'''
    cursor.execute(sql, (search_term, search_term, search_term, search_term))
    products = cursor.fetchall()
    conn.close()
    return products

def delete_product(sku):
    """Deletes a product from the database by SKU."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE sku = ?', (sku,))
    conn.commit()
    conn.close()

def get_product_by_sku(sku):
    """Retrieves a single product by its SKU."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT {", ".join(DB_COLUMNS)} FROM products WHERE sku = ?', (sku,))
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
    
    update_cols = [col for col in DB_COLUMNS if col != 'sku']
    set_clause = ", ".join([f"{col} = ?" for col in update_cols])
    sql = f'UPDATE products SET {set_clause} WHERE sku = ?'
    
    # Ensure data is in the correct order for SET clause, with SKU at the end for WHERE
    ordered_values = [product_data.get(col) for col in update_cols] + [product_data.get('sku')]
    
    cursor.execute(sql, ordered_values)
    conn.commit()
    conn.close()
