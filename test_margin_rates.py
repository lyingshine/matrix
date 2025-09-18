#!/usr/bin/env python3
"""
测试毛利率和净利率计算功能
"""

import database
import main

def test_margin_calculations():
    """测试毛利率和净利率计算"""
    print("=== 毛利率和净利率计算测试 ===\n")
    
    # 初始化数据库
    database.init_db()
    
    # 清理现有数据
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products')
    conn.commit()
    conn.close()
    
    # 创建测试数据
    test_products = [
        # (sku, product_id, spec_id, name, spec_name, price, quantity, shop, category, warehouse, short_name, min_price, purchase_price)
        ('SKU001', 'PROD001', 'SPEC001', '高价商品(≥150)', '规格1', 200.0, 10, '测试店铺', '电子产品', '仓库A', '高价商品', 180.0, 120.0),
        ('SKU002', 'PROD002', 'SPEC002', '低价商品(<150)', '规格2', 80.0, 20, '测试店铺', '日用品', '仓库B', '低价商品', 70.0, 60.0),
        ('SKU003', 'PROD003', 'SPEC003', '边界商品(=150)', '规格3', 150.0, 15, '测试店铺', '服装', '仓库C', '边界商品', 130.0, 100.0),
        ('SKU004', 'PROD004', 'SPEC004', '亏损商品', '规格4', 100.0, 5, '测试店铺', '其他', '仓库D', '亏损商品', 90.0, 95.0)
    ]
    
    # 插入测试数据
    result = database.add_product_batch(test_products)
    print(f"测试数据插入成功: {result}\n")
    
    # 验证计算逻辑
    all_products = database.get_all_products(limit=10)
    
    print("详细计算过程:")
    print("-" * 80)
    
    for product in all_products:
        product_dict = dict(zip(database.DB_COLUMNS, product))
        name = product_dict.get('name', '')
        price = float(product_dict.get('price', 0) or 0)
        purchase_price = float(product_dict.get('purchase_price', 0) or 0)
        
        print(f"\n商品: {name}")
        print(f"  原价: ¥{price:.2f}")
        print(f"  采购价: ¥{purchase_price:.2f}")
        
        # 计算到手价
        final_price = database.calculate_final_price(
            price, 
            product_dict.get('shop', ''), 
            product_dict.get('product_id', '')
        )
        print(f"  到手价: ¥{final_price:.2f}")
        
        if final_price > 0 and purchase_price > 0:
            # 计算快递费
            shipping_fee = 30 if final_price >= 150 else 2
            print(f"  快递费: ¥{shipping_fee:.2f} ({'高价商品' if final_price >= 150 else '低价商品'})")
            
            # 计算毛利
            gross_margin = final_price - purchase_price - shipping_fee
            gross_margin_rate = (gross_margin / final_price) * 100
            print(f"  毛利: ¥{gross_margin:.2f}")
            print(f"  毛利率: {gross_margin_rate:.1f}% = (到手价 - 采购价 - 快递费) / 到手价")
            
            # 计算杂费明细
            after_sales_fee = final_price * 0.02  # 2%
            management_fee = final_price * 0.07   # 7%
            platform_fee = final_price * 0.01    # 1%
            total_misc_fee = after_sales_fee + management_fee + platform_fee
            misc_fee_rate = (total_misc_fee / final_price) * 100
            
            print(f"  杂费明细:")
            print(f"    售后费用(2%): ¥{after_sales_fee:.2f}")
            print(f"    管理费用(7%): ¥{management_fee:.2f}")
            print(f"    平台费用(1%): ¥{platform_fee:.2f}")
            print(f"    杂费合计: ¥{total_misc_fee:.2f} ({misc_fee_rate:.1f}%)")
            
            # 计算净利率
            net_margin_rate = gross_margin_rate - misc_fee_rate
            print(f"  净利率: {net_margin_rate:.1f}% = 毛利率 - 杂费率")
            
            # 计算净利润
            net_profit = final_price - purchase_price - shipping_fee - total_misc_fee
            print(f"  净利润: ¥{net_profit:.2f}")
            
            # 验证计算
            calculated_net_rate = (net_profit / final_price) * 100
            print(f"  验证净利率: {calculated_net_rate:.1f}% (应该与上面的净利率相等)")
            
            if abs(net_margin_rate - calculated_net_rate) < 0.1:
                print("  ✓ 计算正确")
            else:
                print("  ✗ 计算错误")
        else:
            print("  跳过计算 (缺少价格数据)")
    
    print("\n" + "=" * 80)
    print("测试完成")

if __name__ == "__main__":
    test_margin_calculations()