import sqlite3
import json

# The order of columns used throughout the database logic
DB_COLUMNS = [
    'sku', 'product_id', 'spec_id', 'name', 
    'spec_name', 'price', 'quantity', 'shop',
    'category', 'warehouse', 'short_name', 'min_price', 'purchase_price'
]

# 优惠券表列定义
COUPON_COLUMNS = [
    'id', 'shop', 'coupon_type', 'amount', 'min_price', 
    'start_date', 'end_date', 'description', 'is_active', 'product_ids'
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
            shop TEXT,
            category TEXT,
            warehouse TEXT,
            short_name TEXT,
            min_price REAL,
            purchase_price REAL
        )
    ''')
    
    # 创建优惠券表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop TEXT NOT NULL,
            coupon_type TEXT NOT NULL,  -- 'instant' 立减券, 'threshold' 满减券, 'discount' 折扣券
            amount REAL NOT NULL,       -- 优惠金额或折扣比例
            min_price REAL DEFAULT 0,   -- 最低消费金额（满减券使用）
            start_date TEXT NOT NULL,   -- 开始日期
            end_date TEXT NOT NULL,     -- 结束日期
            description TEXT,           -- 优惠券描述
            is_active INTEGER DEFAULT 1, -- 是否启用
            product_ids TEXT            -- 指定商品ID列表，JSON格式，为空表示全店生效
        )
    ''')
    
    # 检查并添加 product_ids 列（用于数据库迁移）
    try:
        cursor.execute("SELECT product_ids FROM coupons LIMIT 1")
    except sqlite3.OperationalError:
        # 如果列不存在，添加它
        cursor.execute("ALTER TABLE coupons ADD COLUMN product_ids TEXT")
        print("数据库已更新：添加 product_ids 列")
    
    # 检查并添加新的商品字段
    new_columns = [
        ('category', 'TEXT'),
        ('warehouse', 'TEXT'), 
        ('short_name', 'TEXT'),
        ('min_price', 'REAL'),
        ('purchase_price', 'REAL')
    ]
    
    for column_name, column_type in new_columns:
        try:
            cursor.execute(f"SELECT {column_name} FROM products LIMIT 1")
        except sqlite3.OperationalError:
            # 如果列不存在，添加它
            cursor.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_type}")
            print(f"数据库已更新：添加 {column_name} 列")
    
    # 检查并添加新的商品字段
    new_columns = [
        ('category', 'TEXT'),
        ('warehouse', 'TEXT'), 
        ('short_name', 'TEXT'),
        ('min_price', 'REAL'),
        ('purchase_price', 'REAL')
    ]
    
    for column_name, column_type in new_columns:
        try:
            cursor.execute(f"SELECT {column_name} FROM products LIMIT 1")
        except sqlite3.OperationalError:
            # 如果列不存在，添加它
            cursor.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_type}")
            print(f"数据库已更新：添加 {column_name} 列")
    
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
    
    # 创建无效规格ID表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invalid_spec_ids (
            invalid_spec_id TEXT PRIMARY KEY
        )
    ''')
    
    # 创建启用SKU表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enabled_skus (
            enabled_sku TEXT PRIMARY KEY
        )
    ''')
    
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
             OR category LIKE ? OR warehouse LIKE ? OR short_name LIKE ?
             ORDER BY shop, name LIMIT ? OFFSET ?'''
    cursor.execute(sql, (search_term, search_term, search_term, search_term, 
                        search_term, search_term, search_term, limit, offset))
    products = cursor.fetchall()
    conn.close()
    return products

def search_products_count(query):
    """Gets the total count of products for a search query."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f'%{query}%'
    sql = f'''SELECT COUNT(*) FROM products 
             WHERE sku LIKE ? OR name LIKE ? OR spec_name LIKE ? OR product_id LIKE ?
             OR category LIKE ? OR warehouse LIKE ? OR short_name LIKE ?'''
    cursor.execute(sql, (search_term, search_term, search_term, search_term,
                        search_term, search_term, search_term))
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

def calculate_final_price(price, shop, product_id=None):
    """计算商品的到手价（应用最优优惠券）"""
    if not price or price <= 0:
        return price
        
    coupons = get_active_coupons_by_shop(shop)
    if not coupons:
        return price
    
    best_price = price
    
    for coupon in coupons:
        coupon_dict = dict(zip(COUPON_COLUMNS, coupon))
        
        # 检查优惠券是否适用于该商品
        if not is_coupon_applicable(coupon_dict, product_id):
            continue
        
        # 根据优惠券类型计算价格
        final_price = apply_coupon_discount(price, coupon_dict)
        if final_price is not None:
            best_price = min(best_price, final_price)
    
    return round(best_price, 2)

def is_coupon_applicable(coupon_dict, product_id):
    """检查优惠券是否适用于指定商品（按货品ID匹配）"""
    
    # 如果没有指定商品，则全店生效
    product_ids_str = coupon_dict.get('product_ids')
    if not product_ids_str:
        return True
    
    # 如果指定了商品，检查当前商品的货品ID是否在列表中
    try:
        selected_product_ids = json.loads(product_ids_str)
        return product_id in selected_product_ids if product_id else False
    except (json.JSONDecodeError, TypeError):
        return True  # 如果解析失败，默认全店生效

def apply_coupon_discount(price, coupon_dict):
    """应用优惠券折扣"""
    coupon_type = coupon_dict['coupon_type']
    amount = coupon_dict['amount']
    min_price = coupon_dict.get('min_price', 0)
    
    if coupon_type == 'instant':
        # 立减券：直接减去面额
        return max(0, price - amount)
    
    elif coupon_type == 'threshold':
        # 满减券：价格大于某个数值才能使用
        if price >= min_price:
            return max(0, price - amount)
        else:
            return None  # 不满足使用条件
    
    elif coupon_type == 'discount':
        # 折扣券：价格乘以折扣（amount为折扣比例，如0.8表示8折）
        return price * amount
    
    return None

def get_all_shops():
    """获取所有店铺列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT shop FROM products WHERE shop IS NOT NULL AND shop != "" ORDER BY shop')
    shops = [row[0] for row in cursor.fetchall()]
    conn.close()
    return shops

def get_products_by_shop(shop):
    """获取指定店铺的所有有效且启用的商品（按货品ID去重）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取无效的规格ID列表
    cursor.execute('SELECT DISTINCT invalid_spec_id FROM invalid_spec_ids')
    invalid_ids = set(row[0].lower() for row in cursor.fetchall() if row[0])
    
    # 获取启用的规格编码列表
    cursor.execute('SELECT DISTINCT enabled_sku FROM enabled_skus')
    enabled_codes = set(row[0] for row in cursor.fetchall() if row[0])
    
    # 获取该店铺的所有商品
    cursor.execute('''
        SELECT DISTINCT product_id, name, spec_id, sku
        FROM products 
        WHERE shop = ? AND product_id IS NOT NULL AND product_id != ""
    ''', (shop,))
    all_products = cursor.fetchall()
    
    # 筛选有效且启用的商品
    valid_products = []
    seen_product_ids = set()
    
    for product_id, name, spec_id, sku in all_products:
        # 检查规格ID是否有效
        if spec_id and spec_id.lower() in invalid_ids:
            continue
            
        # 检查SKU是否启用（*表示通配符，始终启用）
        if sku and sku != '*' and sku not in enabled_codes:
            continue
            
        # 按货品ID去重
        if product_id not in seen_product_ids:
            valid_products.append((product_id, name))
            seen_product_ids.add(product_id)
    
    # 按名称排序
    valid_products.sort(key=lambda x: x[1])
    
    conn.close()
    return valid_products

def update_invalid_spec_ids(invalid_ids):
    """更新无效规格ID列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 清空现有数据
    cursor.execute('DELETE FROM invalid_spec_ids')
    
    # 插入新数据
    if invalid_ids:
        cursor.executemany('INSERT INTO invalid_spec_ids (invalid_spec_id) VALUES (?)', 
                          [(id_,) for id_ in invalid_ids])
    
    conn.commit()
    conn.close()

def update_enabled_skus(enabled_skus):
    """更新启用SKU列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 清空现有数据
    cursor.execute('DELETE FROM enabled_skus')
    
    # 插入新数据
    if enabled_skus:
        cursor.executemany('INSERT INTO enabled_skus (enabled_sku) VALUES (?)', 
                          [(sku,) for sku in enabled_skus])
    
    conn.commit()
    conn.close()

def get_coupon_stats():
    """获取优惠券统计数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 总优惠券数
    cursor.execute('SELECT COUNT(*) FROM coupons')
    total_coupons = cursor.fetchone()[0]
    
    # 启用中的优惠券数
    cursor.execute('SELECT COUNT(*) FROM coupons WHERE is_active = 1')
    active_coupons = cursor.fetchone()[0]
    
    # 已过期的优惠券数（简单判断：结束日期小于今天）
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM coupons WHERE end_date < ?', (today,))
    expired_coupons = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total_coupons,
        'active': active_coupons,
        'expired': expired_coupons
    }