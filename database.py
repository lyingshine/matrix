import sqlite3

# The order of columns used throughout the database logic
DB_COLUMNS = [
    'sku', 'product_id', 'spec_id', 'name', 
    'spec_name', 'price', 'quantity', 'shop'
]

# 优惠券表列定义
COUPON_COLUMNS = [
    'id', 'shop', 'coupon_type', 'amount', 'min_price', 
    'start_date', 'end_date', 'description', 'is_active'
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
    
    # 创建商品表
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
    
    # 创建优惠券表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop TEXT NOT NULL,
            coupon_type TEXT NOT NULL,  -- 'fixed' 固定金额, 'percent' 百分比
            amount REAL NOT NULL,       -- 优惠金额或百分比
            min_price REAL DEFAULT 0,   -- 最低消费金额
            start_date TEXT NOT NULL,   -- 开始日期
            end_date TEXT NOT NULL,     -- 结束日期
            description TEXT,           -- 优惠券描述
            is_active INTEGER DEFAULT 1 -- 是否启用
        )
    ''')
    
    # Add indexes to speed up searching
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON products (name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_name ON products (spec_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_id ON products (product_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sku ON products (sku)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shop ON products (shop)')
    
    # 优惠券表索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coupon_shop ON coupons (shop)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coupon_active ON coupons (is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_coupon_dates ON coupons (start_date, end_date)')
    
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

# ==================== 优惠券相关函数 ====================

def add_coupon(coupon_data):
    """添加新优惠券"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    columns = [col for col in COUPON_COLUMNS if col != 'id']  # 排除自增ID
    placeholders = ', '.join(['?'] * len(columns))
    sql = f'''INSERT INTO coupons ({", ".join(columns)}) VALUES ({placeholders})'''
    
    ordered_data = [coupon_data.get(col) for col in columns]
    cursor.execute(sql, ordered_data)
    conn.commit()
    coupon_id = cursor.lastrowid
    conn.close()
    return coupon_id

def get_all_coupons():
    """获取所有优惠券"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT {", ".join(COUPON_COLUMNS)} FROM coupons ORDER BY shop, start_date DESC')
    coupons = cursor.fetchall()
    conn.close()
    return coupons

def get_active_coupons_by_shop(shop):
    """获取指定店铺的有效优惠券"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取当前日期
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    sql = f'''SELECT {", ".join(COUPON_COLUMNS)} FROM coupons 
             WHERE shop = ? AND is_active = 1 
             AND start_date <= ? AND end_date >= ?
             ORDER BY amount DESC'''
    
    cursor.execute(sql, (shop, current_date, current_date))
    coupons = cursor.fetchall()
    conn.close()
    return coupons

def update_coupon(coupon_data):
    """更新优惠券"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    update_cols = [col for col in COUPON_COLUMNS if col != 'id']
    set_clause = ", ".join([f"{col} = ?" for col in update_cols])
    sql = f'UPDATE coupons SET {set_clause} WHERE id = ?'
    
    ordered_values = [coupon_data.get(col) for col in update_cols] + [coupon_data.get('id')]
    cursor.execute(sql, ordered_values)
    conn.commit()
    conn.close()

def delete_coupon(coupon_id):
    """删除优惠券"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM coupons WHERE id = ?', (coupon_id,))
    conn.commit()
    conn.close()

def get_coupon_by_id(coupon_id):
    """根据ID获取优惠券"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT {", ".join(COUPON_COLUMNS)} FROM coupons WHERE id = ?', (coupon_id,))
    coupon = cursor.fetchone()
    conn.close()
    return coupon

def calculate_final_price(price, shop):
    """计算商品的到手价（应用最优优惠券）"""
    if not price or price <= 0:
        return price
        
    coupons = get_active_coupons_by_shop(shop)
    if not coupons:
        return price
    
    best_price = price
    
    for coupon in coupons:
        coupon_dict = dict(zip(COUPON_COLUMNS, coupon))
        
        # 检查是否满足最低消费
        if price < coupon_dict['min_price']:
            continue
            
        if coupon_dict['coupon_type'] == 'fixed':
            # 固定金额优惠
            final_price = max(0, price - coupon_dict['amount'])
        elif coupon_dict['coupon_type'] == 'percent':
            # 百分比优惠
            final_price = price * (1 - coupon_dict['amount'] / 100)
        else:
            continue
            
        best_price = min(best_price, final_price)
    
    return round(best_price, 2)