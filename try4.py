import tkinter as tk
import customtkinter as ctk
import customtkinter
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import sqlite3
import os
import shutil 
from datetime import datetime 

import tempfile
import webbrowser
#------ใบเสร็จอัตโนมัติ-------
import random
import string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- ค่าคงที่/การตั้งค่าฐานข้อมูลและดัชนีข้อมูล ---
DB_NAME = "user_data.db" 
MENU_IMG_FOLDER = "menu_images" 
SLIP_IMG_FOLDER = "uploaded_slips"

# --- ตัวแปร Global สำหรับตะกร้าสินค้าและโต๊ะ ---
user_cart = {} 
current_table_number = None 
# ดัชนีสำหรับเข้าถึงข้อมูล Order (Tuple)
ORDER_ID_IDX = 0
ORDER_USER_ID_IDX = 1
ORDER_TABLE_NUM_IDX = 2
ORDER_TIME_IDX = 3
ORDER_STATUS_IDX = 4
ORDER_TOTAL_IDX = 5
ORDER_SLIP_PATH_IDX = 6
ORDER_NO_IDX = 7
# ดัชนีสำหรับเข้าถึงข้อมูลผู้ใช้ (Tuple)
USER_ID_IDX = 0
USERNAME_IDX = 1
PASSWORD_IDX = 2 
FIRST_NAME_IDX = 3
LAST_NAME_IDX = 4
PHONE_NUMBER_IDX = 5
EMAIL_IDX = 6
BIRTH_DATE_IDX = 7
PROFILE_PIC_PATH_IDX = 8 

# ดัชนีสำหรับเข้าถึงข้อมูลเมนู (Tuple)
MENU_ID_IDX = 0
MENU_NAME_IDX = 1
MENU_PRICE_IDX = 2
MENU_AMOUNT_IDX = 3
MENU_TYPE_IDX = 4
MENU_IMG_PATH_IDX = 5

# --- ฟังก์ชันสำหรับฐานข้อมูล SQLite ---


def initialize_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                     username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, first_name TEXT, last_name TEXT, phone_number TEXT, 
                                     email TEXT, birth_date TEXT, profile_pic_path TEXT DEFAULT '')
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                     name TEXT NOT NULL, price REAL NOT NULL, amount INTEGER NOT NULL, type TEXT NOT NULL, img_path TEXT DEFAULT '')
    """)
    
    # --- (MODIFIED) แก้ไขตาราง orders ตรงนี้ ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            table_number INTEGER NOT NULL,
            order_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'In the Kitchen', 
            total_price REAL NOT NULL,
            slip_path TEXT,
            order_no TEXT UNIQUE,  -- <--- (1) เพิ่มคอลัมน์นี้เข้ามาในคำสั่ง CREATE
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # --- (END MODIFIED) ---
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_id INTEGER NOT NULL,
            menu_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_item REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (menu_id) REFERENCES menu (id)
        )
    """)
    
    try:
            cursor.execute("ALTER TABLE orders ADD COLUMN order_no TEXT")
            print("--- Database Update: Step 1/2 - Added 'order_no' column. ---")
    except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("--- Database Check: Step 1/2 - 'order_no' column already exists. ---")
                pass 
            else:
                print(f"--- Database Error (Step 1): {e} ---") 


    try:

            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_order_no ON orders(order_no)")
            print("--- Database Update: Step 2/2 - Created UNIQUE index on 'order_no'. ---")
    except Exception as e:
            print(f"--- Database Error (Step 2): {e} ---") 

    conn.commit(); conn.close()
    if not os.path.exists(MENU_IMG_FOLDER): os.makedirs(MENU_IMG_FOLDER)
    if not os.path.exists(SLIP_IMG_FOLDER): os.makedirs(SLIP_IMG_FOLDER)


def register_pdf_fonts(font_paths):
    """
    ลงทะเบียนฟอนต์ภาษาไทยสำหรับ ReportLab
    """
    try:
        pdfmetrics.registerFont(TTFont('Thai-Regular', font_paths['font_regular']))
        pdfmetrics.registerFont(TTFont('Thai-Bold', font_paths['font_bold']))
        print("Fonts registered successfully for PDF generation.")
    except Exception as e:
        print(f"Error registering fonts: {e}")
        messagebox.showerror("Font Error", f"ไม่พบไฟล์ฟอนต์สำหรับ PDF: {e}\nกรุณาตรวจสอบ Path ใน image_paths")

def insert_user(username, password, first_name, last_name, phone_number, email, birth_date):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, first_name, last_name, phone_number, email, birth_date, profile_pic_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                       (username, password, first_name, last_name, phone_number, email, birth_date, ''))
        conn.commit(); conn.close(); return True
    except sqlite3.IntegrityError: return False
    except Exception as e: print(f"Error inserting user: {e}"); return False


def check_login(username, password):
    if username == "adminja" and password == "12345678": return (0, "adminja", "12345678", "Admin", "User", "", "", "", "") 
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user_record = cursor.fetchone(); conn.close(); return user_record


def update_user_profile(user_id, first_name, last_name, phone_number, email, birth_date, profile_pic_path):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("UPDATE users SET first_name = ?, last_name = ?, phone_number = ?, email = ?, birth_date = ?, profile_pic_path = ? WHERE id = ?", 
                       (first_name, last_name, phone_number, email, birth_date, profile_pic_path, user_id))
        conn.commit(); cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)); updated_user_data = cursor.fetchone(); conn.close(); return updated_user_data
    except Exception as e: print(f"Error updating user profile: {e}"); return None

def check_user_by_email_and_phone(email, phone_number):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND phone_number = ?", (email, phone_number))
    user_record = cursor.fetchone(); conn.close(); return user_record

def update_password(user_id, new_password):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
        conn.commit(); conn.close(); return True
    except Exception as e: print(f"Error updating password: {e}"); return False

def add_menu_item(name, price, amount, menu_type, img_path):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("INSERT INTO menu (name, price, amount, type, img_path) VALUES (?, ?, ?, ?, ?)", (name, price, amount, menu_type, img_path))
        conn.commit(); new_id = cursor.lastrowid; conn.close(); return new_id
    except Exception as e: print(f"Error adding menu item: {e}"); return None

def get_all_menu_items(menu_type=None):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    if menu_type: cursor.execute("SELECT * FROM menu WHERE type = ?", (menu_type,))
    else: cursor.execute("SELECT * FROM menu")
    items = cursor.fetchall(); conn.close(); return items

def update_menu_item(menu_id, name, price, amount, menu_type, img_path):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("UPDATE menu SET name = ?, price = ?, amount = ?, type = ?, img_path = ? WHERE id = ?", (name, price, amount, menu_type, img_path, menu_id))
        conn.commit(); conn.close(); return True
    except Exception as e: print(f"Error updating menu item: {e}"); return False

def delete_menu_item(menu_id):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("DELETE FROM menu WHERE id = ?", (menu_id,)); conn.commit(); conn.close(); return True
    except Exception as e: print(f"Error deleting menu item: {e}"); return False


def create_new_order(user_id, table_number, total_price, slip_path, cart_items):
    """
    สร้างออเดอร์ใหม่และบันทึกรายการสินค้าลงฐานข้อมูล
    (MODIFIED: เพิ่มการสร้างและบันทึก order_no)
    (MODIFIED: เพิ่มการหักสต็อกสินค้า)
    """
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        status = "In the Kitchen" 
        
        order_no = ""
        while True:
            prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
            suffix = ''.join(random.choices(string.digits, k=6))
            order_no = f"{prefix}{suffix}"
            
            
            cursor.execute("SELECT id FROM orders WHERE order_no = ?", (order_no,))
            if cursor.fetchone() is None:
                break 


        cursor.execute(

            "INSERT INTO orders (user_id, table_number, order_time, status, total_price, slip_path, order_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, table_number, order_time, status, total_price, slip_path, order_no)
        )
        order_id = cursor.lastrowid 
        
        if not order_id:
            raise Exception("ไม่สามารถสร้างออเดอร์หลักได้")


        for item_id, cart_info in cart_items.items():
            item_data = cart_info['item_data']
            quantity = cart_info['quantity']
            
            menu_name = item_data[MENU_NAME_IDX]
            price = item_data[MENU_PRICE_IDX]
            
            # 1. เพิ่มรายการสินค้าลงใน Order
            cursor.execute(
                "INSERT INTO order_items (order_id, menu_id, menu_name, quantity, price_per_item) VALUES (?, ?, ?, ?, ?)",
                (order_id, item_id, menu_name, quantity, price)
            )
            
            # --- (NEW) 2. หักสต็อกสินค้าออกจากตาราง menu ---
            cursor.execute(
                "UPDATE menu SET amount = amount - ? WHERE id = ?",
                (quantity, item_id)
            )
            # --- (END NEW) ---
                    
        conn.commit()
        conn.close()
        return order_id 
        
    except Exception as e:
        print(f"Error creating new order: {e}")
        conn.rollback() 
        conn.close()
        return None
    

def get_active_order_for_table(user_id, table_number):
    """
    ดึงออเดอร์ล่าสุดของโต๊ะนี้ที่ยังไม่เสิร์ฟ
    """
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM orders WHERE user_id = ? AND table_number = ? AND status != 'Served' ORDER BY order_time DESC LIMIT 1",
            (user_id, table_number)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting active order: {e}")
        return None
    
def get_all_orders_for_table(user_id, table_number):
    """
    ดึงออเดอร์ทั้งหมดสำหรับโต๊ะนี้ (ทั้งที่กำลังทำและเสิร์ฟแล้ว)
    เรียงจากใหม่สุดไปเก่าสุด
    """
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM orders WHERE user_id = ? AND table_number = ? ORDER BY order_time DESC",
            (user_id, table_number)
        )
        results = cursor.fetchall() 
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting all orders: {e}")
        return []
    
def get_order_details(order_id):
    """
    ดึงข้อมูลออเดอร์หลัก (จากตาราง orders)
    """
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting order details: {e}")
        return None

def get_active_tables():
    """
    ดึงหมายเลขโต๊ะที่มีออเดอร์สถานะ 'In the Kitchen' ทั้งหมด
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT table_number FROM orders WHERE status = 'In the Kitchen'")
        # .fetchall() จะให้ [ (1,), (3,) ]
        # เราจึงใช้ list comprehension แปลงเป็น [1, 3]
        active_tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return active_tables
    except Exception as e:
        print(f"Error getting active tables: {e}")
        return []

def get_active_orders_for_table(table_number):
    """
    ดึงออเดอร์ทั้งหมดของโต๊ะที่กำหนด ที่ยังมีสถานะ 'In the Kitchen'
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM orders WHERE table_number = ? AND status = 'In the Kitchen' ORDER BY order_time ASC",
            (table_number,)
        )
        orders = cursor.fetchall()
        conn.close()
        return orders
    except Exception as e:
        print(f"Error getting active orders for table {table_number}: {e}")
        return []

def update_order_status(order_id, new_status):
    """
    อัปเดตสถานะของออเดอร์ (เช่น 'Served', 'Cancelled')
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating order status: {e}")
        return False
    

def get_order_items(order_id):
    """
    ดึงรายการสินค้าทั้งหมดของออเดอร์ (จากตาราง order_items)
    """
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("SELECT menu_name, quantity, price_per_item FROM order_items WHERE order_id = ?", (order_id,))
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting order items: {e}")
        return []

profile_photo_cache = {}; table_profile_photo_cache = {}

def get_sales_report(report_type, year, month, day, menu_type):
    """
    ดึงข้อมูลยอดขายตามเงื่อนไขที่กำหนด
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    base_query = """
        SELECT
            oi.menu_name,
            m.type,
            SUM(oi.quantity) AS total_sold,
            SUM(oi.quantity * oi.price_per_item) AS total_revenue
        FROM order_items AS oi
        JOIN orders AS o ON oi.order_id = o.id
        JOIN menu AS m ON oi.menu_id = m.id
        WHERE o.status = 'Served'
    """
    
    params = []
    
    # 1. ฟิลเตอร์ตามวันที่
    if report_type == 'Daily':
        base_query += " AND strftime('%Y-%m-%d', o.order_time) = ?"
        params.append(f"{year:04d}-{month:02d}-{day:02d}")
    elif report_type == 'Monthly':
        base_query += " AND strftime('%Y-%m', o.order_time) = ?"
        params.append(f"{year:04d}-{month:02d}")
    elif report_type == 'Yearly':
        base_query += " AND strftime('%Y', o.order_time) = ?"
        params.append(f"{year:04d}")
        
    # 2. ฟิลเตอร์ตามประเภทเมนู
    if menu_type != 'All':
        base_query += " AND m.type = ?"
        params.append(menu_type)
        
    # 3. Grouping
    base_query += " GROUP BY oi.menu_id, oi.menu_name, m.type ORDER BY total_revenue DESC"
    
    try:
        cursor.execute(base_query, tuple(params))
        results = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching sales report: {e}")
        results = []
    finally:
        conn.close()
        
    return results


def load_and_display_profile_pic(container, pic_path, default_img_key, x, y, size=50):
    global profile_photo_cache
    if 'profile_pic_label' in profile_photo_cache: profile_photo_cache['profile_pic_label'].destroy()
    photo = None
    target_path = pic_path if pic_path and os.path.exists(pic_path) else image_paths.get(default_img_key)
    if target_path and os.path.exists(target_path):
        try:
            original_image = Image.open(target_path); resized_image = original_image.resize((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized_image)
        except Exception: pass 
    if photo:
        label = tk.Label(container, image=photo, bd=0, highlightthickness=0, bg="#bbd106")
        label.image = photo; label.place(x=x, y=y, width=size, height=size)
        profile_photo_cache['profile_pic_label'] = label; profile_photo_cache['current_photo'] = photo
        return label
    return None

def load_and_display_profile_pic_on_button(pic_path, default_img_key, size=35):
    
    target_path = pic_path if pic_path and os.path.exists(pic_path) else image_paths.get(default_img_key)
    
    if not target_path or not os.path.exists(target_path):
         target_path = image_paths.get('default_profile_pic_small') 
         if not target_path or not os.path.exists(target_path):
              return None 
    
    try:
        original_image = Image.open(target_path).convert("RGBA")
        resized_image = original_image.resize((size, size), Image.Resampling.LANCZOS)
        
        ctk_photo = customtkinter.CTkImage(
            light_image=resized_image,
            dark_image=resized_image,
            size=(size, size)
        )
        return ctk_photo
    except Exception as e:
        print(f"Error loading button profile pic: {e}")
        return None

# --- หน้า About และ Nav Button ---

def create_about_page(root, bg_images, prev_page_func):
    for widget in root.winfo_children(): widget.destroy()
    if 'about' not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพ 'about'"); return
    
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['about'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    customtkinter.CTkButton(
        background_label, 
        text="Back", 
        font=("Arial", 18, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106",  
        hover_color="#a0b507", 
        border_width=0,
        corner_radius=10,      
        width=145,            
        height=38,            
        command=prev_page_func
    ).place(x=654, y=739) 


def create_nav_button(parent_widget, bg_images, current_page_func): 
    about_button = customtkinter.CTkButton(
        parent_widget, 
        text="•\n•\n•", 
        font=("Arial", 12, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106",
        hover_color="#1f8b3f", 
        border_width=0,
        corner_radius=5,
        width=25,
        height=43,
        command=lambda: create_about_page(root, bg_images, current_page_func)
    )
    about_button.place(x=1500, y=767)


def check_password_strength(password):
    """
    ตรวจสอบความแข็งแรงของรหัสผ่านตามเงื่อนไข:
    1. ความยาวอย่างน้อย 8 ตัวอักษร
    2. มีตัวอักษรภาษาอังกฤษตัวพิมพ์ใหญ่ (A-Z) อย่างน้อย 1 ตัว
    3. มีตัวเลข (0-9) อย่างน้อย 1 ตัว
    
    คืนค่า: "OK" ถ้าผ่าน, หรือ ข้อความ error ถ้าไม่ผ่าน
    """
    if len(password) < 8:
        return "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร"
        
    if not any(c.isupper() for c in password):
        return "รหัสผ่านต้องมีตัวอักษรภาษาอังกฤษตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว"
            
    if not any(c.isdigit() for c in password):
        return "รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว"  
    return "OK"

# -----------------------------------------------
# --- หน้า Admin (Order, Edit Menu, Add/Edit Item) ---
# -----------------------------------------------

def create_admin_edit_menu_page(root, bg_images, menu_data, current_category):
    for widget in root.winfo_children():
        widget.destroy()
        
    if 'editmenu' not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'editmenu'")
        return
        
    background_label = ctk.CTkLabel(root, image=bg_images['editmenu'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    menu_id = menu_data[MENU_ID_IDX]
    current_img_path = menu_data[MENU_IMG_PATH_IDX]
    new_img_path = tk.StringVar(value=current_img_path)

    img_size = int(150*1.604)
    img_x, img_y = int(373*1.604), int(145*1.546)
    img_label = None
    
    def display_menu_img(path):
        nonlocal img_label
        if img_label:
            img_label.destroy()
        photo = None
        target_path = path if path and os.path.exists(path) else image_paths.get('default_menu_img')

        if target_path and os.path.exists(target_path):
            original_image = Image.open(target_path)
            resized_image = original_image.resize((img_size, img_size), Image.Resampling.LANCZOS)

            photo = customtkinter.CTkImage(light_image=resized_image, 
                                           dark_image=resized_image, 
                                           size=(img_size, img_size))

        if photo:

            img_label = ctk.CTkLabel(root, image=photo, text="", fg_color="white", corner_radius=0,width=img_size, height=img_size)
            img_label.place(x=img_x, y=img_y)

    display_menu_img(current_img_path)

    def browse_image():
        file_path = filedialog.askopenfilename(title="เลือกรูปภาพเมนู", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            new_img_path.set(file_path)
            display_menu_img(file_path)

    # ใช้ ctk.CTkButton
    ctk.CTkButton(root, 
                text="Browse", 
                font=("Arial", 15, "bold"), 
                text_color="#003728", 
                fg_color="#bbd106", 
                hover_color="#a0b507",
                width=112, height=39, 
                command=browse_image
    ).place(x=858, y=410)

    name_var = tk.StringVar(value=menu_data[MENU_NAME_IDX])
    price_var = tk.StringVar(value=str(menu_data[MENU_PRICE_IDX]))
    amount_var = tk.StringVar(value=str(menu_data[MENU_AMOUNT_IDX]))
    type_var = tk.StringVar(value=menu_data[MENU_TYPE_IDX])
    
    # สไตล์สำหรับ ctk.CTkEntry
    entry_font = ("Arial", 18)
    entry_fg_color = "#ebf3c7"
    entry_border_width = 1
    entry_corner_radius = 0 

    
    ctk.CTkLabel(root, text="Name :", font=("Arial", 18, "bold"), text_color="#003728", fg_color="white", anchor="w").place(x=420, y=479)
    
    ctk.CTkEntry(root, 
                textvariable=name_var, 
                font=entry_font, 
                fg_color=entry_fg_color, 
                border_width=entry_border_width,
                corner_radius=entry_corner_radius,
                width=552, height=31
    ).place(x=510, y=479)

    ctk.CTkLabel(root, text="Price :", font=("Arial", 18, "bold"), text_color="#003728", fg_color="white", anchor="w").place(x=420, y=526)
    ctk.CTkEntry(root, 
                textvariable=price_var, 
                font=entry_font, 
                fg_color=entry_fg_color,
                border_width=entry_border_width,
                corner_radius=entry_corner_radius,
                width=561, height=31
    ).place(x=502, y=526)

    ctk.CTkLabel(root, text="Amount :", font=("Arial", 18, "bold"), text_color="#003728", fg_color="white", anchor="w").place(x=420, y=572)
    ctk.CTkEntry(root, 
                textvariable=amount_var, 
                font=entry_font, 
                fg_color=entry_fg_color,
                border_width=entry_border_width,
                corner_radius=entry_corner_radius,
                width=515, height=31
    ).place(x=549, y=572)

    ctk.CTkLabel(root, text="Food Type :", font=("Arial", 18, "bold"), text_color="#003728", fg_color="white", anchor="w").place(x=420, y=619)
    
    type_dropdown = ctk.CTkComboBox(root, 
                                    variable=type_var,  
                                    values=['Drinks', 'Dessert', 'Food'], 
                                    font=("Arial", 18),
                                    width=241, height=35, 
                                    state="readonly")
    type_dropdown.place(x=555, y=619)

    def handle_save_menu():
        name = name_var.get()
        price_str = price_var.get()
        amount_str = amount_var.get()
        menu_type = type_var.get()
        
        if not (name and price_str and amount_str and menu_type):
            messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบถ้วน")
            return
            
        try:
            price = float(price_str)
            amount = int(amount_str)
        except ValueError:
            messagebox.showerror("Error", "ราคาและจำนวนต้องเป็นตัวเลข")
            return

        final_img_path = new_img_path.get()
        
        if final_img_path and final_img_path != current_img_path:
            file_extension = os.path.splitext(final_img_path)[1]
            new_filename = f"menu_{menu_id}_{name.replace(' ', '_')}{file_extension}"
            dest_path = os.path.join(MENU_IMG_FOLDER, new_filename)
            try:
                Image.open(final_img_path).save(dest_path)
                final_img_path = dest_path
            except Exception as e:
                messagebox.showwarning("Warning", f"ไม่สามารถคัดลอกรูปภาพ: {e}. ใช้ Path เดิมแทน")
                final_img_path = current_img_path
        
        if update_menu_item(menu_id, name, price, amount, menu_type, final_img_path):
            messagebox.showinfo("Success", f"แก้ไขเมนู {name} สำเร็จ")
            create_admin_edit_page(root, bg_images, current_category)
        else:
            messagebox.showerror("Error", "แก้ไขเมนูไม่สำเร็จ")


    ctk.CTkButton(root, 
                text="Save", 
                font=("Arial", 25, "bold"), 
                text_color="#003728", 
                fg_color="#bbd106", 
                hover_color="#a0b507",
                corner_radius=20,
                width=290, height=62,
                command=handle_save_menu,
    ).place(x=611, y=712)

    
    ctk.CTkButton(root, 
                text="Back", 
                font=("Arial", 16, "bold"), 
                text_color="#003728", 
                fg_color="#bbd106", 
                hover_color="#a0b507", 
                corner_radius=20,
                width=128, height=62,
                command=lambda: create_admin_edit_page(root, bg_images, current_category)
    ).place(x=64, y=42)


#หน้า Add Menu
def create_admin_add_menu_page(root, bg_images, current_category):
    for widget in root.winfo_children(): widget.destroy()
    if 'addmenu' not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพ 'addmenu'"); return
    
    background_label = customtkinter.CTkLabel(root, image=bg_images['addmenu'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    img_size = int(150 * 1.604) 
    img_x, img_y = int(373 * 1.604), int(145 * 1.546) 
    img_label = None; new_img_path = tk.StringVar(value="")
    
    def display_menu_img(path):
        nonlocal img_label
        if img_label: img_label.destroy()
        photo = None
        if path and os.path.exists(path):
            original_image = Image.open(path)
            resized_image = original_image.resize((img_size, img_size), Image.Resampling.LANCZOS)
        
            photo = customtkinter.CTkImage(light_image=resized_image, dark_image=resized_image, size=(img_size, img_size))
            
        if photo:
            img_label = customtkinter.CTkLabel(background_label, image=photo, text="", 
                                                fg_color='white',
                                                width=img_size, height=img_size)
            img_label.image = photo; 
            img_label.place(x=img_x, y=img_y)

    def browse_image():
        file_path = filedialog.askopenfilename(title="เลือกรูปภาพเมนู", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path: new_img_path.set(file_path); display_menu_img(file_path)

    customtkinter.CTkButton(background_label, text="Browse", font=("Arial", 15, "bold"), 
                            text_color="#003728", fg_color="#bbd106", hover_color="#a0b507",  
                            width=112, height=39, command=browse_image).place(x=858, y=410) 

    name_var = tk.StringVar(); price_var = tk.StringVar(); amount_var = tk.StringVar(); type_var = tk.StringVar(value=current_category)
    
   
    entry_style = {"font": ("Arial", 18), "border_width": 1} 

    customtkinter.CTkLabel(background_label, text="Name :", font=("Arial", 18, "bold"),
                            text_color="#003728", fg_color="white", anchor="w").place(x=420, y=479) 
    
    customtkinter.CTkEntry(background_label, fg_color="#ebf3c7",width=552, height=31, textvariable=name_var, **entry_style).place(x=510, y=479) 
    
    customtkinter.CTkLabel(background_label, text="Price :", font=("Arial", 18, "bold"), 
                           text_color="#003728", fg_color="white", anchor="w").place(x=420, y=526) 
    
    customtkinter.CTkEntry(background_label, fg_color="#ebf3c7", width=561, height=31,textvariable=price_var, **entry_style).place(x=502, y=526) 
    
    customtkinter.CTkLabel(background_label, text="Amount :", font=("Arial", 18, "bold"), 
                           text_color="#003728", fg_color="white", anchor="w").place(x=420, y=572) 
   
    customtkinter.CTkEntry(background_label, fg_color="#ebf3c7",width=515, height=31,textvariable=amount_var, **entry_style).place(x=549, y=572) 
    
    customtkinter.CTkLabel(background_label, text="Food Type :", font=("Arial", 18, "bold"), 
                           text_color="#003728", fg_color="white", anchor="w").place(x=420, y=619) 
    
    
    type_dropdown = customtkinter.CTkComboBox(background_label, variable=type_var, 
                                            values=['Drinks', 'Dessert', 'Food'], 
                                            font=("Arial", 18), state="readonly", 
                                            width=241, height=35)
    type_dropdown.place(x=555, y=619) 

    def handle_add_to_menu():
        name = name_var.get(); price_str = price_var.get(); amount_str = amount_var.get(); menu_type = type_var.get(); img_path = new_img_path.get()
        
        if not (name and price_str and amount_str and menu_type and img_path): messagebox.showerror("Error", "กรุณากรอกข้อมูลและเลือกรูปภาพให้ครบถ้วน"); return
        try: price = float(price_str); amount = int(amount_str)
        except ValueError: messagebox.showerror("Error", "ราคาและจำนวนต้องเป็นตัวเลข"); return

        
        if not os.path.exists(MENU_IMG_FOLDER):
            try: os.makedirs(MENU_IMG_FOLDER)
            except Exception as e:
                messagebox.showerror("Error", f"ไม่สามารถสร้าง Folder: {e}"); return
        
        new_menu_id = add_menu_item(name, price, amount, menu_type, '')
        if not new_menu_id: messagebox.showerror("Error", "ไม่สามารถเพิ่มเมนูได้"); return
        
        file_extension = os.path.splitext(img_path)[1]; new_filename = f"menu_{new_menu_id}_{name.replace(' ', '_')}{file_extension}"
        dest_path = os.path.join(MENU_IMG_FOLDER, new_filename)
        
        try:
            Image.open(img_path).save(dest_path) 
            
            update_menu_item(new_menu_id, name, price, amount, menu_type, dest_path)
            messagebox.showinfo("Success", f"เพิ่มเมนู {name} สำเร็จ"); 
            create_admin_edit_page(root, bg_images, menu_type) 
        except Exception as e: messagebox.showerror("Error", f"ไม่สามารถคัดลอกรูปภาพและเพิ่มเมนู: {e}")

    customtkinter.CTkButton(root, text="Add to Menu", font=("Arial", 25, "bold"), 
                            text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", 
                            corner_radius=20,width=289, height=62, command=handle_add_to_menu).place(x=611, y=712) 
    
    customtkinter.CTkButton(root, text="Back", font=("Arial", 25, "bold"),text_color="#003728", 
                            fg_color="#bbd106", hover_color="#a0b507", corner_radius=20,
                            width=128, height=54, command=lambda: create_admin_edit_page(root, bg_images, current_category)).place(x=64, y=42)
    

def display_admin_menu_items(root, category, bg_images, item_container):
    for widget in item_container.winfo_children(): widget.destroy()
    menu_list = get_all_menu_items(category)
    
    col_width = int(200 * 1.604); row_height = int(320 * 1.546) 
    items_per_row = 4 
    col_padding = int(16 * 1.604); row_padding = int(15 * 1.546) 
    
    
    
    for i, item in enumerate(menu_list):
        col = i % items_per_row
        row = i // items_per_row
        
        item_frame = customtkinter.CTkFrame(item_container, 
                                            fg_color="#ffffff", 
                                            width=col_width, 
                                            height=row_height, 
                                            border_width=0)
        
        item_frame.grid(row=row, column=col, padx=(0, col_padding), pady=(0, row_padding))

        img_path = item[MENU_IMG_PATH_IDX]; photo = None
        img_size = int(150 * 1.604) 
        
    
        if img_path and os.path.exists(img_path):
            img_resized = Image.open(img_path).resize((img_size, img_size), Image.Resampling.LANCZOS)
            photo = customtkinter.CTkImage(light_image=img_resized, dark_image=img_resized, size=(img_size, img_size))
        
        if photo:
            img_label = customtkinter.CTkLabel(item_frame, image=photo, text="",width=img_size, height=img_size)
            img_label.image = photo 
            img_label.place(x=30, y=10) 
            
        customtkinter.CTkLabel(item_frame, text=item[MENU_NAME_IDX], 
                                font=("THSarabunNew", 40, "bold"), 
                                text_color="#003728", fg_color="#ffffff",
                                anchor="center").place(relx=0.5, y=300, anchor="center") 
        
        # --- (NEW) แสดงจำนวนสต็อกคงเหลือ ---
        stock_amount = item[MENU_AMOUNT_IDX]
        # (Optional) ถ้าสต็อกน้อยกว่า 10 ให้แสดงเป็นสีแดง
        stock_color = "#d90000" if stock_amount <= 10 else "#003728"
        
        customtkinter.CTkLabel(item_frame, text=f"Stock: {stock_amount}", 
                                font=("Arial", 18, "bold"), 
                                text_color=stock_color, 
                                fg_color="#ffffff",
                                anchor="center").place(relx=0.5, y=340, anchor="center") 
        # --- (END NEW) ---
        
        
        customtkinter.CTkLabel(item_frame, text=f"{item[MENU_PRICE_IDX]} ฿", 
                                font=("Arial", 20, "bold"), 
                                text_color="#699039", fg_color="#ffffff",
                                anchor="center").place(relx=0.5, y=380, anchor="center") # <--- (MODIFIED) ปรับ Y-Pos
        
        
        customtkinter.CTkButton(item_frame, text="Edit", font=("Arial", 16, "bold"), 
                                text_color="#000000", fg_color="#ffa214", hover_color="#e28700", 
                                border_width=0,
                                width=112, height=54,
                                command=lambda d=item: create_admin_edit_menu_page(root, bg_images, d, category)).place(x=40, y=420) 
        
        def confirm_delete(menu_id, name):
            if messagebox.askyesno("Confirm Delete", f"คุณต้องการลบเมนู {name} ใช่หรือไม่?"):
                if delete_menu_item(menu_id): create_admin_edit_page(root, bg_images, category)
                else: messagebox.showerror("Error", "ลบเมนูไม่สำเร็จ")


        customtkinter.CTkButton(item_frame, text="Delete", font=("Arial", 16, "bold"), 
                                text_color="#000000", fg_color="#f11c0c", hover_color="#8e140b", 
                                border_width=0,
                                width=112, height=54,
                                command=lambda mid=item[MENU_ID_IDX], name=item[MENU_NAME_IDX]: confirm_delete(mid, name)).place(x=168, y=420)

# -----------------------------------------------
# --- หน้า Admin (Menu Hub) ---
# -----------------------------------------------

def create_admin_menu_for_admin_page(root, bg_images):
    """
    *** หน้าใหม่: หน้าเมนูหลักสำหรับ Admin ***
    """
    for widget in root.winfo_children(): widget.destroy()
    
    if 'admin_menu' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'admin_menu'"); 
        create_main_page(root, bg_images) # กลับหน้าหลักถ้าไม่เจอรูป
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['admin_menu'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # --- สไตล์ปุ่มหลัก (อ้างอิงจากดีไซน์ในรูป) ---
    btn_style = {
        "font": ("Arial", 28, "bold"),
        "text_color": "#003728",
        "fg_color": "#ebf3c7",
        "hover_color": "#d1f680",
        "border_width": 2,
        "border_color": "#bbd106",
        "corner_radius": 20,
        "width": 250,
        "height": 180 
    }

    # --- ปุ่ม Order ---
    # (เราจะให้มันไปที่หน้า order ที่เคยเป็นหน้า landing page เดิม)
    order_btn = customtkinter.CTkButton(
        background_label, 
        text="Order", 
        **btn_style,
        command=lambda: create_admin_order_page(root, bg_images)
    )
    order_btn.place(relx=0.25, rely=0.5, anchor="center")

    # --- ปุ่ม Menu ---
    # (นี่คือปุ่มที่โจทย์สั่ง ให้ไปที่หน้า Edit Menu)
    menu_btn = customtkinter.CTkButton(
        background_label, 
        text="Menu", 
        **btn_style,
        command=lambda: create_admin_edit_page(root, bg_images, 'Drinks') # ไปหน้า Edit โดยเริ่มที่ 'Drinks'
    )
    menu_btn.place(relx=0.5, rely=0.5, anchor="center")

    # --- ปุ่ม Sales ---
    # (ยังไม่สร้าง เลยใส่ Messagebox ไว้ก่อน)
    sales_btn = customtkinter.CTkButton(
        background_label, 
        text="Sales", 
        **btn_style,
        command=lambda: create_sales_dashboard_page(root, bg_images)
    )
    sales_btn.place(relx=0.75, rely=0.5, anchor="center")

    # --- ปุ่ม Log Out (ตามรูป) ---
    logout_btn = customtkinter.CTkButton(
        background_label,
        text="Log Out",
        font=("Arial", 16, "bold"),
        text_color="#bbd106", 
        fg_color="#00452e", 
        hover_color="#2c5432",
        width=193, 
        height=62,
        corner_radius=20,
        command=lambda: create_main_page(root, bg_images)
    )
    logout_btn.place(x=37, y=750) # ตำแหน่งตามรูป

    # --- ปุ่ม Nav (ขวาล่าง) ---
    create_nav_button(background_label, bg_images, lambda: create_admin_menu_for_admin_page(root, bg_images))


def create_admin_edit_page(root, bg_images, category='Drinks'):
    for widget in root.winfo_children(): widget.destroy()
    if 'editdrinks' not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพพื้นหลัง Edit"); return
    
    # <--- CONVERTED: เพิ่ม text="" ---
    background_label = customtkinter.CTkLabel(root, image=bg_images['editdrinks'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    # <--- CONVERTED: (พารามิเตอร์) ---
    customtkinter.CTkButton(root, text="Add Menu", font=("Arial", 25, "bold"), 
                            text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", 
                            border_width=0,
                            width=193, height=54,
                            command=lambda: create_admin_add_menu_page(root, bg_images, category)).place(x=1291, y=39) 
    
    # --- START SCROLLBAR IMPLEMENTATION (REPLACED) ---
    
    scrollable_menu_frame = customtkinter.CTkScrollableFrame(background_label, 
                                                            fg_color="#ebf3c7", 
                                                            border_width=0,
                                                            width=int(857*1.604), height=int(320*1.546))
    scrollable_menu_frame.place(x=64, y=278) 
    
    # --- END SCROLLBAR IMPLEMENTATION ---
    
    button_style = {"font": ("Arial", 25, "bold"), 
                    "text_color": "#003728", 
                    "fg_color": "#bbd106", 
                    "hover_color": "#e6fb42", 
                    "border_width": 0}
    
    def switch_category(new_category): create_admin_edit_page(root, bg_images, new_category)

    customtkinter.CTkButton(background_label, text="Drinks", **button_style,width=193, height=63, command=lambda: switch_category('Drinks')).place(x=460, y=189) 
    customtkinter.CTkButton(background_label, text="Dessert", **button_style, width=193, height=63,command=lambda: switch_category('Dessert')).place(x=669, y=189) 
    customtkinter.CTkButton(background_label, text="Food", **button_style, width=193, height=63,command=lambda: switch_category('Food')).place(x=877, y=189) 

    display_admin_menu_items(root, category, bg_images, scrollable_menu_frame)

    customtkinter.CTkButton(root, text="Back", font=("Arial", 25, "bold"), 
                            text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", 
                            border_width=0,
                            width=128, height=54,
                            command=lambda: create_admin_menu_for_admin_page(root, bg_images)).place(x=64, y=42) 
    
    create_nav_button(root, bg_images, lambda: create_admin_edit_page(root, bg_images, category))

# --- (NEW) Cache สำหรับรูปสลิปของ Admin ---
admin_slip_cache = {}

def create_admin_order_details_page(root, bg_images, table_number):
    """
    *** NEW: หน้า "Order Details" (รูปที่ 23) ***
    แสดงออเดอร์ที่ค้างของโต๊ะที่เลือก
    """
    global admin_slip_cache
    admin_slip_cache.clear() # ล้าง Cache ทุกครั้งที่เปิดหน้า
    
    for widget in root.winfo_children(): widget.destroy()
    
    # *** สำคัญ: ต้องเพิ่มรูปนี้ใน image_paths ***
    if 'admin_order_details' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'admin_order_details'"); 
        create_admin_order_page(root, bg_images) # ย้อนกลับไปหน้า See Order
        return
    
    background_label = customtkinter.CTkLabel(root, image=bg_images['admin_order_details'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # 1. Header (ปุ่ม Back และ หมายเลขโต๊ะ)
    customtkinter.CTkButton(
        root, text="Back", font=("Arial", 16, "bold"), 
        text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", 
        border_width=0, width=128, height=54,
        command=lambda: create_admin_order_page(root, bg_images) # กลับไปหน้า See Order
    ).place(x=64, y=42)

    customtkinter.CTkLabel(
        root, text=f"{table_number}", font=("Arial", 40, "bold"),
        text_color="#003728", fg_color="#bbd106",
        width=70, height=65, corner_radius=10, anchor="center"
    ).place(x=210, y=36) # ตำแหน่งตามรูป

    # 2. สร้าง Scrollable Frame สำหรับรายการออเดอร์
    order_scroll_frame = customtkinter.CTkScrollableFrame(
        root,
        fg_color="#ebf3c7", # สีพื้นหลังของ Scroll Frame
        bg_color="#ebf3c7", # สีพื้นหลังของพื้นที่
        width=1300,
        height=550
    )
    order_scroll_frame.place(x=118, y=200)

    # 3. ดึงออเดอร์ที่ค้างของโต๊ะนี้
    active_orders = get_active_orders_for_table(table_number)

    if not active_orders:
        customtkinter.CTkLabel(
            order_scroll_frame, text="ไม่พบออเดอร์สำหรับโต๊ะนี้",
            font=("Arial", 25, "bold"), text_color="#003728"
        ).pack(pady=50)

    # 4. ฟังก์ชัน Helper สำหรับปุ่ม
    def handle_complete(order_id, table_num):
        if messagebox.askyesno("Confirm", "ยืนยันว่าออเดอร์นี้เสร็จสิ้น?"):
            if update_order_status(order_id, 'Served'):
                messagebox.showinfo("Success", "อัปเดตสถานะเป็น 'Served' เรียบร้อย")
                # โหลดหน้านี้ใหม่
                create_admin_order_details_page(root, bg_images, table_num)
            else:
                messagebox.showerror("Error", "ไม่สามารถอัปเดตสถานะได้")
    
    def handle_cancel(order_id, table_num):
        if messagebox.askyesno("Confirm", "คุณต้องการยกเลิกออเดอร์นี้?"):
            if update_order_status(order_id, 'Cancelled'):
                messagebox.showinfo("Cancelled", "ออเดอร์ถูกยกเลิกแล้ว")
                # โหลดหน้านี้ใหม่
                create_admin_order_details_page(root, bg_images, table_num)
            else:
                messagebox.showerror("Error", "ไม่สามารถยกเลิกได้")

    # 5. วนลูปสร้างการ์ดออเดอร์
    for order_data in active_orders:
        order_id = order_data[ORDER_ID_IDX]
        slip_path = order_data[ORDER_SLIP_PATH_IDX]
        total_price = order_data[ORDER_TOTAL_IDX]
        order_time_str = order_data[ORDER_TIME_IDX]
        order_no = order_data[ORDER_NO_IDX]
        
        # จัดการเวลา
        try:
            order_time_dt = datetime.strptime(order_time_str, "%Y-%m-%d %H:%M:%S")
            formatted_time = order_time_dt.strftime("%d/%m/%Y %H:%M pm")
        except ValueError:
            formatted_time = order_time_str

        # --- สร้างการ์ดหลัก (กรอบสีขาว) ---
        card_frame = customtkinter.CTkFrame(
            order_scroll_frame,
            fg_color="white",
            corner_radius=20,
            height=250 # ความสูงโดยประมาณ
        )
        card_frame.pack(fill="x", expand=True, pady=10, padx=10)

        # --- (ฝั่งซ้าย) รูปสลิป ---
        slip_frame = customtkinter.CTkFrame(card_frame, fg_color="white", width=280, height=340)
        slip_frame.pack(side="left", padx=20, pady=20, fill="y")
        
        customtkinter.CTkLabel(slip_frame, text="PAY SLIP", font=("Arial", 16, "bold"), text_color="#003728").pack(anchor="w")
        
        slip_img_label = customtkinter.CTkLabel(slip_frame, text="Loading Slip...", fg_color="#e0e0e0", width=280, height=340)
        slip_img_label.pack(pady=5)
        
        # โหลดรูปสลิป
        ctk_slip_img = None
        if slip_path and os.path.exists(slip_path):
            try:
                img_pil = Image.open(slip_path).convert("RGBA")
                img_resized = img_pil.resize((280, 340), Image.Resampling.LANCZOS)
                ctk_slip_img = customtkinter.CTkImage(light_image=img_resized, dark_image=img_resized, size=(280, 340))
                admin_slip_cache[order_id] = ctk_slip_img # เก็บเข้า Cache
            except Exception as e:
                print(f"Error loading slip image {slip_path}: {e}")
                
        if ctk_slip_img:
            slip_img_label.configure(image=ctk_slip_img, text="")
        else:
            slip_img_label.configure(text="Slip Not Found")

        # --- (ฝั่งขวา) รายละเอียดออเดอร์ ---
        details_frame = customtkinter.CTkFrame(card_frame, fg_color="white")
        details_frame.pack(side="right", fill="both", expand=True, padx=20, pady=10)

        # Frame สำหรับรายการอาหาร
        items_list_frame = customtkinter.CTkFrame(details_frame, fg_color="transparent")
        items_list_frame.pack(fill="x", expand=True)
        
        order_items = get_order_items(order_id)
        item_index = 1
        for item in order_items:
            name, qty, price_per_item = item
            
            customtkinter.CTkLabel(
                items_list_frame, 
                text=f"{item_index}. {name}", 
                font=("THSarabunNew", 30, "bold"), text_color="#003728"
            ).grid(row=item_index-1, column=0, sticky="w")
            
            customtkinter.CTkLabel(
                items_list_frame, 
                text=f"{price_per_item:.0f} ฿ x {qty}", 
                font=("Arial", 18), text_color="#417c49"
            ).grid(row=item_index-1, column=1, sticky="e", padx=20)
            
            item_index += 1
            
        items_list_frame.grid_columnconfigure(0, weight=3)
        items_list_frame.grid_columnconfigure(1, weight=1)

        # ราคารวม (อยู่ใต้รายการอาหาร)
        customtkinter.CTkLabel(
            details_frame, text=f"{total_price:.0f} ฿", 
            font=("Arial", 28, "bold"), text_color="#003728",
            anchor="e"
        ).pack(anchor="e", fill="x", pady=(10,0), padx=20)
        
        # --- (ส่วนล่าง) เลขที่, เวลา, ปุ่ม ---
        bottom_frame = customtkinter.CTkFrame(details_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", side="bottom", pady=10)

        # (ซ้ายล่าง) เลขที่ และ เวลา
        info_frame = customtkinter.CTkFrame(bottom_frame, fg_color="transparent")
        info_frame.pack(side="left")
        customtkinter.CTkLabel(info_frame, text=f"No. {order_no}", font=("Arial", 16, "bold"), text_color="#003728").pack(anchor="w")
        customtkinter.CTkLabel(info_frame, text=f"Order Time: {formatted_time}", font=("Arial", 14), text_color="#505050").pack(anchor="w")

        # (ขวาล่าง) ปุ่ม
        button_frame = customtkinter.CTkFrame(bottom_frame, fg_color="transparent")
        button_frame.pack(side="right")
        
        
        customtkinter.CTkButton(
            button_frame, text="Complete", font=("Arial", 16, "bold"),
            text_color="#003728", fg_color="#bbd106", hover_color="#a0b507",
            width=120, height=40, corner_radius=20,
            command=lambda oid=order_id, t=table_number: handle_complete(oid, t)
        ).pack(side="left", padx=5)

    create_nav_button(root, bg_images, lambda: create_admin_order_details_page(root, bg_images, table_number))


def create_admin_order_page(root, bg_images):
    """
    *** MODIFIED: หน้า "See Order" (รูปที่ 22) ***
    แสดงโต๊ะทั้งหมด และไฮไลต์โต๊ะที่มีออเดอร์
    """
    for widget in root.winfo_children(): widget.destroy()
    if 'order' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'order'"); return
    
    background_label = customtkinter.CTkLabel(root, image=bg_images['order'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    # 1. ดึงข้อมูลโต๊ะที่มีออเดอร์ค้าง
    active_tables = get_active_tables() # เช่น [1, 3]

    table_names = ["1", "2", "3", "4"]
    button_width = int(124 * 1.604); button_height = int(133 * 1.546) 
    start_x = int(156 * 1.604); spacing = int(39 * 1.604) 
    
    for i, num_str in enumerate(table_names):
        table_num_int = int(num_str)
        x = start_x + i * (button_width + spacing)
        y = 363 # y-position ของปุ่ม
        
        # 2. สร้างปุ่ม
        table_btn = customtkinter.CTkButton(
            root, 
            text=f"Table\n{num_str}", 
            font=("Arial", 24, "bold"), 
            text_color="#417c49", 
            fg_color="#ebf3c7", 
            hover_color="#a0b507", 
            border_width=0,
            width=button_width, 
            height=button_height,
            # 3. เชื่อมปุ่มไปยังหน้า Order Details
            command=lambda n=table_num_int: create_admin_order_details_page(root, bg_images, n)
        )
        table_btn.place(x=x, y=y)

        # 4. ตรวจสอบว่าต้องเพิ่ม "Have Order" หรือไม่
        if table_num_int in active_tables:
            # เพิ่ม Label สีแดงไว้ข้างใต้ปุ่ม
            have_order_label = customtkinter.CTkLabel(
                root,
                text="Have Order",
                font=("Arial", 16, "bold"),
                text_color="red",
                fg_color="white" # สีพื้นหลังของหน้าจอ
            )
            # วาง Label นี้ไว้ข้างใต้ปุ่ม
            have_order_label.place(x=x + (button_width/2), y=y + button_height + 15, anchor="center")

    
    # ปุ่ม Back (กลับไปหน้า Admin Menu)
    customtkinter.CTkButton(
        root, text="Back", font=("Arial", 16, "bold"), 
        text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", 
        border_width=0,
        width=128, height=54,
        command=lambda: create_admin_menu_for_admin_page(root, bg_images) 
    ).place(x=64, y=42)
    
    create_nav_button(root, bg_images, lambda: create_admin_order_page(root, bg_images))


def create_sales_dashboard_page(root, bg_images):
    """
    *** NEW: หน้า Sales Dashboard (ตามรูป) ***
    """
    for widget in root.winfo_children(): widget.destroy()
        
    if 'sales_dashboard' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'sales_dashboard'"); 
        create_admin_menu_for_admin_page(root, bg_images)
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['sales_dashboard'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # --- ตัวแปรสำหรับ Filters ---
    report_type_var = tk.StringVar(value="Monthly")
    type_var = tk.StringVar(value="All")
    year_var = tk.StringVar(value="2025")
    month_var = tk.StringVar(value="11")
    day_var = tk.StringVar(value="29")
    total_sales_var = tk.StringVar(value="Total Sales\n0.00 ฿")

    # --- ปุ่ม Back ---
    customtkinter.CTkButton(
        root, text="Back", font=("Arial", 20, "bold"), 
        text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", 
        border_width=0, width=128, height=54, corner_radius=20,
        command=lambda: create_admin_menu_for_admin_page(root, bg_images)
    ).place(x=30, y=30)
    
    # --- Total Sales Label ---
    total_sales_label = customtkinter.CTkLabel(
        root, 
        textvariable=total_sales_var,
        font=("Arial", 40, "bold"),
        text_color="#003728",
        fg_color="#ebf3c7", # สีพื้นหลังตามดีไซน์
        anchor="e",
        justify="right"
    )
    total_sales_label.place(x=1400, y=170, anchor="ne")

    # --- Frame สำหรับ Filters ---
    filter_frame = customtkinter.CTkFrame(root, fg_color="#ebf3c7")
    filter_frame.place(x=40, y=170)

    customtkinter.CTkLabel(filter_frame, text="Sales Report", font=("Arial", 16, "bold"), text_color="#003728").pack(side="left", padx=(10, 5), pady=5)
    
    report_type_segmented_btn = customtkinter.CTkSegmentedButton(
        filter_frame,
        values=["Daily", "Monthly", "Yearly"],
        variable=report_type_var,
        font=("Arial", 14, "bold"),
        selected_color="#bbd106",
        selected_hover_color="#a0b507",
        unselected_color="#ffffff",
        unselected_hover_color="#f0f0f0",
        text_color="#003728",
        height=35
    )
    report_type_segmented_btn.pack(side="left", padx=5, pady=5)

    customtkinter.CTkLabel(filter_frame, text="Type", font=("Arial", 16, "bold"), text_color="#003728").pack(side="left", padx=(15, 5), pady=10)
    type_combo = customtkinter.CTkComboBox(
        filter_frame,
        values=['All', 'Drinks', 'Dessert', 'Food'],
        variable=type_var,
        state="readonly",
        font=("Arial", 14),
        width=120,
        height=35
    )
    type_combo.pack(side="left", padx=5, pady=10)

    # --- Frame สำหรับ Date Filters ---
    date_filter_frame = customtkinter.CTkFrame(root, fg_color="#ebf3c7")
    date_filter_frame.place(x=40, y=230)
    
    customtkinter.CTkLabel(date_filter_frame, text="Year", font=("Arial", 16, "bold"), text_color="#003728").pack(side="left", padx=(10, 5), pady=10)
    year_combo = customtkinter.CTkComboBox(
        date_filter_frame, values=[str(y) for y in range(2024, 2031)], variable=year_var, state="readonly", font=("Arial", 14), width=80, height=35
    )
    year_combo.pack(side="left", padx=5, pady=10)

    customtkinter.CTkLabel(date_filter_frame, text="Month", font=("Arial", 16, "bold"), text_color="#003728").pack(side="left", padx=(10, 5), pady=10)
    month_combo = customtkinter.CTkComboBox(
        date_filter_frame, values=[str(m) for m in range(1, 13)], variable=month_var, state="readonly", font=("Arial", 14), width=70, height=35
    )
    month_combo.pack(side="left", padx=5, pady=10)

    customtkinter.CTkLabel(date_filter_frame, text="Day", font=("Arial", 16, "bold"), text_color="#003728").pack(side="left", padx=(10, 5), pady=10)
    day_combo = customtkinter.CTkComboBox(
        date_filter_frame, values=[str(d) for d in range(1, 32)], variable=day_var, state="readonly", font=("Arial", 14), width=70, height=35
    )
    day_combo.pack(side="left", padx=5, pady=10)

    # --- ฟังก์ชันเปิด/ปิด Date Filters ---
    def update_filter_state(*args):
        report_type = report_type_var.get()
        if report_type == 'Daily':
            year_combo.configure(state="readonly")
            month_combo.configure(state="readonly")
            day_combo.configure(state="readonly")
        elif report_type == 'Monthly':
            year_combo.configure(state="readonly")
            month_combo.configure(state="readonly")
            day_combo.configure(state="disabled")
        elif report_type == 'Yearly':
            year_combo.configure(state="readonly")
            month_combo.configure(state="disabled")
            day_combo.configure(state="disabled")

    report_type_var.trace_add("write", update_filter_state)
    update_filter_state() # เรียกครั้งแรกเพื่อตั้งค่า

    # --- TreeView (ตาราง) ---
    style = ttk.Style()
    style.theme_use("default")
    
    # สไตล์ของ Header
    style.configure("Treeview.Heading", 
        font=("Arial", 18, "bold"), 
        background="#003728",  # สีเขียวเข้ม
        foreground="white",
        padding=10
    )
    # สไตล์ของ Row
    style.configure("Treeview", 
        rowheight=40, 
        font=("Arial", 16), 
        background="#ffffff", 
        foreground="#003728", 
        fieldbackground="#ffffff"
    )
    # สไตล์เมื่อเลือก
    style.map("Treeview", 
        background=[('selected', '#bbd106')],
        foreground=[('selected', '#003728')]
    )
    style.configure("Treeview", borderwidth=0, relief="flat")
    style.configure("Treeview.Heading", borderwidth=0, relief="flat")


    tree_frame = customtkinter.CTkFrame(root, fg_color="#ffffff",
                                        width=1700, height=600)
    tree_frame.place(x=140, y=310)

    tree = ttk.Treeview(
        tree_frame, 
        columns=("Name", "Type", "Sold", "Total"), 
        show="headings",
        style="Treeview"
    )
    
    tree.heading("Name", text="Name", anchor="w")
    tree.heading("Type", text="Type", anchor="center")
    tree.heading("Sold", text="Sold", anchor="center")
    tree.heading("Total", text="Total", anchor="e")

    tree.column("Name", width=680, anchor="w")
    tree.column("Type", width=270, anchor="center")
    tree.column("Sold", width=270, anchor="center")
    tree.column("Total", width=300, anchor="e")

    tree.pack(fill="both", expand=True)

    # --- ฟังก์ชัน Search ---
    def handle_search():
        # 1. ล้างข้อมูลเก่า
        for item in tree.get_children():
            tree.delete(item)
            
        # 2. ดึงค่าจาก filters
        report_type = report_type_var.get()
        menu_type = type_var.get()
        
        try:
            year = int(year_var.get())
            month = int(month_var.get()) if month_combo.cget("state") != "disabled" else 1
            day = int(day_var.get()) if day_combo.cget("state") != "disabled" else 1
        except ValueError:
            messagebox.showerror("Error", "ข้อมูลวันที่ไม่ถูกต้อง")
            return
            
        # 3. ดึงข้อมูลจาก DB
        results = get_sales_report(report_type, year, month, day, menu_type)
        
        # 4. แสดงผลในตาราง
        grand_total = 0.0
        for row in results:
            (name, m_type, sold, total) = row
            if total is None: total = 0.0
            
            formatted_total = f"{total:,.2f} ฿"
            tree.insert("", "end", values=(name, m_type, sold, formatted_total))
            grand_total += total
            
        # 5. อัปเดตยอดรวม
        total_sales_var.set(f"Total Sales\n{grand_total:,.2f} ฿")

    # --- ปุ่ม Search ---
    search_button = customtkinter.CTkButton(
        filter_frame,
        text="Search",
        font=("Arial", 16, "bold"),
        text_color="#003728",
        fg_color="#ffa214", # สีส้มตามดีไซน์
        hover_color="#e28700",
        width=100,
        height=35,
        command=handle_search
    )
    search_button.pack(side="left", padx=15, pady=10)

    # --- โหลดข้อมูลครั้งแรกเมื่อเปิดหน้า ---
    handle_search()
    
    create_nav_button(root, bg_images, lambda: create_sales_dashboard_page(root, bg_images))

# -----------------------------------------------
# --- หน้า User  ---
# -----------------------------------------------


menu_image_cache = {} 

def display_menu_items(root, category, bg_images, item_container, user_data, table_number):
    global menu_image_cache
    menu_image_cache.clear()

    for widget in item_container.winfo_children(): 
        widget.destroy()
        
    menu_list = get_all_menu_items(category)

    col_width = int(200 * 1.604); row_height = int(320 * 1.546) 
    items_per_row = 4 
    col_padding = int(15 * 1.604); row_padding = int(15 * 1.546) 
    

    for i, item in enumerate(menu_list):
        col = i % items_per_row
        row = i // items_per_row
        
        item_frame = customtkinter.CTkFrame(
            item_container, 
            width=col_width, 
            height=row_height,
            fg_color="#ffffff",
            corner_radius=10
        )
        
        item_frame.grid(row=row, column=col, padx=(0, col_padding), pady=(0, row_padding))
        
        item_frame.grid_propagate(False) 

        img_path = item[MENU_IMG_PATH_IDX]
        photo = None
        target_path = img_path if img_path and os.path.exists(img_path) else image_paths.get('default_menu_img')

        img_size = int(150 * 1.604) 
        if target_path and os.path.exists(target_path):
            try:
                img_original = Image.open(target_path).convert("RGBA")
                img_resized = img_original.resize((img_size, img_size), Image.Resampling.LANCZOS)
                
                photo = customtkinter.CTkImage(
                    light_image=img_resized,
                    dark_image=img_resized,
                    size=(img_size, img_size)
                )
                menu_image_cache[item[MENU_ID_IDX]] = photo
            except Exception as e:
                print(f"Error loading menu item image: {e}")

        if photo:
            img_label = customtkinter.CTkLabel(
                item_frame, 
                text="", 
                image=photo
            )
            img_label.place(x=40, y=8) 
        
        customtkinter.CTkLabel(
            item_frame, 
            text=item[MENU_NAME_IDX], 
            font=("THSarabunNew", 35, "bold"), 
            text_color="#003728", 
            fg_color="transparent" 
        ).place(relx=0.5, y=294, anchor=tk.CENTER) 
        
        customtkinter.CTkLabel(
            item_frame, 
            text=f"{item[MENU_PRICE_IDX]:,.2f} ฿", 
            font=("Arial", 40, "bold"), 
            text_color="#417c49", 
            fg_color="transparent"
        ).place(relx=0.5, y=379, anchor=tk.CENTER) 
        
        customtkinter.CTkButton(
            item_frame, 
            text="Add to Cart", 
            font=("Arial", 16, "bold"), 
            text_color="#FFFFFF",   
            fg_color="#417c49",    
            hover_color="#2c5432",   
            width=193, 
            height=46, 
            corner_radius=8,
            command=lambda i=item: create_add_to_cart_page(root, bg_images, user_data, table_number, i)
        ).place(relx=0.5, y=441, anchor=tk.CENTER) 



def create_add_to_cart_page(root, bg_images, user_data, table_number, item_data):
    """
    *** ฟังก์ชันใหม่สำหรับหน้า Add To Cart ***
    """
    for widget in root.winfo_children(): widget.destroy()
    
    # 1. ตรวจสอบและตั้งค่าพื้นหลัง
    if 'add_to_cart' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'add_to_cart'"); 
        create_menu_page(root, bg_images, user_data, table_number) 
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['add_to_cart'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    item_id = item_data[MENU_ID_IDX]
    item_name = item_data[MENU_NAME_IDX]
    item_price = item_data[MENU_PRICE_IDX]
    item_img_path = item_data[MENU_IMG_PATH_IDX]
    item_stock = item_data[MENU_AMOUNT_IDX] 

    quantity = tk.IntVar(value=1)
    
    total_string_var = tk.StringVar(value=f"Total : {item_price:,.2f} ฿")

    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=70)
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_add_to_cart_page(root, bg_images, user_data, table_number, item_data)
    
    profile_btn = customtkinter.CTkButton(
        background_label, image=profile_button_image, text="", 
        fg_color="transparent", hover_color="#a0b507", 
        width=70, height=70, corner_radius=0, border_width=0, 
        # <--- (MODIFIED) ส่ง lambda ไปให้หน้า Profile
        command=lambda: create_profile_page(root, bg_images, user_data, rebuild_this_page_func)
    )
    profile_btn.place(x=38, y=40) 
    
    customtkinter.CTkLabel(
        background_label, 
        text=f" {table_number}", 
        font=("Arial", 40, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106" 
    ).place(x=245, y=54) 

    customtkinter.CTkLabel(
        customtkinter.CTkLabel(background_label, text=f"{item_price:,.2f} ฿"), 
        font=("Arial", 40, "bold"), text_color="#003728", fg_color="#bbd106"
    ).place(x=245, y=54) 
    
    cart_btn_header = customtkinter.CTkButton(
        background_label, text="🛒 Cart", 
        font=("Arial", 25, "bold"), text_color="#003728", 
        fg_color="#bbd106", hover_color="#a0b507",
        width=145, height=66, corner_radius=30,
        
        command=lambda: create_cart_page(root, bg_images, user_data, table_number) 
    )
    cart_btn_header.place(x=1335, y=42) 

    
    img_size = 338
    ctk_photo = None
    target_path = item_img_path if item_img_path and os.path.exists(item_img_path) else image_paths.get('default_menu_img')
    
    if target_path and os.path.exists(target_path):
        try:
            img_original = Image.open(target_path).convert("RGBA")
            img_resized = img_original.resize((img_size, img_size), Image.Resampling.LANCZOS)
            ctk_photo = customtkinter.CTkImage(light_image=img_resized, dark_image=img_resized, size=(img_size, img_size))
        except Exception as e:
            print(f"Error loading item image: {e}")
    
    if ctk_photo:
        img_label = customtkinter.CTkLabel(background_label, text="", image=ctk_photo, fg_color="#FFFFFF", corner_radius=10, width=img_size, height=img_size)
        img_label.place(x=106, y=289) 

    # --- ชื่อและราคา ---
    customtkinter.CTkLabel(background_label, text=item_name, font=("THSarabunNew", 40, "bold"), 
                            text_color="#003728", fg_color="#FFFFFF"
                            ).place(x=495, y=320)
    
    customtkinter.CTkLabel(background_label, text=f"{item_price:,.2f} ฿", font=("Arial", 40, "bold"), 
                            text_color="#417c49", fg_color="#FFFFFF"
                            ).place(x=500, y=400)

    #ฟังก์ชันสำหรับปุ่มเพิ่ม/ลด
    def update_total():
        qty = quantity.get()
        new_total = qty * item_price
        total_string_var.set(f"Total : {new_total:,.2f} ฿")

    def increase_qty():
        current_qty = quantity.get()
        if current_qty < item_stock:
            quantity.set(current_qty + 1)
        else:
            messagebox.showwarning("Stock Limit", f"มีสินค้าในสต็อกเพียง {item_stock} ชิ้น")
        update_total()

    def decrease_qty():
        current_qty = quantity.get()
        if current_qty > 1:
            quantity.set(current_qty - 1)
        update_total()

    # 6. UI สำหรับส่วนเลือกจำนวน
    customtkinter.CTkLabel(background_label, text="จำนวน", font=("THSarabunNew", 60, "bold"), text_color="#799841", fg_color="#ebf3c7").place(x=1060, y=370)
    
    qty_label = customtkinter.CTkLabel(background_label, textvariable=quantity, font=("Arial", 40, "bold"), 
                                        text_color="#799841", fg_color="#ebf3c7", width=50, anchor="center")
    qty_label.place(x=1090, y=472) 

    # --- ปุ่ม +/- ---
    btn_style = {"font": ("Arial", 30, "bold"), "text_color": "#FFFFFF", "fg_color": "#799841", "hover_color": "#709036", "width": 50, "height": 60, "corner_radius": 30}
    
    minus_btn = customtkinter.CTkButton(background_label, text="-", **btn_style, command=decrease_qty)
    minus_btn.place(x=1000, y=470)

    plus_btn = customtkinter.CTkButton(background_label, text="+", **btn_style, command=increase_qty)
    plus_btn.place(x=1150, y=470)

    def handle_add_to_cart():
        global user_cart # <--- NEW
        qty_to_add = quantity.get()
        
        # <--- NEW: Logic to add item to global cart dictionary
        if item_id in user_cart:
            # ถ้ามีอยู่แล้ว, เช็คสต็อกก่อนบวกเพิ่ม
            current_in_cart = user_cart[item_id]['quantity']
            if current_in_cart + qty_to_add > item_stock:
                messagebox.showwarning("Stock Limit", f"คุณมี {item_name} ในตะกร้า {current_in_cart} ชิ้น และในสต็อกมี {item_stock} ชิ้น ไม่สามารถเพิ่มได้อีก")
                return # ไม่ต้องทำอะไรต่อ
            else:
                user_cart[item_id]['quantity'] += qty_to_add
        else:
            # ถ้ายังไม่มี, ก็เพิ่มใหม่
            user_cart[item_id] = {'item_data': item_data, 'quantity': qty_to_add}
        
        messagebox.showinfo("Cart", f"เพิ่ม {item_name} (จำนวน {qty_to_add}) ลงตะกร้าแล้ว!")
        # <--- END NEW ---
        
        create_menu_page(root, bg_images, user_data, table_number)

    btn_style_footer = {"font": ("Arial", 25, "bold"), "text_color": "#003728", "fg_color": "#bbd106", 
                        "hover_color": "#a0b507", "width": 195, "height": 62, "corner_radius": 20}

    back_btn = customtkinter.CTkButton(background_label, text="Back", **btn_style_footer,
                                        command=lambda: create_menu_page(root, bg_images, user_data, table_number))
    back_btn.place(x=95, y=708) 

    total_label = customtkinter.CTkLabel(background_label, textvariable=total_string_var, font=("Arial", 48, "bold"), text_color="#003728", fg_color="#ebf3c7")
    total_label.place(x=850, y=719) 

    add_cart_btn = customtkinter.CTkButton(background_label, text="Add Cart", **btn_style_footer,
                                            command=handle_add_to_cart) 
    add_cart_btn.place(x=1247, y=708) 
    

    create_nav_button(background_label, bg_images, rebuild_this_page_func) # <--- (MODIFIED)

# -----------------------------------------------
# --- *** CART PAGE *** ---
# -----------------------------------------------

def create_cart_page(root, bg_images, user_data, table_number):
    """
    *** ฟังก์ชันใหม่สำหรับหน้าตะกร้าสินค้า (Cart) ***
    """
    global user_cart
    for widget in root.winfo_children(): widget.destroy()

    
    if 'cart' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'cart'"); 
        create_menu_page(root, bg_images, user_data, table_number) 
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['cart'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)


    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=70)
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_cart_page(root, bg_images, user_data, table_number)

    profile_btn = customtkinter.CTkButton(
        background_label, image=profile_button_image, text="", 
        fg_color="transparent", hover_color="#a0b507", 
        width=70, height=70, corner_radius=0, border_width=0, 
        # <--- (MODIFIED) ส่ง lambda ไปให้หน้า Profile
        command=lambda: create_profile_page(root, bg_images, user_data, rebuild_this_page_func)
    )
    profile_btn.place(x=38, y=40) 
    
    customtkinter.CTkLabel(
        background_label, text=f" {table_number}", 
        font=("Arial", 40, "bold"), text_color="#003728", fg_color="#bbd106"
    ).place(x=245, y=54) 
    
    
    customtkinter.CTkButton(
        background_label, text="Order", 
        font=("Arial", 25, "bold"), text_color="#003728", 
        fg_color="#bbd106", hover_color="#a0b507",
        width=145, height=66, corner_radius=30,
        command=lambda: create_your_order_page(root, bg_images, user_data, table_number)
    ).place(x=1335, y=42) 

    
    scroll_frame = customtkinter.CTkScrollableFrame(
        background_label,
        fg_color="#ebf3c7",
        bg_color="#ebf3c7", 
        corner_radius=20,
        width=1300, 
        height=450  
    )
    scroll_frame.place(x=90, y=240) 

    total_label = customtkinter.CTkLabel(
        background_label, text="Total Pay 0.00 ฿",
        font=("Arial", 40, "bold"), 
        text_color="#003728", 
        fg_color="#ebf3c7" 
    )
    total_label.place(x=850, y=745)
    
    def refresh_display():
        """
        ฟังก์ชันสำหรับวาดรายการสินค้าในตะกร้าใหม่ทั้งหมด
        """
        # ล้างของเก่า
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        total_pay = 0.0
        
        if not user_cart:
            customtkinter.CTkLabel(
                scroll_frame, 
                text="ตะกร้าสินค้าว่างเปล่า",
                font=("Arial", 25, "bold"),
                text_color="#003728"
            ).pack(pady=20)

        
        for item_id, cart_info in user_cart.items():
            item = cart_info['item_data']
            quantity = cart_info['quantity']
            
            name = item[MENU_NAME_IDX]
            price = item[MENU_PRICE_IDX]
            stock = item[MENU_AMOUNT_IDX]
            item_total = price * quantity
            total_pay += item_total

            row_frame = customtkinter.CTkFrame(
                scroll_frame, 
                fg_color="#ffffff", 
                height=60, 
                corner_radius=10
            )
            row_frame.pack(fill="x", expand=True, pady=5, padx=10)

            
            # ชื่อ
            customtkinter.CTkLabel(row_frame, text=name, font=("THSarabunNew", 30, "bold"), text_color="#003728") \
                .place(x=20, y=30, anchor="w")
            
            # ราคา 
            customtkinter.CTkLabel(row_frame, text=f"{price:,.2f} ฿", font=("Arial", 20), text_color="#417c49") \
                .place(x=350, y=30, anchor="w")
            
            # ปุ่มลบ
            customtkinter.CTkLabel(row_frame, text="x", font=("Arial", 20, "bold"), text_color="#aaaaaa") \
                .place(x=470, y=30, anchor="w")

            # ปุ่มลด
            btn_minus = customtkinter.CTkButton(
                row_frame, text="-", font=("Arial", 20, "bold"), text_color="#FFFFFF",
                fg_color="#799841", hover_color="#709036", width=35, height=35, corner_radius=17,
                command=lambda i=item_id: handle_decrease(i)
            )
            btn_minus.place(x=580, y=30, anchor="center")

            # จำนวน
            qty_label = customtkinter.CTkLabel(row_frame, text=str(quantity), font=("Arial", 22, "bold"), text_color="#003728")
            qty_label.place(x=640, y=30, anchor="center")

            # ปุ่มเพิ่ม
            btn_plus = customtkinter.CTkButton(
                row_frame, text="+", font=("Arial", 20, "bold"), text_color="#FFFFFF",
                fg_color="#799841", hover_color="#709036", width=35, height=35, corner_radius=17,
                command=lambda i=item_id, s=stock: handle_increase(i, s)
            )
            btn_plus.place(x=700, y=30, anchor="center")

            # ราคารวม 
            customtkinter.CTkLabel(row_frame, text=f"{item_total:,.2f} ฿", font=("Arial", 22, "bold"), text_color="#003728") \
                .place(x=900, y=30, anchor="w")
            
            # ปุ่มลบ (ถังขยะ)
            btn_delete = customtkinter.CTkButton(
                row_frame, text="❌", font=("Arial", 25), text_color="#f11c0c",
                fg_color="transparent", hover_color="#f0f0f0", width=40,
                command=lambda i=item_id: handle_delete(i)
            )
            btn_delete.place(x=1220, y=30, anchor="center")

        total_label.configure(text=f"Total Pay {total_pay:,.2f} ฿")

    def handle_decrease(item_id):
        global user_cart
        if item_id in user_cart:
            user_cart[item_id]['quantity'] -= 1
            if user_cart[item_id]['quantity'] == 0:
                del user_cart[item_id] 
        refresh_display()

    def handle_increase(item_id, stock):
        global user_cart
        if item_id in user_cart:
            if user_cart[item_id]['quantity'] < stock:
                user_cart[item_id]['quantity'] += 1
            else:
                messagebox.showwarning("Stock Limit", f"มีสินค้าในสต็อกเพียง {stock} ชิ้น")
        refresh_display()

    def handle_delete(item_id):
        global user_cart
        if item_id in user_cart:
            if messagebox.askyesno("Confirm Delete", "คุณต้องการลบรายการนี้ใช่หรือไม่?"):
                del user_cart[item_id]
        refresh_display()

    def handle_send_order():
        global user_cart
        if not user_cart:
            messagebox.showerror("Error", "ตะกร้าสินค้าว่างเปล่า")
            return
            

        total_pay = 0.0
        for item_id, cart_info in user_cart.items():

            item_price = cart_info['item_data'][MENU_PRICE_IDX] 
            quantity = cart_info['quantity']
            total_pay += (item_price * quantity)
            
        create_pay_page(root, bg_images, user_data, table_number, total_pay)

    btn_style_footer = {"font": ("Arial", 25, "bold"), "text_color": "#003728", "fg_color": "#bbd106", "hover_color": "#a0b507", "width": 195, "height": 62, "corner_radius": 20}

    back_btn = customtkinter.CTkButton(
        background_label, text="Back", **btn_style_footer,
        command=lambda: create_menu_page(root, bg_images, user_data, table_number)
    )
    back_btn.place(x=95, y=730) 

    send_order_btn = customtkinter.CTkButton(
        background_label, text="Send Order", **btn_style_footer,
        command=handle_send_order
    )
    send_order_btn.place(x=1247, y=730) 

    refresh_display()
    
    create_nav_button(background_label, bg_images, rebuild_this_page_func) # <--- (MODIFIED)

    
# -----------------------------------------------
# --- *** PAY PAGE *** ---
# -----------------------------------------------

def create_pay_page(root, bg_images, user_data, table_number, total_pay):
    """
    *** ฟังก์ชันใหม่สำหรับหน้าจ่ายเงิน (Pay) ***
    """
    global user_cart
    for widget in root.winfo_children(): widget.destroy()

    if 'pay' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'pay'"); 
        create_cart_page(root, bg_images, user_data, table_number) 
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['pay'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    customtkinter.CTkLabel(
        background_label, 
        text=f" {table_number}", 
        font=("Arial", 40, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106" 
    ).place(x=245, y=54) 

    slip_path_var = tk.StringVar(value="")
    slip_image_cache = None 

    
    QR_CODE_SIZE = 330 
    
    qr_code_img_ctk = None
    qr_path = image_paths.get('qr_code') 
    
    if qr_path and os.path.exists(qr_path):
        try:
            img_pil = Image.open(qr_path).convert("RGBA")
            img_resized = img_pil.resize((QR_CODE_SIZE, QR_CODE_SIZE), Image.Resampling.LANCZOS)
            
            qr_code_img_ctk = customtkinter.CTkImage(
                light_image=img_resized, 
                dark_image=img_resized, 
                size=(QR_CODE_SIZE, QR_CODE_SIZE)
            )
        except Exception as e:
            print(f"Error loading QR code: {e}")
    
    if qr_code_img_ctk:
        qr_label = customtkinter.CTkLabel(background_label, text="", image=qr_code_img_ctk)
        qr_label.place(x=270, y=345) 
    else:
        customtkinter.CTkLabel(background_label, text="QR Code Error", font=("Arial", 20)) \
            .place(x=200, y=350)
    # --- END NEW ---
    

    # --- Slip Placeholder ---
    slip_placeholder_img = None
    if 'default_slip' in bg_images:
        slip_placeholder_img = bg_images['default_slip']

    slip_image_label = customtkinter.CTkLabel(background_label, text="", image=slip_placeholder_img, fg_color="#bbd106",width=288, height=330)
   
    slip_image_label.place(x=952, y=348) 

    
    def browse_slip():
        nonlocal slip_image_cache
        file_path = filedialog.askopenfilename(title="เลือกสลิปโอนเงิน", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            slip_path_var.set(file_path)
            
            try:
                img_pil = Image.open(file_path).convert("RGBA")
                img_resized = img_pil.resize((285, 330), Image.Resampling.LANCZOS) 
                slip_image_cache = customtkinter.CTkImage(light_image=img_resized, dark_image=img_resized, size=(285, 330))
                
                slip_image_label.configure(image=slip_image_cache)
            except Exception as e:
                messagebox.showerror("Error", f"ไม่สามารถโหลดรูปสลิป: {e}")
                slip_path_var.set("")

    
    customtkinter.CTkButton(
        background_label, text="Browse",
        font=("Arial", 18, "bold"), text_color="#003728", 
        fg_color="#bbd106", hover_color="#a0b507",
        width=110, height=32, corner_radius=30,
        command=browse_slip
    ).place(x=1190, y=692)

    
    def handle_confirm():
        slip_path = slip_path_var.get()
        if not slip_path:
            messagebox.showerror("Error", "กรุณาแนบสลิปการโอนเงินก่อนยืนยืน")
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = os.path.splitext(slip_path)[1]
            new_slip_name = f"slip_{user_data[USER_ID_IDX]}_{table_number}_{timestamp}{file_extension}"
            dest_slip_path = os.path.join(SLIP_IMG_FOLDER, new_slip_name)
            
            shutil.copy(slip_path, dest_slip_path) 

            new_order_id = create_new_order(
                user_id=user_data[USER_ID_IDX],
                table_number=table_number,
                total_price=total_pay,
                slip_path=dest_slip_path,
                cart_items=user_cart
            )
            
            if new_order_id:
                messagebox.showinfo("Success", "ยืนยันการสั่งซื้อสำเร็จ! ออเดอร์ของคุณกำลังถูกจัดเตรียม")
                user_cart.clear() 
                create_your_order_page(root, bg_images, user_data, table_number)
            else:
                messagebox.showerror("Error", "เกิดข้อผิดพลาดในการบันทึกออเดอร์")

        except Exception as e:
            messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {e}")

   
    btn_style_footer = {"font": ("Arial", 25, "bold"), "text_color": "#003728", "fg_color": "#bbd106", "hover_color": "#a0b507", "width": 195, "height": 62, "corner_radius": 20}

    customtkinter.CTkButton(
        background_label, text="Back", **btn_style_footer,
        command=lambda: create_cart_page(root, bg_images, user_data, table_number) 
    ).place(x=110, y=750)

    customtkinter.CTkLabel(
        background_label, text=f"Total {total_pay:,.2f} ฿",
        font=("Arial", 40, "bold"), 
        text_color="#003728", 
        fg_color="#ebf3c7"
    ).place(x=350, y=760)

    customtkinter.CTkButton(
        background_label, text="Confirm", **btn_style_footer,
        command=handle_confirm
    ).place(x=1247, y=750)

    create_nav_button(background_label, bg_images, lambda: create_pay_page(root, bg_images, user_data, table_number, total_pay))

def generate_pdf_receipt(order_id, user_data, logo_path):
    """
    สร้างใบเสร็จรับเงินเป็นไฟล์ PDF
    (MODIFIED: เปลี่ยนจากการสุ่มเลข เป็นการดึง order_no จาก DB)
    """
    # 1. ดึงข้อมูล
    order_data = get_order_details(order_id)
    order_items = get_order_items(order_id)

    if not order_data:
        messagebox.showerror("Error", "ไม่พบข้อมูลออเดอร์")
        return

    
    formatted_order_no = ""
    
    if len(order_data) > ORDER_NO_IDX and order_data[ORDER_NO_IDX]:
        formatted_order_no = order_data[ORDER_NO_IDX]
    else:
    
        formatted_order_no = f"ID{order_id:06d}"
    # --- (END MODIFIED) ---

    table_num = order_data[ORDER_TABLE_NUM_IDX]
    total_price = order_data[ORDER_TOTAL_IDX]

    try:
        order_time_dt = datetime.strptime(order_data[ORDER_TIME_IDX], "%Y-%m-%d %H:%M:%S")
        formatted_time = order_time_dt.strftime("%d/%m/%Y %H:%M pm")
    except ValueError:
        formatted_time = order_data[ORDER_TIME_IDX]

    price_before_vat = total_price / 1.07
    vat_amount = total_price - price_before_vat

 
    temp_dir = tempfile.gettempdir() 
    file_path = os.path.join(temp_dir, f"receipt_{formatted_order_no}.pdf")

    
    try:
        receipt_width = 8 * cm
        receipt_height = 29.7 * cm 
        custom_pagesize = (receipt_width, receipt_height)
        
        c = canvas.Canvas(file_path, pagesize=custom_pagesize)
        width, height = custom_pagesize

        
        margin = 0.5 * cm 
        x_center = width / 2
        x_left = margin
        x_right = width - margin

        y = height - (1 * cm) 

    
        c.setFont('Thai-Bold', 16) 
        c.drawCentredString(x_center, y, "ใบเสร็จรับเงิน")
        y -= 0.8 * cm 

        c.setFont('Thai-Bold', 20) 
        c.drawCentredString(x_center, y, "ร้าน Baimon Herb Cafe'")
        y -= 0.6 * cm 

        c.setFont('Thai-Regular', 10) 
        c.drawCentredString(x_center, y, "สาขากังสดาล จ.ขอนแก่น 40000")
        y -= 0.4 * cm 
        c.drawCentredString(x_center, y, "โทร : 083-451-3077")
        y -= 0.7 * cm 

        c.line(x_left, y, x_right, y) 
        y -= 0.6 * cm 

        # --- ส่วนข้อมูลออเดอร์ ---
        c.setFont('Thai-Regular', 10) 
        c.drawString(x_left, y, f"เลขที่/Order No. : {formatted_order_no}") 
        y -= 0.6 * cm # <--- Spacing changed
        c.drawString(x_left, y, f"โต๊ะ/Table : {table_num}")
        y -= 0.6 * cm # <--- Spacing changed
        c.drawString(x_left, y, f"วันที่/Date : {formatted_time}")
        y -= 0.8 * cm # <--- Spacing changed


        c.setFont('Thai-Bold', 10) 
        c.line(x_left, y+ (0.2*cm), x_right, y+ (0.2*cm))
        c.drawString(x_left, y, "No.")
        c.drawString(x_left + (0.8 * cm), y, "Item")
        c.drawRightString(x_right - (3.5 * cm), y, "Qty")
        c.drawRightString(x_right - (1.5 * cm), y, "Price")
        c.drawRightString(x_right, y, "Amount")
        y -= 0.2 * cm
        c.line(x_left, y, x_right, y)
        y -= 0.5 * cm 

        
        c.setFont('Thai-Regular', 10) 
        for i, item in enumerate(order_items):
            name, qty, price_per_item = item
            amount = qty * price_per_item

            c.drawString(x_left, y, str(i + 1))
            c.drawString(x_left + (0.8 * cm), y, name)
            c.drawRightString(x_right - (3.5 * cm), y, str(qty))
            c.drawRightString(x_right - (1.5 * cm), y, f"{price_per_item:,.2f}")
            c.drawRightString(x_right, y, f"{amount:,.2f}")
            y -= 0.6 * cm 

    
        y -= 0.3 * cm
        c.line(x_left, y, x_right, y)
        y -= 0.6 * cm


        c.setFont('Thai-Regular', 10) 
        c.drawString(x_right - (3.5 * cm), y, "ยอดรวม (Subtotal)")
        c.drawRightString(x_right, y, f"{price_before_vat:,.2f}")
        y -= 0.6 * cm 

        c.setFont('Thai-Regular', 10)
        c.drawString(x_right - (3.5 * cm), y, "ภาษีมูลค่าเพิ่ม (VAT 7%)")
        c.drawRightString(x_right, y, f"{vat_amount:,.2f}")
        y -= 0.2 * cm
        c.line(x_right - (3.5 * cm), y, x_right, y) 
        y -= 0.6 * cm

        c.setFont('Thai-Bold', 12)
        c.drawString(x_right - (3.5 * cm), y, "รวมทั้งสิ้น (Total)")
        c.drawRightString(x_right, y, f"{total_price:,.2f}") 
        y -= 0.2 * cm
        c.line(x_right - (3.5 * cm), y, x_right, y)
        c.line(x_right - (3.5 * cm), y - (0.1*cm), x_right, y- (0.1*cm))
        # --- (END MODIFIED) ---

        
        y -= 2 * cm 
        c.setFont('Thai-Bold', 12) 
        c.drawCentredString(x_center, y, "ขอบคุณค่ะ/Thank you :)")

        c.showPage()
        c.save()

        try:
            webbrowser.open(f"file://{os.path.abspath(file_path)}")
        except Exception as open_e:
            messagebox.showwarning("PDF Success", f"บันทึกใบเสร็จที่ {file_path} สำเร็จ แต่ไม่สามารถเปิดอัตโนมัติได้: {open_e}")

    except Exception as e:
        messagebox.showerror("PDF Error", f"ไม่สามารถสร้างไฟล์ PDF ได้: {e}")

# -----------------------------------------------
# --- *** YOUR ORDER PAGE *** ---
# -----------------------------------------------

def create_your_order_page(root, bg_images, user_data, table_number):
    """
    *** MODIFIED: หน้าดูออเดอร์ (Your Order) ***
    (แสดงออเดอร์ทั้งหมด, ทั้งที่กำลังทำและเสิร์ฟแล้ว)
    (MODIFIED: เพิ่ม Order No. และปรับเลย์เอาต์)
    """
    for widget in root.winfo_children(): widget.destroy()

    if 'your_order' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'your_order'"); 
        create_menu_page(root, bg_images, user_data, table_number) 
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['your_order'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # 1. Header (เหมือนเดิม)
    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=70)
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_your_order_page(root, bg_images, user_data, table_number)

    customtkinter.CTkButton(
        background_label, image=profile_button_image, text="", 
        fg_color="transparent", hover_color="#a0b507", 
        width=70, height=70, corner_radius=0, border_width=0, 
        # <--- (MODIFIED) ส่ง lambda ไปให้หน้า Profile
        command=lambda: create_profile_page(root, bg_images, user_data, rebuild_this_page_func)
    ).place(x=38, y=40) 
    
    customtkinter.CTkLabel(
        background_label, text=f" {table_number}", 
        font=("Arial", 40, "bold"), text_color="#003728", fg_color="#bbd106"
    ).place(x=245, y=54) 
    
    
    scroll_frame = customtkinter.CTkScrollableFrame(
        background_label,
        fg_color="#ebf3c7", 
        bg_color="#ebf3c7",
        corner_radius=20,
        width=1300, 
        height=480 
    )
    scroll_frame.place(x=90, y=240)

    
    all_orders = get_all_orders_for_table(user_data[USER_ID_IDX], table_number)

    if not all_orders:
        customtkinter.CTkLabel(
            scroll_frame, text="ไม่พบประวัติการสั่งอาหาร",
            font=("Arial", 25, "bold"), text_color="#003728"
        ).pack(pady=20)
    else:
        for order_data in all_orders:
            
            order_id = order_data[ORDER_ID_IDX]
            status = order_data[ORDER_STATUS_IDX]
            order_time_str = order_data[ORDER_TIME_IDX]
            total_price = order_data[ORDER_TOTAL_IDX]
            
            
            order_no_str = ""
            if len(order_data) > ORDER_NO_IDX and order_data[ORDER_NO_IDX]:
                order_no_str = order_data[ORDER_NO_IDX]
            else:
                order_no_str = f"ID{order_id:06d}" 
            
            
            try:
                order_time_dt = datetime.strptime(order_time_str, "%Y-%m-%d %H:%M:%S")
                formatted_time = order_time_dt.strftime("%d/%m/%Y %H:%M pm")
            except ValueError:
                formatted_time = order_time_str 
 
            order_block_frame = customtkinter.CTkFrame(
                scroll_frame,
                fg_color="#ffffff", 
                corner_radius=20
            )
            order_block_frame.pack(fill="x", expand=True, pady=(0, 15), padx=10) 

 
            order_items = get_order_items(order_id)
            item_index = 1
            
            for item in order_items:
                name, qty, price_per_item = item
                item_total = price_per_item * qty

                
                item_row_frame = customtkinter.CTkFrame(
                    order_block_frame, fg_color="transparent", height=30
                )
                item_row_frame.pack(fill="x", expand=True, pady=(10, 5), padx=20)
                
                
                customtkinter.CTkLabel(item_row_frame, text=f"{item_index}.", font=("THSarabunNew", 30, "bold"), text_color="#003728") \
                    .place(relx=0.01, rely=0.5, anchor="w")
                customtkinter.CTkLabel(item_row_frame, text=name, font=("THSarabunNew", 30, "bold"), text_color="#003728") \
                    .place(relx=0.05, rely=0.5, anchor="w")
                
                customtkinter.CTkLabel(item_row_frame, text=f"{price_per_item:,.2f} ฿", font=("Arial", 20), text_color="#417c49") \
                    .place(relx=0.60, rely=0.5, anchor="w") 
                
                customtkinter.CTkLabel(item_row_frame, text="x", font=("Arial", 20, "bold"), text_color="#aaaaaa") \
                    .place(relx=0.70, rely=0.5, anchor="w") 
                
                customtkinter.CTkLabel(item_row_frame, text=str(qty), font=("Arial", 22, "bold"), text_color="#003728") \
                    .place(relx=0.75, rely=0.5, anchor="center") 
                
                customtkinter.CTkLabel(item_row_frame, text=f"{item_total:,.2f} ฿", font=("Arial", 22, "bold"), text_color="#003728") \
                    .place(relx=0.90, rely=0.5, anchor="w") 
                
                item_index += 1

 
            footer_frame = customtkinter.CTkFrame(
                order_block_frame, fg_color="transparent"
            )
            footer_frame.pack(fill="x", expand=True, pady=(15, 20), padx=20)
            
            footer_frame.grid_columnconfigure(0, weight=2)
            footer_frame.grid_columnconfigure(1, weight=1) 
            footer_frame.grid_columnconfigure(2, weight=1) 

            
            left_frame = customtkinter.CTkFrame(footer_frame, fg_color="transparent")
            left_frame.grid(row=0, column=0, sticky="w") 

            status_color = "#f5b000" if status == "In the Kitchen"  else "#1efb16" 
            
            
            status_line_frame = customtkinter.CTkFrame(left_frame, fg_color="transparent")
            status_line_frame.pack(anchor="w")
            customtkinter.CTkLabel(status_line_frame, text="Status :", font=("Arial", 18, "bold"), text_color="#003728").pack(side="left")
            customtkinter.CTkLabel(status_line_frame, text=status, font=("Arial", 16, "bold"), text_color="#003728", fg_color=status_color, corner_radius=10, width=120, height=30).pack(side="left", padx=5)

            
            customtkinter.CTkLabel(left_frame, text=f"Order Time : {formatted_time}", font=("Arial", 18, "bold"), text_color="#003728").pack(anchor="w", pady=(5,0))

            def handle_download_check(oid=order_id, udata=user_data):
                logo_path = image_paths.get('logo')

                if not logo_path or not os.path.exists(logo_path):
                    messagebox.showwarning(
                        "Logo Not Found",
                        f"ไม่พบไฟล์โลโก้ที่: {logo_path}\n\n"
                        "ใบเสร็จจะถูกสร้างโดยไม่มีโลโก้"
                           )
                    logo_path = '' 

                generate_pdf_receipt(oid, udata, logo_path)
            
            # --- (NEW) สร้างเฟรมสำหรับคอลัมน์กลาง (เลข + ปุ่ม) ---
            middle_frame = customtkinter.CTkFrame(footer_frame, fg_color="transparent")
            middle_frame.grid(row=0, column=1, sticky="e")

            # Label สำหรับ Order No.
            customtkinter.CTkLabel(
                middle_frame,
                text=f"No. {order_no_str}",
                font=("Arial", 16, "bold"), 
                text_color="#003728",
                anchor="e"
            ).pack(anchor="e", pady=(0, 2)) # วางไว้ด้านบน

            
            customtkinter.CTkButton(
                middle_frame, 
                text="Download Check",
                font=("Arial", 16, "bold"), text_color="#003728", 
                fg_color="#bbd106", hover_color="#a0b507",
                width=160, height=40, corner_radius=20,
                command=lambda oid=order_id: handle_download_check(oid, user_data)
            ).pack(anchor="e") 
            
            customtkinter.CTkLabel(footer_frame, text=f"{total_price:,.2f} ฿", font=("Arial", 35, "bold"), text_color="#003728") \
                .grid(row=0, column=2, sticky="e", padx=10) 
            
            
    customtkinter.CTkButton(
        background_label, text="Back to Menu",
        font=("Arial", 25, "bold"), text_color="#003728", 
        fg_color="#bbd106", hover_color="#a0b507",
        width=195, height=62, corner_radius=20,
        command=lambda: create_menu_page(root, bg_images, user_data, table_number)
    ).place(x=95, y=750) 
    
    create_nav_button(background_label, bg_images, rebuild_this_page_func) # <--- (MODIFIED)



def create_menu_page(root, bg_images, user_data, table_number):
    for widget in root.winfo_children(): widget.destroy()
    if 'menudrink' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'menudrink'")
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['menudrink'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    scrollable_menu_frame = customtkinter.CTkScrollableFrame(
        background_label, 
        fg_color="#ebf3c7",
        corner_radius=10,
        width=int(857 * 1.604),  
        height=int(320 * 1.546)  
    )
    scrollable_menu_frame.place(x=64, y=278) 
    
    # --- (จบส่วน Scrollbar) ---

    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=70) 
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_menu_page(root, bg_images, user_data, table_number)

    profile_btn = customtkinter.CTkButton(
        background_label, 
        image=profile_button_image, 
        text="",
        fg_color="transparent",
        hover_color="#a0b507",
        width=70, 
        height=70, 
        corner_radius=0, 
        border_width=0,
        # <--- (MODIFIED) ส่ง lambda ไปให้หน้า Profile
        command=lambda: create_profile_page(root, bg_images, user_data, rebuild_this_page_func)
    )
    profile_btn.place(x=38, y=40) 
    
    customtkinter.CTkLabel(
        background_label, 
        text=f" {table_number}", 
        font=("Arial", 40, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106" 
    ).place(x=245, y=54) 
    
    cart_btn_header = customtkinter.CTkButton(
        background_label, text="🛒 Cart", 
        font=("Arial", 25, "bold"), text_color="#003728", 
        fg_color="#bbd106", hover_color="#a0b507",
        width=145, height=66, corner_radius=30,
        
        command=lambda: create_cart_page(root, bg_images, user_data, table_number) 
    )
    cart_btn_header.place(x=1335, y=42) 

    
    def switch_category(category):
        display_menu_items(root, category, bg_images, scrollable_menu_frame, user_data, table_number)

    customtkinter.CTkButton(
        background_label, 
        text="Drinks", 
        font=("Arial", 25, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=193, 
        height=62,
        command=lambda: switch_category('Drinks')
    ).place(x=460, y=189) 
    
    customtkinter.CTkButton(
        background_label, 
        text="Dessert", 
        font=("Arial", 25, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=193, 
        height=62, 
        command=lambda: switch_category('Dessert')
    ).place(x=669, y=189) 
    
    customtkinter.CTkButton(
        background_label, 
        text="Food", 
        font=("Arial", 25, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=193, 
        height=62, 
        command=lambda: switch_category('Food')
    ).place(x=877, y=189) 

    switch_category('Drinks')

    create_nav_button(background_label, bg_images, rebuild_this_page_func) # <--- (MODIFIED)


def create_table_page(root, bg_images, user_data): 
    
    global user_cart
    user_cart.clear()

    for widget in root.winfo_children(): widget.destroy()
    
    
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['table'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    active_tables = get_active_tables()
    
    selected_table = tk.IntVar(); selected_table.set(0)
    table_names = ["1", "2", "3", "4"]
    button_width = int(124 * 1.604); button_height = int(133 * 1.546) 
    start_x = int(156 * 1.604); spacing = int(39 * 1.605) 
    
    table_buttons = [] 
    
    color_normal = "#ebf3c7"
    color_hover = "#a0b507"
    color_selected = "#d1f680" 
    color_text = "#417c49"
    
    color_disabled_bg = "#b0b0b0"   
    color_disabled_text = "#606060" 

    def select_table(selected_num):
        selected_table.set(selected_num)

        for i, btn in enumerate(table_buttons):
            table_num_in_loop = i + 1
            
            if table_num_in_loop in active_tables:
                continue 
                
            if table_num_in_loop == selected_num:
                btn.configure(fg_color=color_selected) 
            else:
                btn.configure(fg_color=color_normal) 
    
    for i, num in enumerate(table_names):
        x = start_x + i * (button_width + spacing)
        table_num_int = int(num) 

        is_active = table_num_int in active_tables

        if is_active:
            btn_state = "disabled"              
            btn_fg_color = color_disabled_bg    
            btn_text_color = color_disabled_text
            btn_hover_color = color_disabled_bg 
            btn_command = None                  
            btn_text = f"Table\n{num}\n(In Use)" 
        else:
            btn_state = "normal"                
            btn_fg_color = color_normal
            btn_text_color = color_text
            btn_hover_color = color_hover
            btn_command = lambda n=table_num_int: select_table(n)
            btn_text = f"Table\n{num}"
            
        btn = customtkinter.CTkButton(
            background_label, 
            text=btn_text,                  
            font=("Arial", 24, "bold"), 
            text_color=btn_text_color,      
            fg_color=btn_fg_color,          
            hover_color=btn_hover_color,    
            border_width=0, 
            corner_radius=15,       
            width=button_width,       
            height=button_height,       
            state=btn_state,                
            command=btn_command             
        )
        btn.place(x=x, y=363) 
        table_buttons.append(btn) 
            
    def handle_next():
        table_num = selected_table.get()
        if table_num > 0: 
            if table_num in active_tables:
                 messagebox.showerror("Error", "โต๊ะนี้ถูกใช้งานอยู่ กรุณาเลือกโต๊ะอื่น")
            else:
                global current_table_number 
                current_table_number = table_num 
                create_menu_page(root, bg_images, user_data, table_num) 
        else: 
            messagebox.showerror("Error", "กรุณาเลือกโต๊ะก่อน")

    customtkinter.CTkButton(
        background_label, 
        text="Next", 
        font=("Arial", 25, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        width=210,    
        height=74,    
        command=handle_next 
    ).place(x=630, y=683) 

    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=70) 
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_table_page(root, bg_images, user_data)
    
    profile_btn = customtkinter.CTkButton(
        background_label, 
        image=profile_button_image, 
        text="",         
        fg_color="transparent", 
        hover_color="#a0b507",  
        width=48,     
        height=70,      
        corner_radius=0, 
        border_width=0,
        # <--- (MODIFIED) ส่ง lambda ไปให้หน้า Profile
        command=lambda: create_profile_page(root, bg_images, user_data, rebuild_this_page_func)
    )
    profile_btn.place(x=38, y=40) 
    
    customtkinter.CTkButton(
        background_label, 
        text="Log Out", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=193,      
        height=62,      
        command=lambda: create_main_page(root, bg_images)
    ).place(x=1283, y=31) 
    
    create_nav_button(background_label, bg_images, rebuild_this_page_func) # <--- (MODIFIED)


def create_profile_page(root, bg_images, user_data, prev_page_func): # <--- (MODIFIED) เพิ่ม prev_page_func
    """
    *** ฟังก์ชันที่ถูกถามถึง (NameError) ***
    (ปรับปรุงเป็น CustomTkinter)
    """
    for widget in root.winfo_children(): widget.destroy()
    if 'profile' not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพ 'profile'"); return
    
    background_label = customtkinter.CTkLabel(root, image=bg_images['profile'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    username = user_data[USERNAME_IDX]; first_name = user_data[FIRST_NAME_IDX]; last_name = user_data[LAST_NAME_IDX]
    phone_number = user_data[PHONE_NUMBER_IDX] if user_data[PHONE_NUMBER_IDX] else "-"; email = user_data[EMAIL_IDX] if user_data[EMAIL_IDX] else "-"
    birth_date = user_data[BIRTH_DATE_IDX] if user_data[BIRTH_DATE_IDX] else "-"; pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data[PROFILE_PIC_PATH_IDX] else ""; points = 14 
    text_font = ("Arial", 22, "bold"); text_fg = "#003728"; text_bg = "#ffffff" 
    
    def create_info_label(text, x, y, anchor="w", width=300, height=46): 
        customtkinter.CTkLabel(background_label,
                                text=text,
                                font=text_font,
                                text_color=text_fg,
                                fg_color=text_bg,
                                anchor=anchor,
                                width=width, 
                                height=height
        ).place(x=x, y=y)
    
    load_and_display_profile_pic(root, pic_path, 'default_profile_pic', 77, 289, size=250) 
    
    
    customtkinter.CTkButton(background_label,
                            text="Edit",
                            font=("Arial", 20, "bold"),
                            text_color="#003728",
                            fg_color="#bbd106",
                            hover_color="#a0b507",
                            border_width=0,
                            width=70, 
                            height=46,
                            # <--- (MODIFIED) ส่ง prev_page_func ต่อไปให้หน้า Edit
                            command=lambda: create_edit_profile_page(root, bg_images, user_data, prev_page_func)
    ).place(x=83, y=47) 
    
    create_info_label(f"Username : {username}", 321, 247, width=802) 
    create_info_label(f"Frist Name : {first_name}", 321, 309, width=481) 
    create_info_label(f"Last Name : {last_name}", 898, 309, width=481) 
    create_info_label(f"Phone Number : {phone_number}", 321, 371, width=545) 
    create_info_label(f"BirthDate : {birth_date}", 898, 371, width=401) 
    create_info_label(f"Email : {email}", 321, 433, width=802) 

    customtkinter.CTkButton(background_label,
                            text="Log out",
                            font=("Arial", 25, "bold"),
                            text_color="#ffffff",
                            fg_color="#417c49",
                            hover_color="#2c5432",
                            border_width=0,
                            width=321, 
                            height=66,
                            command=lambda: create_main_page(root, bg_images)
    ).place(relx=0.5, y=630, anchor="center") 
    

    customtkinter.CTkButton(background_label,
                            text="Back",
                            font=("Arial", 25, "bold"),
                            text_color="#003728",
                            fg_color="#bbd106",
                            hover_color="#a0b507",
                            border_width=0,
                            width=321, 
                            height=66,
                            command=prev_page_func # <--- (MODIFIED) ใช้ prev_page_func ที่รับมา
    ).place(relx=0.5, y=720, anchor="center") 
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_profile_page(root, bg_images, user_data, prev_page_func)
    create_nav_button(root, bg_images, rebuild_this_page_func)


def create_edit_profile_page(root, bg_images, user_data, prev_page_func): # <--- (MODIFIED) เพิ่ม prev_page_func
    """
    *** หน้าแก้ไขโปรไฟล์ ***
    (ปรับปรุงเลย์เอาต์ให้ตรงกับ create_profile_page ที่ขยายสเกลแล้ว)
    """
    for widget in root.winfo_children(): widget.destroy()
    if 'edit_profile' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'edit_profile'"); return
    
    background_label = customtkinter.CTkLabel(root, image=bg_images['edit_profile'], text="")
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    user_id = user_data[USER_ID_IDX]; username = user_data[USERNAME_IDX]
    
 
    first_name = tk.StringVar(value=user_data[FIRST_NAME_IDX])
    last_name = tk.StringVar(value=user_data[LAST_NAME_IDX])
    phone_number = tk.StringVar(value=user_data[PHONE_NUMBER_IDX] if user_data[PHONE_NUMBER_IDX] else "")
    email = tk.StringVar(value=user_data[EMAIL_IDX] if user_data[EMAIL_IDX] else "")
    birth_date = tk.StringVar(value=user_data[BIRTH_DATE_IDX] if user_data[BIRTH_DATE_IDX] else "")
    current_pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data[PROFILE_PIC_PATH_IDX] else ""
    new_pic_path = tk.StringVar(value=current_pic_path)

    entry_font = ("Arial", 22, "bold") 
    entry_font_normal = ("Arial", 22) 
    text_fg = "#003728"
    entry_bg = "#ffffff" 

    def select_profile_picture():
        file_path = filedialog.askopenfilename(title="เลือกรูปภาพโปรไฟล์",filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path: 
            new_pic_path.set(file_path)
            
            load_and_display_profile_pic(background_label, file_path, 'default_profile_pic', 77, 289, size=250)
    
    def handle_save():
        fn = first_name.get(); ln = last_name.get()
        if not (fn and ln): 
            messagebox.showerror("Save Failed", "กรุณากรอกชื่อและนามสกุล"); return
        
        updated_data = update_user_profile(user_id, fn, ln, phone_number.get(), email.get(), birth_date.get(), new_pic_path.get())
        
        if updated_data: 
            messagebox.showinfo("Save Success", "บันทึกข้อมูลเรียบร้อย")
            # <--- (MODIFIED) กลับไปหน้า Profile พร้อมข้อมูลใหม่ และส่ง prev_page_func เดิมกลับไป
            create_profile_page(root, bg_images, updated_data, prev_page_func) 
        else: 
            messagebox.showerror("Error", "เกิดข้อผิดพลาดในการบันทึกข้อมูล")
    
    load_and_display_profile_pic(background_label, current_pic_path, 'default_profile_pic', 77, 289, size=250)
    
 
    customtkinter.CTkButton(background_label,
                            text="Browse💾", 
                            font=("Arial", 18, "bold"),
                            text_color="#003728",
                            fg_color="#bbd106",
                            hover_color="#a0b507",
                            border_width=0,
                            width=70, 
                            height=44,
                            command=select_profile_picture 
    ).place(x=115, y=180) 

    customtkinter.CTkLabel(background_label,
                            text=f"Username : {username}",
                            font=entry_font,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            anchor="w",
                            width=802, 
                            height=46
    ).place(x=321, y=247)

    customtkinter.CTkLabel(background_label, 
                            text="First Name :",
                            font=entry_font,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            anchor="w",
                            width=180,
                            height=46
                            ).place(x=321, y=309)
    
    customtkinter.CTkEntry(background_label,
                            textvariable=first_name,
                            font=entry_font_normal,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            border_width=1,
                            width=481-200-5, 
                            height=46
                            ).place(x=321+200+5, y=309)

    customtkinter.CTkLabel(background_label,
                            text="Last Name :",
                            font=entry_font,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            anchor="w",
                            width=200, 
                            height=46
                            ).place(x=898, y=309)
    
    customtkinter.CTkEntry(background_label,
                            textvariable=last_name,
                            font=entry_font_normal,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            border_width=1,
                            width=481-200-10,
                            height=46
                            ).place(x=898+200+10, y=309)

    vcmd = (background_label.register(lambda P: P.isdigit() or P == ""), '%P')
    customtkinter.CTkLabel(background_label,
                            text="Phone Number :",
                            font=entry_font,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            anchor="w",
                            width=220,
                            height=46
                            ).place(x=321, y=371)
    customtkinter.CTkEntry(background_label,
                            textvariable=phone_number,
                            font=entry_font_normal,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            border_width=1,
                            validate="key",
                            validatecommand=vcmd,
                            width=545-220-10,
                            height=46
                            ).place(x=321+220+10, y=371)

    customtkinter.CTkLabel(background_label,
                            text="BirthDate :",
                            font=entry_font,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            anchor="w",
                            width=150,
                            height=46
                            ).place(x=898, y=371,)
    customtkinter.CTkEntry(background_label,
                            textvariable=birth_date,
                            font=entry_font_normal,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            border_width=1,
                            width=401-150-10,
                            height=46
                            ).place(x=898+150+10, y=371)

    customtkinter.CTkLabel(background_label,
                            text="Email :",
                            font=entry_font,
                            text_color=text_fg,
                            fg_color=entry_bg,
                            anchor="w",
                            width=120, height=46
                            ).place(x=321, y=433)
    customtkinter.CTkEntry(background_label,
                            textvariable=email,
                            font=entry_font_normal, 
                            text_color=text_fg, 
                            fg_color=entry_bg, 
                            border_width=1,
                            width=802-120-10, 
                            height=46
                            ).place(x=321+120+10, y=433)

    customtkinter.CTkButton(background_label,
                                text="Save", 
                                font=("Arial", 25, "bold"),
                                text_color="#003728",
                                fg_color="#bbd106", 
                                hover_color="#a0b507",
                                border_width=0,
                                width=321, 
                                height=66,
                                command=handle_save 
    ).place(relx=0.5, y=636, anchor="center") 
    
    customtkinter.CTkButton(background_label,
                            text="Back",
                            font=("Arial", 25, "bold"),
                            text_color="#003728",
                            fg_color="#bbd106",
                            hover_color="#a0b507",
                            border_width=0,
                            width=321, 
                            height=66,
                            # <--- (MODIFIED) กลับไปหน้า Profile และส่ง prev_page_func เดิมกลับไป
                            command=lambda: create_profile_page(root, bg_images, user_data, prev_page_func)
    ).place(relx=0.5, y=720, anchor="center") 
    
    # <--- (MODIFIED) สร้าง lambda เพื่อย้อนกลับมาที่หน้านี้
    rebuild_this_page_func = lambda: create_edit_profile_page(root, bg_images, user_data, prev_page_func)
    create_nav_button(background_label, bg_images, rebuild_this_page_func)

ORIG_W = 960.0
ORIG_H = 540.0
NEW_W = 1540.0
NEW_H = 835.0

SCALE_W = NEW_W / ORIG_W  
SCALE_H = NEW_H / ORIG_H  
FONT_SCALE = SCALE_H #

def create_forgot_password_page(root, bg_images):
    for widget in root.winfo_children(): widget.destroy()

    if 'forgot_password' not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'forgot_password'"); return

    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['forgot_password'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    # --- SCALED FONT ---
    entry_font = ("Arial", int(22 * FONT_SCALE))
    button_font = ("Arial", int(25 * FONT_SCALE), "bold")

    email_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font, 
        border_width=0,
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=int(343 * SCALE_W),
        height=int(40 * SCALE_H) 
    )
    # --- SCALED PLACE ---
    email_entry.place(x=int(303 * SCALE_W), y=int(212 * SCALE_H)) 
    
    phone_number_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font,
        border_width=0, 
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=int(343 * SCALE_W), 
        height=int(40 * SCALE_H) 
    )
    # --- SCALED PLACE ---
    phone_number_entry.place(x=int(303 * SCALE_W), y=int(282 * SCALE_H)) 

    def handle_submit_verification():
        email = email_entry.get().strip()
        phone_number = phone_number_entry.get().strip()
        
        if not (email and phone_number):
            messagebox.showerror("Error", "กรุณากรอก Email และ Phone Number"); return

        user_data = check_user_by_email_and_phone(email, phone_number)
        
        if user_data:
            messagebox.showinfo("Verification Success", "ยืนยันตัวตนสำเร็จ! กรุณาตั้งรหัสผ่านใหม่")
            create_change_password_page(root, bg_images, user_data) 
        else:
            messagebox.showerror("Verification Failed", "Email หรือ Phone Number ไม่ตรงกับข้อมูลในระบบ")

    
    submit_button = customtkinter.CTkButton(
        background_label, 
        text="Submit", 
        font=button_font, 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0,
        corner_radius=20,
        width=int(200 * SCALE_W), 
        height=int(45 * SCALE_H),
        command=handle_submit_verification
    )
    
    submit_button.place(x=int(380 * SCALE_W), y=int(348 * SCALE_H)) 

    back_button = customtkinter.CTkButton(
        background_label, 
        text="Back", 
        font=button_font, 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        width=int(200 * SCALE_W), 
        height=int(45 * SCALE_H), 
        command=lambda: create_login_page(root, bg_images)
    )
    back_button.place(x=int(380 * SCALE_W), y=int(400 * SCALE_H)) 
    
    create_nav_button(background_label, bg_images, lambda: create_change_password_page(root, bg_images))


def create_change_password_page(root, bg_images, user_data):
    for widget in root.winfo_children(): widget.destroy()

    if 'change_password' not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'change_password'"); return

    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['change_password'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    user_id = user_data[USER_ID_IDX]
    
    entry_font = ("Arial", int(25 * FONT_SCALE))
    button_font = ("Arial", int(25 * FONT_SCALE), "bold")

    new_password_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font, 
        show="*", 
        border_width=0, 
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=int(343 * SCALE_W), 
        height=int(40 * SCALE_H) 
    )
    new_password_entry.place(x=int(303 * SCALE_W), y=int(212 * SCALE_H)) 
    
    confirm_password_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font, 
        show="*", 
        border_width=0, 
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=int(343 * SCALE_W), 
        height=int(40 * SCALE_H)
    )
    # --- SCALED PLACE ---
    confirm_password_entry.place(x=int(303 * SCALE_W), y=int(282 * SCALE_H)) 
    
    def handle_save_password():

        new_pass = new_password_entry.get()
        confirm_pass = confirm_password_entry.get()
        
        if not (new_pass and confirm_pass):
            messagebox.showerror("Error", "กรุณากรอกรหัสผ่านใหม่ให้ครบถ้วน")
            return 

        password_check_result = check_password_strength(new_pass)
        
        if password_check_result != "OK":
            messagebox.showerror("Password Error", password_check_result)
            return
        elif new_pass != confirm_pass:
            messagebox.showerror("Error", "รหัสผ่านใหม่ไม่ตรงกัน")
        else:
            if update_password(user_id, new_pass):
                messagebox.showinfo("Success", "เปลี่ยนรหัสผ่านสำเร็จ! กรุณาเข้าสู่ระบบใหม่")
                create_login_page(root, bg_images) 
            else:
                messagebox.showerror("Error", "ไม่สามารถเปลี่ยนรหัสผ่านได้ กรุณาลองใหม่")

    save_button = customtkinter.CTkButton(
        background_label, 
        text="Save", 
        font=button_font, 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0,
        corner_radius=10,
        width=int(200 * SCALE_W), 
        height=int(45 * SCALE_H), 
        command=handle_save_password
    )
    
    save_button.place(x=int(380 * SCALE_W), y=int(348 * SCALE_H)) 
    
    back_button = customtkinter.CTkButton(
        background_label, 
        text="Back", 
        font=button_font, 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0,
        corner_radius=10,
        width=int(200 * SCALE_W), 
        height=int(45 * SCALE_H), # 
        command=lambda: create_forgot_password_page(root, bg_images) 
    )
    back_button.place(x=int(380 * SCALE_W), y=int(400 * SCALE_H)) 

    create_nav_button(background_label, bg_images, lambda: create_login_page(root, bg_images))


def create_login_page(root, bg_images):
    for widget in root.winfo_children(): widget.destroy()
    
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['login'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    def handle_submit():
        username = username_entry.get()
        password = password_entry.get()
        
        if not username or not password: 
            messagebox.showerror("Login Failed", "กรุณากรอก Username และ Password")
            return
            
        user_data = check_login(username, password)
        
        if user_data:
            if user_data[USER_ID_IDX] == 0 and user_data[USERNAME_IDX] == "adminja":
                messagebox.showinfo("Admin Login", "เข้าสู่ระบบผู้ดูแลระบบสำเร็จ!")
                create_admin_menu_for_admin_page(root, bg_images)
            else:
                messagebox.showinfo("Login Status", "เข้าสู่ระบบสำเร็จ!")
                create_table_page(root, bg_images, user_data) 
        else: 
            messagebox.showerror("Login Failed", "Username หรือ Password ไม่ถูกต้อง")
            
    username_entry = customtkinter.CTkEntry(root, 
                                            font=("Arial", 30), 
                                            fg_color="#ebf3c7",    
                                            text_color="#000000",  
                                            border_width=0,       
                                            corner_radius=0,
                                            width=500, 
                                            height=60)      
    username_entry.place(x=531, y=329)

    
    password_entry = customtkinter.CTkEntry(root, 
                                            font=("Arial", 30), 
                                            show="*", 
                                            fg_color="#ebf3c7",
                                            text_color="#000000",
                                            border_width=0, 
                                            corner_radius=0,
                                            width=500, 
                                            height=60)
    password_entry.place(x=531, y=425)

    submit_button = customtkinter.CTkButton(root, 
                                            text="Submit", 
                                            font=("Arial", 30, "bold"), 
                                            text_color="#003728",    
                                            fg_color="#bbd106",      
                                            hover_color="#a0b507",  
                                            corner_radius=20,       
                                            command=handle_submit,
                                            width=200, 
                                            height=58)
    submit_button.place(x=648, y=534)

    back_button = customtkinter.CTkButton(root, 
                                          text="Back", 
                                          font=("Arial", 30, "bold"),
                                          text_color="#003728",
                                          fg_color="#bbd106",
                                          hover_color="#a0b507",
                                          corner_radius=20,
                                          command=lambda: create_main_page(root, bg_images),
                                          width=200,
                                          height=58) 
    back_button.place(x=648, y=625)

    forgot_button = customtkinter.CTkButton(root,
                                            text="Forgot Password?",
                                            font=("Arial", 18, "underline"),
                                            text_color="#a0b507",
                                            fg_color="transparent", 
                                            hover_color="#f3f6e8", 
                                            corner_radius=20, 
                                            command=lambda: create_forgot_password_page(root, bg_images)) 
    forgot_button.place(x=740, y=750, anchor=tk.CENTER)
    create_nav_button(root, bg_images, lambda: create_login_page(root, bg_images))


def create_main_page(root, bg_images):
    for widget in root.winfo_children(): 
        widget.destroy()
        
    if 'main' not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'main'")
        return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['main'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    login_button = customtkinter.CTkButton(
        background_label, 
        text="Log In", 
        font=("Arial", 25, "bold"),
        fg_color="#bbd106",
        text_color="#003728",
        hover_color="#a0b507",
        border_width=0,
        corner_radius=20,
        command=lambda: create_login_page(root, bg_images),
        width=120,
        height=45 
    )
    login_button.place(x=130, y=430) 
    
    signup_button = customtkinter.CTkButton(
        background_label, 
        text="Sign Up", 
        font=("Arial", 25, "bold"),
        fg_color="#bbd106",
        text_color="#003728",
        hover_color="#a0b507",
        border_width=0,
        corner_radius=20,
        command=lambda: create_signup_page(root, bg_images),
        width=120, 
        height=45 
    )
    signup_button.place(x=275, y=430) 

    create_nav_button(background_label, bg_images, lambda: create_main_page(root, bg_images))


def create_signup_page(root, bg_images):
    for widget in root.winfo_children(): 
        widget.destroy()
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images['signup'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    def validate_phone_number(P): 
        return P.isdigit() or P == ""

    def handle_signup():
        username = username_entry.get()
        password = password_entry.get()
        first_name = first_name_entry.get()
        last_name = last_name_entry.get()
        phone_number = phone_number_entry.get()
        email = email_entry.get()
        birth_date = birth_date_entry.get()

        if not (username and password and first_name and last_name):
            messagebox.showerror("Sign Up Failed", "กรุณากรอก Username, Password, ชื่อ และนามสกุล")
            return 
            
        password_check_result = check_password_strength(password)
        if password_check_result != "OK":
            messagebox.showerror("Sign Up Failed", password_check_result)
            return

    
        if len(phone_number) != 10: 
            messagebox.showerror("Sign Up Failed", "กรุณากรอกเบอร์โทรศัพท์ให้ครบ 10 หลัก")
            return 
            
        if insert_user(username, password, first_name, last_name, phone_number, email, birth_date):
            messagebox.showinfo("Sign Up Success", "สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")
            create_login_page(root, bg_images)
        else: 
            messagebox.showerror("Sign Up Failed", "Username นี้ถูกใช้ไปแล้ว กรุณาเลือก Username ใหม่")

    vcmd = (background_label.register(validate_phone_number), '%P')
    

    entry_font = ("Arial", int(16 * FONT_SCALE))
    button_font = ("Arial", int(16 * FONT_SCALE), "bold")
    
    entry_fg_color = "#ebf3c7"
    entry_text_color = "#000000"
    entry_corner_radius = 0 
    entry_border_width = 0

    # --- SCALED Sizes ---
    entry_width = int(190 * SCALE_W)
    entry_height = int(27 * SCALE_H)
    button_width = int(145 * SCALE_W)
    button_height = int(40 * SCALE_H)

    username_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        height=entry_height, width=entry_width
    )
    username_entry.place(x=int(227 * SCALE_W), y=int(160 * SCALE_H)) 

    password_entry = customtkinter.CTkEntry(
        background_label, # <--- FIXED
        font=entry_font, show="*", fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        height=entry_height, width=entry_width
    )
    password_entry.place(x=int(515 * SCALE_W), y=int(160 * SCALE_H)) 

    first_name_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        height=entry_height, width=entry_width
    )
    first_name_entry.place(x=int(227 * SCALE_W), y=int(204 * SCALE_H)) 

    last_name_entry = customtkinter.CTkEntry(
        background_label, # <--- FIXED
        font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        height=entry_height, width=entry_width
    )
    last_name_entry.place(x=int(515 * SCALE_W), y=int(204 * SCALE_H)) 

    phone_number_entry = customtkinter.CTkEntry(
        background_label,
        font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius, 
        validate="key", validatecommand=vcmd,
        height=entry_height, width=entry_width
    )
    phone_number_entry.place(x=int(360 * SCALE_W), y=int(253 * SCALE_H)) 

    email_entry = customtkinter.CTkEntry(
        background_label, 
        font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        height=entry_height, width=entry_width
    )
    email_entry.place(x=int(360 * SCALE_W), y=int(298 * SCALE_H)) 

    birth_date_entry = customtkinter.CTkEntry(
        background_label, # <--- FIXED
        font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        height=entry_height, width=entry_width
    )
    birth_date_entry.place(x=int(360 * SCALE_W), y=int(343 * SCALE_H)) 
    
    signup_btn = customtkinter.CTkButton(
        background_label, 
        text="Sign up", 
        font=button_font, 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        width=button_width, 
        height=button_height, 
        command=handle_signup
    )
    signup_btn.place(x=int(476 * SCALE_W), y=int(395 * SCALE_H))
    

    back_btn = customtkinter.CTkButton(
        background_label, # <--- FIXED
        text="Back", 
        font=button_font, 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        width=button_width, 
        height=button_height, 
        command=lambda: create_main_page(root, bg_images)
    )
    back_btn.place(x=int(319 * SCALE_W), y=int(395 * SCALE_H))  

    create_nav_button(background_label, bg_images, lambda: create_signup_page(root, bg_images))


image_paths = {
        'main': "D:\\โปรเจ็คของใบหม่อน\\1.png",
        'login': "D:\\โปรเจ็คของใบหม่อน\\2.png",
        'signup': "D:\\โปรเจ็คของใบหม่อน\\3.png",
        'about': "D:\\โปรเจ็คของใบหม่อน\\about.png",
        'table': "D:\\โปรเจ็คของใบหม่อน\\table.png", 
        'profile': "D:\\โปรเจ็คของใบหม่อน\\profile.png", 
        'edit_profile': "D:\\โปรเจ็คของใบหม่อน\\editpf.png", 
        'forgot_password': "D:\\โปรเจ็คของใบหม่อน\\forgotpw.png", 
        'change_password': "D:\\โปรเจ็คของใบหม่อน\\changepw.png",
        'add_to_cart': "D:\\โปรเจ็คของใบหม่อน\\add_to_cart.png", 
        'cart': "D:\\โปรเจ็คของใบหม่อน\\cart.png", 
        'pay': "D:\\โปรเจ็คของใบหม่อน\\pay.png", 
        'your_order': "D:\\โปรเจ็คของใบหม่อน\\yourorder.png", 
        
        #ใบเสร็จ
        'logo': "D:/โปรเจ็คของใบหม่อน/logo.png", 
        'font_regular': "D:\\โปรเจ็คของใบหม่อน\\THSarabunNew.ttf", 
        'font_bold': "D:\\โปรเจ็คของใบหม่อน\\THSarabunNew Bold.ttf",
        
        # Admin & Menu Management
        'order': "D:\\โปรเจ็คของใบหม่อน\\see_order.png", 
        'admin_order_details': "D:\\โปรเจ็คของใบหม่อน\\23.png",
        'editdrinks': "D:\\โปรเจ็คของใบหม่อน\\edit.png",
        'addmenu': "D:\\โปรเจ็คของใบหม่อน\\addmenu.png",
        'editmenu': "D:\\โปรเจ็คของใบหม่อน\\editmenu.png",
        'menudrink': "D:\\โปรเจ็คของใบหม่อน\\menu.png",
        'qr_code': "D:\\โปรเจ็คของใบหม่อน\\qr_code.JPEG",
        'sales_dashboard': "D:\\โปรเจ็คของใบหม่อน\\sales_dashboard.png",
        #'default_slip': "D:\\โปรเจ็คของใบหม่อน\\default_slip.png",
        'admin_menu': "D:\\โปรเจ็คของใบหม่อน\\menu_for_admin.png",
        
        #'default_profile_pic': "D:\\โปรเจ็คของใบหม่อน\\default_profile.png", 
        #'default_profile_pic_small': "D:\\โปรเจ็คของใบหม่อน\\default_profile.png",
        #'default_menu_img': "D:\\โปรเจ็คของใบหม่อน\\default_menu.png", 
    }
# --- ส่วนหลักของโปรแกรม ---
if __name__ == "__main__":

    initialize_db()

    root = customtkinter.CTk()
    root.title("Baimon Herb Cafe")
    root.geometry("1540x835") 
    customtkinter.set_appearance_mode("light")
    customtkinter.set_default_color_theme("green")

    # โหลดรูปภาพทั้งหมด
    bg_images = {}
    try:
        for name, path in image_paths.items():
            if name.startswith('font_') or name == 'logo':
                continue
            
            if os.path.exists(path):
                original_image = Image.open(path).convert("RGBA")
                if name not in ['default_profile_pic', 'default_profile_pic_small', 'default_menu_img']:
                    resized_image = original_image.resize((1540, 835), Image.Resampling.LANCZOS)
                    bg_images[name] = customtkinter.CTkImage(
                        light_image=resized_image, 
                        dark_image=resized_image,  
                        size=(1540, 835)
                    )
            else:
                 print(f"Warning: ไม่พบไฟล์รูปภาพที่: {path}") 
                 
    except FileNotFoundError as e:
        messagebox.showerror("Error", f"ไม่พบไฟล์รูปภาพ: {e.filename} กรุณาตรวจสอบ path"); root.destroy(); exit()
    except Exception as e:
        messagebox.showerror("Error Loading Images", str(e)); root.destroy(); exit()

    register_pdf_fonts(image_paths)
    create_main_page(root, bg_images)
    
    root.geometry("1540x835") 
    root.mainloop()