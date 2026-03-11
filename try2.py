import tkinter as tk
import customtkinter
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import sqlite3
import os

# --- ค่าคงที่/การตั้งค่าฐานข้อมูลและดัชนีข้อมูล ---
DB_NAME = "user_data.db" 
MENU_IMG_FOLDER = "menu_images" 
bg_images = {} 
original_pil_images = {}

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
    try: cursor.execute("SELECT profile_pic_path FROM users LIMIT 1")
    except sqlite3.OperationalError: cursor.execute("ALTER TABLE users ADD COLUMN profile_pic_path TEXT DEFAULT ''")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, first_name TEXT, last_name TEXT, phone_number TEXT, email TEXT, birth_date TEXT, profile_pic_path TEXT DEFAULT '')
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL, amount INTEGER NOT NULL, type TEXT NOT NULL, img_path TEXT DEFAULT '')
    """)
    conn.commit(); conn.close()
    if not os.path.exists(MENU_IMG_FOLDER): os.makedirs(MENU_IMG_FOLDER)

def toggle_fullscreen(event=None):
    is_zoomed = root.state() == 'zoomed'
    root.state('normal' if is_zoomed else 'zoomed')

# (ฟังก์ชัน toggle_fullscreen ของคุณ)

def resize_background_image(event, label_widget, image_name):
    """
    ฟังก์ชันนี้จะถูกเรียกทุกครั้งที่ Label เปลี่ยนขนาด (ผ่าน <Configure>)
    ปรับปรุงใหม่: รักษาสัดส่วนภาพ (Aspect Ratio) และ Crop ส่วนเกิน (Cover)
    """
    if image_name not in original_pil_images:
        return 

    original_pil = original_pil_images[image_name]
    
    new_width = event.width
    new_height = event.height
    
    # ป้องกันการคำนวณตอนหน้าต่างเล็กเกินไป (ตอนเริ่มโปรแกรม)
    if new_width < 50 or new_height < 50:
        return

    try:
        # --- [START] ส่วนตรรกะที่แก้ไขใหม่ ---

        # 1. คำนวณสัดส่วนของภาพต้นฉบับ และหน้าต่างใหม่
        original_ratio = original_pil.width / original_pil.height
        new_ratio = new_width / new_height

        # 2. ตัดสินใจว่าจะยึด "ความกว้าง" หรือ "ความสูง" เป็นหลัก
        if new_ratio > original_ratio:
            # ถ้าหน้าต่างใหม่ "กว้างกว่า" รูปเดิม -> ยึด "ความกว้าง" เป็นหลัก
            scale_factor = new_width / original_pil.width
            resize_width = new_width
            resize_height = int(original_pil.height * scale_factor)
        else:
            # ถ้าหน้าต่างใหม่ "สูงกว่า" (หรือเท่ากับ) รูปเดิม -> ยึด "ความสูง" เป็นหลัก
            scale_factor = new_height / original_pil.height
            resize_height = new_height
            resize_width = int(original_pil.width * scale_factor)

        # 3. Resize ภาพตามสัดส่วนที่คำนวณได้ (ภาพจะใหญ่กว่าหน้าต่างในมิติใดมิติหนึ่ง)
        resized_pil = original_pil.resize((resize_width, resize_height), Image.Resampling.LANCZOS)

        # 4. คำนวณจุดกึ่งกลางเพื่อ Crop
        crop_x = (resize_width - new_width) / 2
        crop_y = (resize_height - new_height) / 2

        # 5. Crop ภาพให้อยู่ตรงกลางและมีขนาดเท่าหน้าต่างพอดี
        #    Box คือ (left, upper, right, lower)
        final_pil_image = resized_pil.crop((
            crop_x,
            crop_y,
            crop_x + new_width,
            crop_y + new_height
        ))
        
        # --- [END] ส่วนตรรกะที่แก้ไขใหม่ ---

        # 6. สร้าง CTkImage จากภาพที่ Crop แล้ว
        new_ctk_image = customtkinter.CTkImage(
            light_image=final_pil_image,  # <-- ใช้ภาพที่ Crop แล้ว
            dark_image=final_pil_image,   # <-- ใช้ภาพที่ Crop แล้ว
            size=(new_width, new_height)
        )
        
        bg_images[image_name] = new_ctk_image 
        label_widget.configure(image=new_ctk_image)
        label_widget.image = new_ctk_image # กันภาพหาย (Good practice)

    except Exception as e:
        # อาจเกิด Error ถ้าผู้ใช้ย่อหน้าต่างจนเล็กจิ๋ว
        print(f"Error resizing {image_name} ({new_width}x{new_height}): {e}")

def insert_user(username, password, first_name, last_name, phone_number, email, birth_date):
    try:
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, first_name, last_name, phone_number, email, birth_date, profile_pic_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (username, password, first_name, last_name, phone_number, email, birth_date, ''))
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
        cursor.execute("UPDATE users SET first_name = ?, last_name = ?, phone_number = ?, email = ?, birth_date = ?, profile_pic_path = ? WHERE id = ?", (first_name, last_name, phone_number, email, birth_date, profile_pic_path, user_id))
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

# --- ฟังก์ชันสำหรับรูปภาพ ---
profile_photo_cache = {}; table_profile_photo_cache = {}

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

# --- ฟังก์ชันสำหรับหน้า About และ Nav Button ---

def create_about_page(root, bg_images, prev_page_func):
    for widget in root.winfo_children(): widget.destroy()
    
    image_name = 'about' # <-- 1. ระบุชื่อรูป
    if image_name not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'about'"); return
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
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
    ).place(x=408, y=478) 


def create_nav_button(parent_widget, bg_images, current_page_func): 
    about_button = customtkinter.CTkButton(
        parent_widget, 
        text="•\n•\n•", 
        font=("Arial", 10, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106",
        hover_color="#1f8b3f", 
        border_width=0,
        corner_radius=5,
        width=24,
        height=40,
        command=lambda: create_about_page(root, bg_images, current_page_func)
    )
    about_button.place(x=925, y=485)


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
    # ...
    image_name = 'editmenu' # <-- 1.
    if image_name not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพ 'editmenu'"); return
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name]) # <-- แก้
    
    # --- 2. เพิ่ม Bind ---
    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    menu_id = menu_data[MENU_ID_IDX]; current_img_path = menu_data[MENU_IMG_PATH_IDX]
    new_img_path = tk.StringVar(value=current_img_path)

    img_size = 150; img_x, img_y = 373, 145; img_label = None
    
    def display_menu_img(path):
        nonlocal img_label
        if img_label: img_label.destroy()
        photo = None
        target_path = path if path and os.path.exists(path) else image_paths.get('default_menu_img')
        if target_path and os.path.exists(target_path):
            original_image = Image.open(target_path); resized_image = original_image.resize((img_size, img_size), Image.Resampling.LANCZOS); photo = ImageTk.PhotoImage(resized_image)
        if photo:
            img_label = tk.Label(root, image=photo, bd=1, relief=tk.SOLID, bg='white'); img_label.image = photo; img_label.place(x=img_x, y=img_y, width=img_size, height=img_size)

    display_menu_img(current_img_path)
    def browse_image():
        file_path = filedialog.askopenfilename(title="เลือกรูปภาพเมนู", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path: new_img_path.set(file_path); display_menu_img(file_path)

    customtkinter.CTkButton(root, text="Browse", font=("Arial", 12, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=browse_image).place(x=535, y=265, width=70, height=25)

    name_var = tk.StringVar(value=menu_data[MENU_NAME_IDX]); price_var = tk.StringVar(value=str(menu_data[MENU_PRICE_IDX])); amount_var = tk.StringVar(value=str(menu_data[MENU_AMOUNT_IDX])); type_var = tk.StringVar(value=menu_data[MENU_TYPE_IDX])
    entry_style = {"font": ("Arial", 16), "bd": 1, "relief": tk.FLAT}

    customtkinter.CTkLabel(root, text="Name :", font=("Arial", 16, "bold"), fg="#003728",bg="white", anchor="w").place(x=240, y=310); customtkinter.CTkEntry(root, bg="#ebf3c7",textvariable=name_var, **entry_style).place(x=318, y=318, width=344, height=20)
    customtkinter.CTkLabel(root, text="Price :", font=("Arial", 16, "bold"), fg="#003728",bg="white", anchor="w").place(x=240, y=340);customtkinter.CTkEntry(root, bg="#ebf3c7",textvariable=price_var, **entry_style).place(x=313, y=346, width=350, height=20)
    customtkinter.CTkLabel(root, text="Amount :", font=("Arial", 16, "bold"), fg="#003728",bg="white", anchor="w").place(x=240, y=370); customtkinter.CTkEntry(root, bg="#ebf3c7",textvariable=amount_var, **entry_style).place(x=342, y=375, width=321, height=20)
    customtkinter.CTkLabel(root, text="Food Type :", font=("Arial", 16, "bold"), fg="#003728",bg="white", anchor="w").place(x=240, y=400)
    type_dropdown = ttk.Combobox(root, textvariable=type_var, values=['Drinks', 'Dessert', 'Food'], font=("Arial", 16), state="readonly"); type_dropdown.place(x=380, y=405, width=150, height=25)

    def handle_save_menu():
        name = name_var.get(); price_str = price_var.get(); amount_str = amount_var.get(); menu_type = type_var.get()
        if not (name and price_str and amount_str and menu_type): messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบถ้วน"); return
        try: price = float(price_str); amount = int(amount_str)
        except ValueError: messagebox.showerror("Error", "ราคาและจำนวนต้องเป็นตัวเลข"); return

        final_img_path = new_img_path.get()
        if final_img_path and final_img_path != current_img_path:
            file_extension = os.path.splitext(final_img_path)[1]; new_filename = f"menu_{menu_id}_{name.replace(' ', '_')}{file_extension}"
            dest_path = os.path.join(MENU_IMG_FOLDER, new_filename)
            try: Image.open(final_img_path).save(dest_path); final_img_path = dest_path
            except Exception as e: messagebox.showwarning("Warning", f"ไม่สามารถคัดลอกรูปภาพ: {e}. ใช้ Path เดิมแทน"); final_img_path = current_img_path
        
        if update_menu_item(menu_id, name, price, amount, menu_type, final_img_path):
            messagebox.showinfo("Success", f"แก้ไขเมนู {name} สำเร็จ"); create_admin_edit_page(root, bg_images, current_category)
        else: messagebox.showerror("Error", "แก้ไขเมนูไม่สำเร็จ")

    customtkinter.CTkButton(root, text="Save", font=("Arial", 18, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=handle_save_menu).place(x=381, y=460, width=180, height=40)
    customtkinter.CTkButton(root, text="Back", font=("Arial", 16, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=lambda: create_admin_edit_page(root, bg_images, current_category)).place(x=40, y=27, width=80, height=35)

#หน้า Add Menu
def create_admin_add_menu_page(root, bg_images, current_category):
    # ...
    image_name = 'addmenu' 
    if image_name not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพ 'addmenu'"); return
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name]) # <-- แก้
    

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    img_size = 150; img_x, img_y = 373, 145; img_label = None; new_img_path = tk.StringVar(value="")
    
    def display_menu_img(path):
        nonlocal img_label
        if img_label: img_label.destroy()
        photo = None
        if path and os.path.exists(path):
            original_image = Image.open(path); resized_image = original_image.resize((img_size, img_size), Image.Resampling.LANCZOS); photo = ImageTk.PhotoImage(resized_image)
        if photo:
            img_label = customtkinter.CTkLabel(root, image=photo, bd=1, relief=tk.SOLID, bg='white'); img_label.image = photo; img_label.place(x=img_x, y=img_y, width=img_size, height=img_size)

    def browse_image():
        file_path = filedialog.askopenfilename(title="เลือกรูปภาพเมนู", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path: new_img_path.set(file_path); display_menu_img(file_path)

    customtkinter.CTkButton(root, text="Browse", font=("Arial", 12, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=browse_image).place(x=535, y=265, width=70, height=25)

    name_var = tk.StringVar(); price_var = tk.StringVar(); amount_var = tk.StringVar(); type_var = tk.StringVar(value=current_category)
    entry_style = {"font": ("Arial", 14), "bd": 1, "relief": tk.FLAT}

    customtkinter.CTkLabel(root, text="Name :", font=("Arial", 16, "bold"), fg="#003728", bg="white", anchor="w").place(x=240, y=310); customtkinter.CTkEntry(root, bg="#ebf3c7", textvariable=name_var, **entry_style).place(x=318, y=318, width=344, height=20)
    customtkinter.CTkLabel(root, text="Price :", font=("Arial", 16, "bold"), fg="#003728", bg="white", anchor="w").place(x=240, y=340); customtkinter.CTkEntry(root, bg="#ebf3c7",textvariable=price_var, **entry_style).place(x=313, y=346, width=350, height=20)
    customtkinter.CTkLabel(root, text="Amount :", font=("Arial", 16, "bold"), fg="#003728", bg="white", anchor="w").place(x=240, y=370); customtkinter.CTkEntry(root, bg="#ebf3c7",textvariable=amount_var, **entry_style).place(x=342, y=375, width=321, height=20)
    customtkinter.CTkLabel(root, text="Food Type :", font=("Arial", 16, "bold"), fg="#003728", bg="white", anchor="w").place(x=240, y=400)

    type_dropdown = ttk.Combobox(root, textvariable=type_var, values=['Drinks', 'Dessert', 'Food'], font=("Arial", 16), state="readonly"); type_dropdown.place(x=380, y=405, width=150, height=25)

    def handle_add_to_menu():
        name = name_var.get(); price_str = price_var.get(); amount_str = amount_var.get(); menu_type = type_var.get(); img_path = new_img_path.get()
        
        if not (name and price_str and amount_str and menu_type and img_path): messagebox.showerror("Error", "กรุณากรอกข้อมูลและเลือกรูปภาพให้ครบถ้วน"); return
        try: price = float(price_str); amount = int(amount_str)
        except ValueError: messagebox.showerror("Error", "ราคาและจำนวนต้องเป็นตัวเลข"); return

        new_menu_id = add_menu_item(name, price, amount, menu_type, '')
        if not new_menu_id: messagebox.showerror("Error", "ไม่สามารถเพิ่มเมนูได้"); return
        
        file_extension = os.path.splitext(img_path)[1]; new_filename = f"menu_{new_menu_id}_{name.replace(' ', '_')}{file_extension}"
        dest_path = os.path.join(MENU_IMG_FOLDER, new_filename)
        
        try:
            Image.open(img_path).save(dest_path)
            update_menu_item(new_menu_id, name, price, amount, menu_type, dest_path)
            messagebox.showinfo("Success", f"เพิ่มเมนู {name} สำเร็จ"); create_admin_edit_page(root, bg_images, menu_type)
        except Exception as e: messagebox.showerror("Error", f"ไม่สามารถคัดลอกรูปภาพและเพิ่มเมนู: {e}")

    customtkinter.CTkButton(root, text="Add to Menu", font=("Arial", 18, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=handle_add_to_menu).place(x=381, y=460, width=180, height=40)
    customtkinter.CTkButton(root, text="Back", font=("Arial", 16, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=lambda: create_admin_edit_page(root, bg_images, current_category)).place(x=40, y=27, width=80, height=35)

 
def display_admin_menu_items(root, category, bg_images, item_container):
    for widget in item_container.winfo_children(): widget.destroy()
    menu_list = get_all_menu_items(category)
    
    col_width = 200; row_height = 320 # ขนาดของกรอบเมนูแต่ละอัน
    items_per_row = 4                  # จำนวนเมนูต่อแถว
    col_padding = 16; row_padding = 15 # ระยะห่างระหว่างเมนู
    
    item_container.config(padx=15, pady=15) 

    for i, item in enumerate(menu_list):
        col = i % items_per_row
        row = i // items_per_row
        
        item_frame = tk.Frame(item_container, bg="#ffffff", width=col_width, height=row_height, bd=0, highlightthickness=0)
        
        item_frame.grid(row=row, column=col, padx=(0, col_padding), pady=(0, row_padding))
        
        item_frame.pack_propagate(False) 
    # --- END MODIFICATION ---

        img_path = item[MENU_IMG_PATH_IDX]; photo = None
        if img_path and os.path.exists(img_path):
            img_resized = Image.open(img_path).resize((150, 150), Image.Resampling.LANCZOS); photo = ImageTk.PhotoImage(img_resized)
        if photo:
            img_label = tk.Label(item_frame, image=photo, bd=0, highlightthickness=0); img_label.image = photo; img_label.place(x=25, y=5, width=150, height=150)
            
        customtkinter.CTkLabel(item_frame, text=item[MENU_NAME_IDX], font=("CkPomeloDemo", 16, "bold"), fg="#003728", bg="#ffffff").place(relx=0.5, y=190, anchor=tk.CENTER)
        customtkinter.CTkLabel(item_frame, text=f"{item[MENU_PRICE_IDX]} ฿", font=("Arial", 16, "bold"), fg="#699039", bg="#ffffff").place(relx=0.5, y=240, anchor=tk.CENTER)
        
        customtkinter.CTkButton(item_frame, text="Edit", font=("Arial", 14, "bold"), fg="#000000", bg="#ffa214", activebackground="#e28700", bd=0, highlightthickness=0, 
                    command=lambda d=item: create_admin_edit_menu_page(root, bg_images, d, category)).place(x=25, y=270, width=70, height=35)
        
        def confirm_delete(menu_id, name):
            if messagebox.askyesno("Confirm Delete", f"คุณต้องการลบเมนู {name} ใช่หรือไม่?"):
                if delete_menu_item(menu_id): create_admin_edit_page(root, bg_images, category)
                else: messagebox.showerror("Error", "ลบเมนูไม่สำเร็จ")

        customtkinter.CTkButton(item_frame, text="Delete", font=("Arial", 14, "bold"), fg="#000000", bg="#f11c0c", activebackground="#8e140b", bd=0, highlightthickness=0,
                    command=lambda mid=item[MENU_ID_IDX], name=item[MENU_NAME_IDX]: confirm_delete(mid, name)).place(x=105, y=270, width=70, height=35)



def create_admin_edit_page(root, bg_images, category='Drinks'):
    # ...
    image_name = 'editdrinks' # <-- 1.
    if image_name not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพพื้นหลัง Edit"); return
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name]) # <-- แก้
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    customtkinter.CTkButton(root, text="Add Menu", font=("Arial", 16, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=lambda: create_admin_add_menu_page(root, bg_images, category)).place(x=805, y=25, width=120, height=40)
    
    # --- START SCROLLBAR IMPLEMENTATION ---
    scroll_container = tk.Frame(root, bd=0, highlightthickness=0, bg="#ebf3c7")
    scroll_container.place(x=40, y=180, width=878, height=340) # ขนาดและตำแหน่งเดิม

    canvas = tk.Canvas(scroll_container, bd=0, highlightthickness=0, bg="#ebf3c7")
    
    scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    menu_item_frame = tk.Frame(canvas, bg="#ebf3c7", bd=0, highlightthickness=0)

    canvas_frame_id = canvas.create_window((0, 0), window=menu_item_frame, anchor="nw")

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all")) 

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_frame_id, width=event.width)

    menu_item_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    def on_mouse_wheel(event):
        if event.delta: # Windows/macOS
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4: # Linux scroll up
            canvas.yview_scroll(-1, "units")
        elif event.num == 5: # Linux scroll down
            canvas.yview_scroll(1, "units")
            
    # ฟังก์ชันสำหรับผูก Mouse Wheel กับ Widget ลูกทั้งหมด
    def bind_all_children(widget, event_name, callback):
        widget.bind(event_name, callback)
        if event_name == "<MouseWheel>":
            widget.bind("<Button-4>", callback) # Linux
            widget.bind("<Button-5>", callback) # Linux
        
        for child in widget.winfo_children():
            bind_all_children(child, event_name, callback)

    # ผูก Canvas และ Scrollbar ก่อน
    canvas.bind("<MouseWheel>", on_mouse_wheel)
    scrollbar.bind("<MouseWheel>", on_mouse_wheel)
    menu_item_frame.bind("<MouseWheel>", on_mouse_wheel)
    # --- END SCROLLBAR IMPLEMENTATION ---
    
    button_style = {"font": ("Arial", 16, "bold"), "fg": "#003728", "bg": "#bbd106", "activebackground": "#e6fb42", "bd": 0, "highlightthickness": 0}
    def switch_category(new_category): create_admin_edit_page(root, bg_images, new_category)

    customtkinter.CTkButton(root, text="Drinks", **button_style, command=lambda: switch_category('Drinks')).place(x=287, y=122, width=120, height=40)
    customtkinter.CTkButton(root, text="Dessert", **button_style, command=lambda: switch_category('Dessert')).place(x=417, y=122, width=120, height=40)
    customtkinter.CTkButton(root, text="Food", **button_style, command=lambda: switch_category('Food')).place(x=547, y=122, width=120, height=40)

    display_admin_menu_items(root, category, bg_images, menu_item_frame)

    bind_all_children(menu_item_frame, "<MouseWheel>", on_mouse_wheel)

    customtkinter.CTkButton(root, text="Back", font=("Arial", 16, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=lambda: create_admin_order_page(root, bg_images)).place(x=40, y=27, width=80, height=35)
    create_nav_button(root, bg_images, lambda: create_admin_edit_page(root, bg_images, category))


def create_admin_order_page(root, bg_images):
    # ...
    image_name = 'order' # <-- 1.
    if image_name not in bg_images: messagebox.showerror("Error", "ไม่พบรูปภาพ 'order'"); return
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name]) # <-- แก้
    
    
    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    table_names = ["1", "2", "3", "4"]; button_width = 124; button_height = 133; start_x = 156; spacing = 39
    
    for i, num in enumerate(table_names):
        x = start_x + i * (button_width + spacing)
        customtkinter.CTkButton(root, text=f"Table\n{num}", font=("Arial", 24, "bold"), fg="#417c49", bg="#ebf3c7", activebackground="#a0b507", bd=0, highlightthickness=0, 
                  command=lambda n=num: messagebox.showinfo("Order View", f"เปิดดูออเดอร์โต๊ะ {n} (ยังไม่ถูกสร้าง)")).place(x=x, y=235, width=button_width, height=button_height)

    customtkinter.CTkButton(root, text="Log Out", font=("Arial", 16, "bold"), fg="#bbd106", bg="#00452e", activebackground="#2c5432", bd=0, highlightthickness=0, command=lambda: create_main_page(root, bg_images)).place(x=23, y=485, width=120, height=40)
    customtkinter.CTkButton(root, text="Sales", font=("Arial", 16, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=lambda: messagebox.showinfo("Sales", "เปิดรายงานยอดขาย (ยังไม่ถูกสร้าง)")).place(x=612, y=484, width=115, height=40)
    customtkinter.CTkButton(root, text="Menu", font=("Arial", 16, "bold"), fg="#003728", bg="#bbd106", activebackground="#a0b507", bd=0, highlightthickness=0, command=lambda: create_admin_edit_page(root, bg_images, 'Drinks')).place(x=773, y=484, width=115, height=40)
    
    create_nav_button(root, bg_images, lambda: create_admin_order_page(root, bg_images))


# -----------------------------------------------
# --- หน้า User (Menu, Table, Profile, Login) ---
# -----------------------------------------------

# (เพิ่ม cache นี้ไว้ด้านบนของฟังก์ชัน หรือไว้ระดับ global)
menu_image_cache = {} 

def display_menu_items(root, category, bg_images, item_container):
    global menu_image_cache
    menu_image_cache.clear()

    for widget in item_container.winfo_children(): 
        widget.destroy()
        
    menu_list = get_all_menu_items(category)

    col_width = 200; row_height = 320 
    items_per_row = 4 
    col_padding = 15; row_padding = 15
    

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

        if target_path and os.path.exists(target_path):
            try:
                img_original = Image.open(target_path).convert("RGBA")
                img_resized = img_original.resize((150, 150), Image.Resampling.LANCZOS)
                
                photo = customtkinter.CTkImage(
                    light_image=img_resized,
                    dark_image=img_resized,
                    size=(150, 150)
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
            img_label.place(x=25, y=5) 
        
        customtkinter.CTkLabel(
            item_frame, 
            text=item[MENU_NAME_IDX], 
            font=("CkPomeloDemo", 16, "bold"), 
            text_color="#003728", 
            fg_color="transparent" 
        ).place(relx=0.5, y=190, anchor=tk.CENTER)
        
        customtkinter.CTkLabel(
            item_frame, 
            text=f"{item[MENU_PRICE_IDX]} ฿", 
            font=("Arial", 18, "bold"), 
            text_color="#417c49", 
            fg_color="transparent" 
        ).place(relx=0.5, y=245, anchor=tk.CENTER)
        
        customtkinter.CTkButton(
            item_frame, 
            text="Add to Cart", 
            font=("Arial", 12, "bold"),
            text_color="#FFFFFF",      
            fg_color="#417c49",    
            hover_color="#2c5432",   
            width=120, 
            height=30,
            corner_radius=8,
            command=lambda i=item: messagebox.showinfo("Cart", f"Added {i[MENU_NAME_IDX]} to cart")
        ).place(relx=0.5, y=285, anchor=tk.CENTER)


def create_menu_page(root, bg_images, user_data, table_number):
    for widget in root.winfo_children(): widget.destroy()
    
    image_name = 'menudrink' # <-- 1. ระบุชื่อรูป
    if image_name not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'menudrink'"); return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    scrollable_menu_frame = customtkinter.CTkScrollableFrame(
        background_label, 
        fg_color="#ebf3c7",
        corner_radius=10,
        width=858,  
        height=320  
    )
    scrollable_menu_frame.place(x=40, y=180)
    
    # --- (จบส่วน Scrollbar) ---

    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=45) 
    
    profile_btn = customtkinter.CTkButton(
        background_label, 
        image=profile_button_image, 
        text="",
        fg_color="transparent",
        hover_color="#a0b507",
        width=45,
        height=45,
        corner_radius=22, 
        border_width=0,
        command=lambda: create_profile_page(root, bg_images, user_data)
    )
    profile_btn.place(x=25, y=27) 
    
    customtkinter.CTkLabel(
        background_label, 
        text=f" {table_number}", 
        font=("Arial", 20, "bold"), 
        text_color="#003728", 
        fg_color="transparent" 
    ).place(x=150, y=32)
    
    customtkinter.CTkLabel(
        background_label, 
        text="🛒 Cart", 
        font=("Arial", 14, "bold"), 
        text_color="#003728", 
        fg_color="transparent" 
    ).place(x=850, y=35)

 
    def switch_category(category):
        display_menu_items(root, category, bg_images, scrollable_menu_frame)

    customtkinter.CTkButton(
        background_label, 
        text="Drinks", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=120,
        height=40,
        command=lambda: switch_category('Drinks')
    ).place(x=287, y=122)
    
    customtkinter.CTkButton(
        background_label, 
        text="Dessert", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=120,
        height=40,
        command=lambda: switch_category('Dessert')
    ).place(x=417, y=122)
    
    customtkinter.CTkButton(
        background_label, 
        text="Food", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=120,
        height=40,
        command=lambda: switch_category('Food')
    ).place(x=547, y=122)

    switch_category('Drinks')

    create_nav_button(background_label, bg_images, lambda: create_menu_page(root, bg_images, user_data, table_number))


def create_table_page(root, bg_images, user_data): 
    for widget in root.winfo_children(): widget.destroy()
    
    image_name = 'table' 
    if image_name not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'table'"); return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])
    
    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    selected_table = tk.IntVar(); selected_table.set(0)
    table_names = ["1", "2", "3", "4"]; button_width = 124; button_height = 133; start_x = 156; spacing = 39
    
    table_buttons = [] 
    
    # กำหนดสีไว้ล่วงหน้า
    color_normal = "#ebf3c7"
    color_hover = "#a0b507"
    color_selected = "#d1f680" 
    color_text = "#417c49"

    def select_table(selected_num):
        selected_table.set(selected_num)

        for i, btn in enumerate(table_buttons):
            table_num_in_loop = i + 1
            if table_num_in_loop == selected_num:
                btn.configure(fg_color=color_selected) 
            else:
                btn.configure(fg_color=color_normal) 

    
    for i, num in enumerate(table_names):
        x = start_x + i * (button_width + spacing)
        
        
        btn = customtkinter.CTkButton(
            background_label, 
            text=f"Table\n{num}", 
            font=("Arial", 24, "bold"), 
            text_color=color_text,    
            fg_color=color_normal,    
            hover_color=color_hover,  
            border_width=0, 
            corner_radius=15,         
            width=button_width,       
            height=button_height,     
            command=lambda n=int(num): select_table(n)
        )
        btn.place(x=x, y=235)
        table_buttons.append(btn) 
            
    def handle_next():
        table_num = selected_table.get()
        if table_num > 0: 
            create_menu_page(root, bg_images, user_data, table_num) 
        else: 
            messagebox.showerror("Error", "กรุณาเลือกโต๊ะก่อน")


    customtkinter.CTkButton(
        background_label, 
        text="Next", 
        font=("Arial", 18, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        width=130,        
        height=45,        
        command=handle_next
    ).place(x=396, y=441)

    pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data and len(user_data) > PROFILE_PIC_PATH_IDX else ''
    
    profile_button_image = load_and_display_profile_pic_on_button(pic_path, 'default_profile_pic_small', size=45) 
    
    profile_btn = customtkinter.CTkButton(
        background_label, 
        image=profile_button_image, 
        text="",          
        fg_color="transparent", 
        hover_color="#a0b507",  
        width=30,         
        height=45,        
        corner_radius=0, 
        border_width=0,
        command=lambda: create_profile_page(root, bg_images, user_data)
    )
    profile_btn.place(x=24, y=26) 
    
    customtkinter.CTkButton(
        background_label, 
        text="Log Out", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=10,
        width=120,        
        height=40,        
        command=lambda: create_main_page(root, bg_images)
    ).place(x=800, y=20)
    
    create_nav_button(background_label, bg_images, lambda: create_table_page(root, bg_images, user_data))


def create_profile_page(root, bg_images, user_data):
    for widget in root.winfo_children(): widget.destroy()
    
    image_name = 'profile' 
    if image_name not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'profile'"); return
    
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name], anchor="nw") 

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    username = user_data[USERNAME_IDX]; first_name = user_data[FIRST_NAME_IDX]; last_name = user_data[LAST_NAME_IDX]
    phone_number = user_data[PHONE_NUMBER_IDX] if user_data[PHONE_NUMBER_IDX] else "-"; email = user_data[EMAIL_IDX] if user_data[EMAIL_IDX] else "-"
    birth_date = user_data[BIRTH_DATE_IDX] if user_data[BIRTH_DATE_IDX] else "-"; pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data[PROFILE_PIC_PATH_IDX] else ""; points = 14 
    text_font = ("Arial", 18, "bold"); text_fg = "#003728"; text_bg = "#ffffff" 

    def create_info_label(text, x, y, anchor="w", width=300):
    
        customtkinter.CTkLabel(root, text=text, font=text_font, text_color=text_fg, fg_color=text_bg, anchor=anchor).place(x=x, y=y, width=width, height=30)
    
    load_and_display_profile_pic(root, pic_path, 'default_profile_pic', 40, 150, size=140)
    
    edit_button = customtkinter.CTkButton(background_label,
                            text="Edit",
                            font=("Arial", 15, "bold"),
                            text_color="#003728", fg_color="#bbd106",
                            hover_color="#a0b507", border_width=0,
                            width=45,
                            height=30,
                            command=lambda: create_edit_profile_page(root, bg_images, user_data))
    edit_button.place(x=52, y=30)
    
    create_info_label(f"Username : {username}", 200, 160, width=500)
    create_info_label(f"Frist Name : {first_name}", 200, 200, width=300)
    create_info_label(f"Last Name : {last_name}", 560, 200, width=300)
    create_info_label(f"Phone Number : {phone_number}", 200, 240, width=340)
    create_info_label(f"BirthDate : {birth_date}", 560, 240, width=250)
    create_info_label(f"Email : {email}", 200, 280, width=500)
    
   
    # --- อัปเดตพารามิเตอร์ปุ่ม และ anchor ใน .place() ---
    logout_button = customtkinter.CTkButton(background_label,
                                            text="Log out",
                                            font=("Arial", 18, "bold"),
                                            text_color="#ffffff",
                                            fg_color="#417c49",
                                            hover_color="#2c5432",
                                            border_width=0,
                                            width=200,
                                            height=43,
                                            command=lambda: create_main_page(root, bg_images))
    logout_button.place(relx=0.5, y=405, anchor="center")

    back_button = customtkinter.CTkButton(background_label,
                                        text="Back",
                                        font=("Arial", 18, "bold"),
                                        text_color="#003728",
                                        fg_color="#bbd106",
                                        hover_color="#a0b507",
                                        border_width=0,
                                        width=200, 
                                        height=43,
                                        command=lambda: create_table_page(root, bg_images, user_data))
    back_button.place(relx=0.5, y=465, anchor="center")
    
    create_nav_button(root, bg_images, lambda: create_profile_page(root, bg_images, user_data))

def create_edit_profile_page(root, bg_images, user_data):
    for widget in root.winfo_children(): widget.destroy()
    image_name = 'edit_profile' 
    if image_name not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'edit_profile'"); return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name], anchor="nw")

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    user_id = user_data[USER_ID_IDX]; username = user_data[USERNAME_IDX]

    first_name = customtkinter.StringVar(value=user_data[FIRST_NAME_IDX])
    last_name = customtkinter.StringVar(value=user_data[LAST_NAME_IDX])
    phone_number = customtkinter.StringVar(value=user_data[PHONE_NUMBER_IDX] if user_data[PHONE_NUMBER_IDX] else "")
    email = customtkinter.StringVar(value=user_data[EMAIL_IDX] if user_data[EMAIL_IDX] else "")
    birth_date = customtkinter.StringVar(value=user_data[BIRTH_DATE_IDX] if user_data[BIRTH_DATE_IDX] else "")
    current_pic_path = user_data[PROFILE_PIC_PATH_IDX] if user_data[PROFILE_PIC_PATH_IDX] else ""
    new_pic_path = customtkinter.StringVar(value=current_pic_path)
    
    entry_font = ("Arial", 16)

    def select_profile_picture():
        file_path = filedialog.askopenfilename(title="เลือกรูปภาพโปรไฟล์",filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path: 
            new_pic_path.set(file_path)
            load_and_display_profile_pic(root, file_path, 'default_profile_pic', 40, 150, size=140)
            
    def handle_save():
        fn = first_name.get(); ln = last_name.get()
        if not (fn and ln): 
            messagebox.showerror("Save Failed", "กรุณากรอกชื่อและนามสกุล"); return
        updated_data = update_user_profile(user_id, fn, ln, phone_number.get(), email.get(), birth_date.get(), new_pic_path.get())
        if updated_data: 
            messagebox.showinfo("Save Success", "บันทึกข้อมูลเรียบร้อย")
            create_profile_page(root, bg_images, updated_data)
        else: 
            messagebox.showerror("Error", "เกิดข้อผิดพลาดในการบันทึกข้อมูล")
    
    load_and_display_profile_pic(root, current_pic_path, 'default_profile_pic', 40, 150, size=140)
    
    
    edit_button = customtkinter.CTkButton(background_label,
                                        text="📝Edit",
                                        font=("Arial", 12, "bold"),
                                        text_color="#003728",
                                        fg_color="#bbd106",
                                        hover_color="#a0b507",
                                        border_width=0,
                                        width=50, 
                                        height=30,
                                        command=select_profile_picture)
    edit_button.place(x=40, y=115)
    
    
    customtkinter.CTkLabel(root, text=f"Username : {username}", font=entry_font, text_color="#003728", fg_color="white", anchor="w").place(x=200, y=150, width=500, height=30)
   
    customtkinter.CTkLabel(root, text="Frist Name :", font=entry_font, text_color="#003728", fg_color="white", anchor="w").place(x=200, y=190, width=150, height=30)
    customtkinter.CTkEntry(root, textvariable=first_name, font=entry_font, border_width=1, fg_color="white").place(x=330, y=193, width=195, height=25)
    
    customtkinter.CTkLabel(root, text="Last Name :", font=entry_font, text_color="#003728", fg_color="white", anchor="w").place(x=540, y=190, width=140, height=30)
    customtkinter.CTkEntry(root, textvariable=last_name, font=entry_font, border_width=1, fg_color="white").place(x=670, y=193, width=180, height=25)
    
    customtkinter.CTkLabel(root, text="Phone Number :", font=entry_font, text_color="#003728", fg_color="white", anchor="w").place(x=200, y=230, width=180, height=30)
    vcmd = (root.register(lambda P: P.isdigit() or P == ""), '%P')
    customtkinter.CTkEntry(root, textvariable=phone_number, font=entry_font, border_width=1, fg_color="white", validate="key", validatecommand=vcmd).place(x=360, y=233, width=155, height=25)
    
    customtkinter.CTkLabel(root, text="BirthDate :", font=entry_font, text_color="#003728", fg_color="white", anchor="w").place(x=520, y=230, width=140, height=30)
    customtkinter.CTkEntry(root, textvariable=birth_date, font=entry_font, border_width=1, fg_color="white").place(x=640, y=233, width=140, height=25)
    
    customtkinter.CTkLabel(root, text="Email :", font=entry_font, text_color="#003728", fg_color="white", anchor="w").place(x=200, y=270, width=150, height=30)
    customtkinter.CTkEntry(root, textvariable=email, font=entry_font, border_width=1, fg_color="white").place(x=270, y=273, width=415, height=25)
     
    customtkinter.CTkLabel(root, text=f"Your Points : 14", font=("Arial", 20, "bold"), text_color="#003728", fg_color="white").place(relx=0.5, y=340, anchor="center")
    
    customtkinter.CTkButton(root, text="Save", font=("Arial", 18, "bold"), text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", border_width=0, command=handle_save).place(relx=0.5, y=410, width=200, height=43, anchor="center")
    customtkinter.CTkButton(root, text="Back", font=("Arial", 18, "bold"), text_color="#003728", fg_color="#bbd106", hover_color="#a0b507", border_width=0, command=lambda: create_profile_page(root, bg_images, user_data)).place(relx=0.5, y=465, width=200, height=43, anchor="center")
    
    create_nav_button(root, bg_images, lambda: create_edit_profile_page(root, bg_images, user_data))


def create_forgot_password_page(root, bg_images):
    for widget in root.winfo_children(): widget.destroy()

    image_name = 'forgot_password' # <-- 1. ระบุชื่อรูป
    if image_name not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'forgot_password'"); return

    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])
    
    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    email_entry = customtkinter.CTkEntry(
        background_label,  
        font=("Arial", 18), 
        border_width=0,
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=343,         
        height=40
    )
    email_entry.place(x=303, y=212) 
    
    phone_number_entry = customtkinter.CTkEntry(
        background_label,  
        font=("Arial", 18), 
        border_width=0, 
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=343,         
        height=40
    )
    phone_number_entry.place(x=303, y=282) 

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
        font=("Arial", 18, "bold"), 
        text_color="#003728",    
        fg_color="#bbd106",      
        hover_color="#a0b507",   
        border_width=0,
        corner_radius=20,
        width=200,               
        height=45,
        command=handle_submit_verification
    )
    submit_button.place(x=380, y=345) 

    back_button = customtkinter.CTkButton(
        background_label, 
        text="Back", 
        font=("Arial", 18, "bold"), 
        text_color="#003728",    
        fg_color="#bbd106",      
        hover_color="#a0b507",   
        border_width=0, 
        corner_radius=20,
        width=200,               
        height=45,
        command=lambda: create_login_page(root, bg_images)
    )
    back_button.place(x=380, y=400) 
    create_nav_button(background_label, bg_images, lambda: create_change_password_page(root, bg_images))


def create_change_password_page(root, bg_images, user_data):
    for widget in root.winfo_children(): widget.destroy()

    image_name = 'change_password' # <-- 1. ระบุชื่อรูป
    if image_name not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'change_password'"); return

    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    user_id = user_data[USER_ID_IDX]
    
    new_password_entry = customtkinter.CTkEntry(
        background_label,  
        font=("Arial", 20), 
        show="*", 
        border_width=0, 
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=343,         
        height=40
    )
    new_password_entry.place(x=303, y=212) 
    
    confirm_password_entry = customtkinter.CTkEntry(
        background_label,  
        font=("Arial", 20), 
        show="*", 
        border_width=0, 
        fg_color="#ebf3c7",
        text_color="#000000",
        corner_radius=10,
        width=343,         
        height=40
    )
    confirm_password_entry.place(x=303, y=282) 
    
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
        font=("Arial", 18, "bold"), 
        text_color="#003728",    
        fg_color="#bbd106",      
        hover_color="#a0b507",   
        border_width=0,
        corner_radius=10,
        width=200,               
        height=45,
        command=handle_save_password
    )
    save_button.place(x=380, y=345) 
    
    back_button = customtkinter.CTkButton(
        background_label,  
        text="Back", 
        font=("Arial", 18, "bold"), 
        text_color="#003728",    
        fg_color="#bbd106",      
        hover_color="#a0b507",   
        border_width=0,
        corner_radius=10,
        width=200,               
        height=45,
        command=lambda: create_forgot_password_page(root, bg_images) 
    )
    back_button.place(x=380, y=400) 

    create_nav_button(background_label, bg_images, lambda: create_login_page(root, bg_images))


def create_login_page(root, bg_images):
    for widget in root.winfo_children(): 
        widget.destroy()
    
    image_name = 'login' # <-- 1. ระบุชื่อรูป
    if image_name not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'login'"); return

    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    # เราจะสร้าง 3 คอลัมน์: [Spacer] [Content] [Spacer]
    background_label.grid_columnconfigure((0, 2), weight=1) # คอลัมน์ 0 และ 2 (ซ้าย/ขวา) จะยืดออกเพื่อดัน Content ให้อยู่ตรงกลาง
    background_label.grid_columnconfigure(1, weight=0)      # คอลัมน์ 1 (Content) จะมีขนาดคงที่
    
    # เราจะสร้างหลายแถว เพื่อจัดเรียงปุ่มในแนวตั้ง
    background_label.grid_rowconfigure(0, weight=2) # แถวบนสุด (Spacer) ดันลงมา
    background_label.grid_rowconfigure(1, weight=0) # username
    background_label.grid_rowconfigure(2, weight=0) # password
    background_label.grid_rowconfigure(3, weight=0) # submit
    background_label.grid_rowconfigure(4, weight=0) # back
    background_label.grid_rowconfigure(5, weight=0) # forgot
    background_label.grid_rowconfigure(6, weight=1) # แถวล่าง (Spacer) ดันขึ้นไป
    background_label.grid_rowconfigure(7, weight=1) # แถวล่างสุดสำหรับ nav_button
    
    # 3. สร้าง Widgets (เหมือนเดิม)
    
    # (เรากำหนดค่า `width` และ `height` ให้ widget โดยตรง)
    entry_width = 315
    entry_height = 42
    btn_width = 200
    btn_height = 45
    
    username_entry = customtkinter.CTkEntry(
        background_label, # <--- สังเกตว่า parent คือ background_label
        font=("Arial", 20), 
        fg_color="#ebf3c7", 
        text_color="#000000",
        border_width=0,
        corner_radius=0,
        width=entry_width, 
        height=entry_height
    )
    
    password_entry = customtkinter.CTkEntry(
        background_label,
        font=("Arial", 20), 
        show="*", 
        fg_color="#ebf3c7",
        text_color="#000000",
        border_width=0, 
        corner_radius=0,
        width=entry_width, 
        height=entry_height
    )

    submit_button = customtkinter.CTkButton(
        background_label, 
        text="Submit", 
        font=("Arial", 18, "bold"), 
        text_color="#003728",
        fg_color="#bbd106",
        hover_color="#a0b507",
        corner_radius=20,
        command=lambda: handle_submit(username_entry.get(), password_entry.get()), # <--- ต้องแก้ handle_submit เล็กน้อย
        width=btn_width, 
        height=btn_height
    )

    back_button = customtkinter.CTkButton(
        background_label, 
        text="Back", 
        font=("Arial", 18, "bold"),
        text_color="#003728",
        fg_color="#bbd106",
        hover_color="#a0b507",
        corner_radius=20,
        command=lambda: create_main_page(root, bg_images),
        width=btn_width,
        height=btn_height
    ) 

    forgot_button = customtkinter.CTkButton(
        background_label,
        text="Forgot Password?",
        font=("Arial", 12, "underline"),
        text_color="#a0b507",
        fg_color="transparent", 
        hover_color="#f3f6e8", 
        command=lambda: create_forgot_password_page(root, bg_images)
    )
    
    # 4. "จัดวาง" Widgets ลงในตาราง
    # เราจะวางทุกอย่างลงใน `column=1` (คอลัมน์กลาง)
    username_entry.grid(row=1, column=1, pady=10)
    password_entry.grid(row=2, column=1, pady=10)
    submit_button.grid(row=3, column=1, pady=15)
    back_button.grid(row=4, column=1, pady=10)
    forgot_button.grid(row=5, column=1, pady=10)

    # 5. จัดการปุ่ม Nav Button (ที่ต้องอยู่มุมขวาล่าง)
    # เราจะใช้ `.grid()` กับมันด้วย!
    nav_btn = customtkinter.CTkButton(
        background_label, 
        text="•\n•\n•", 
        font=("Arial", 10, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106",
        hover_color="#1f8b3f", 
        border_width=0,
        corner_radius=5,
        width=24,
        height=40,
        command=lambda: create_about_page(root, bg_images, lambda: create_login_page(root, bg_images))
    )
    # วางไว้ที่แถวล่างสุด, คอลัมน์ขวาสุด และ "ยึด" ไว้ที่มุมขวาล่าง (South-East)
    nav_btn.grid(row=7, column=2, sticky="se", padx=5, pady=5)
    
    # 6. แก้ไขฟังก์ชัน handle_submit (เพราะเราไม่ได้สร้าง entry เป็น global)
    def handle_submit(username, password):
        # (คัดลอกโค้ดจากฟังก์ชันเดิมของคุณมาที่นี่)
        if not username or not password: 
            messagebox.showerror("Login Failed", "กรุณากรอก Username และ Password")
            return
            
        user_data = check_login(username, password)
        
        if user_data:
            if user_data[USER_ID_IDX] == 0 and user_data[USERNAME_IDX] == "adminja":
                messagebox.showinfo("Admin Login", "เข้าสู่ระบบผู้ดูแลระบบสำเร็จ!")
                create_admin_order_page(root, bg_images)
            else:
                messagebox.showinfo("Login Status", "เข้าสู่ระบบสำเร็จ!")
                create_table_page(root, bg_images, user_data) 
        else: 
            messagebox.showerror("Login Failed", "Username หรือ Password ไม่ถูกต้อง")


def create_main_page(root, bg_images):
    for widget in root.winfo_children(): 
        widget.destroy()
        
    image_name = 'main' # <-- 1. ระบุชื่อรูป
    if image_name not in bg_images: 
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'main'"); return
        
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )

    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    # --- คำนวณสัดส่วน (จาก 960x540) ---
    # login: relx = 110 / 960 = 0.114
    # signup: relx = 255 / 960 = 0.265
    # y: rely = 300 / 540 = 0.555
    # nav: relx = 925 / 960 = 0.963, rely = 485 / 540 = 0.898
    
    # --- กำหนดขนาดปุ่มแบบสัมพัทธ์ ---
    # rel_width_btn = 120 / 960 = 0.125
    # rel_height_btn = 45 / 540 = 0.083

    login_button = customtkinter.CTkButton(
        background_label, 
        text="Log In", 
        font=("Arial", 16, "bold"),
        fg_color="#bbd106",
        text_color="#003728",
        hover_color="#a0b507",
        border_width=0,
        corner_radius=20,
        command=lambda: create_login_page(root, bg_images)
        # เราจะกำหนดขนาดใน .place()
    )
    # ใช้ relx, rely และ anchor='nw' (North-West) เพื่อให้จุดยึดเหมือน x,y เดิม
    login_button.place(relx=0.114, rely=0.555, relwidth=0.125, relheight=0.083, anchor="nw") 
    
    signup_button = customtkinter.CTkButton(
        background_label, 
        text="Sign Up", 
        font=("Arial", 16, "bold"),
        fg_color="#bbd106",
        text_color="#003728",
        hover_color="#a0b507",
        border_width=0,
        corner_radius=20,
        command=lambda: create_signup_page(root, bg_images)
    )
    signup_button.place(relx=0.265, rely=0.555, relwidth=0.125, relheight=0.083, anchor="nw") 

    # สร้าง Nav Button ใหม่ด้วย relx/rely (จากโค้ดเดิมของคุณ)
    nav_btn = customtkinter.CTkButton(
        background_label,
        text="•\n•\n•", 
        font=("Arial", 10, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106",
        hover_color="#1f8b3f", 
        border_width=0,
        corner_radius=5,
        width=24, # <--- ใช้อันเล็กๆ ขนาดคงที่ได้
        height=40,
        command=lambda: create_about_page(root, bg_images, lambda: create_main_page(root, bg_images))
    )
    # x=925, y=485 -> relx=0.963, rely=0.898
    nav_btn.place(relx=0.963, rely=0.898, anchor="nw")


def create_signup_page(root, bg_images):
    for widget in root.winfo_children(): 
        widget.destroy()
        
    image_name = 'signup' # <-- 1. ระบุชื่อรูป
    background_label = customtkinter.CTkLabel(root, text="", image=bg_images[image_name])

    background_label.bind(
        "<Configure>", 
        lambda event, lbl=background_label, name=image_name: resize_background_image(event, lbl, name)
    )
    background_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    def validate_phone_number(P): 
        return P.isdigit() or P == ""
 
    def handle_signup():
        # ... (โค้ด handle_signup ของคุณเหมือนเดิมเป๊ะ) ...
        # (ดึงค่าจาก entry_vars ที่เราจะสร้างด้านล่าง)
        username = username_var.get()
        password = password_var.get()
        first_name = first_name_var.get()
        last_name = last_name_var.get()
        phone_number = phone_number_var.get()
        email = email_var.get()
        birth_date = birth_date_var.get()
        
        # (ส่วนที่เหลือของฟังก์ชัน handle_signup... )
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
    
    vcmd = (root.register(validate_phone_number), '%P')
    
    # --- สร้าง StringVars สำหรับเก็บค่า ---
    username_var = tk.StringVar()
    password_var = tk.StringVar()
    first_name_var = tk.StringVar()
    last_name_var = tk.StringVar()
    phone_number_var = tk.StringVar()
    email_var = tk.StringVar()
    birth_date_var = tk.StringVar()
    
    # --- กำหนดค่าคงที่ของ Entry ---
    entry_font = ("Arial", 16)
    entry_fg_color = "#ebf3c7"
    entry_text_color = "#000000"
    entry_corner_radius = 0 
    entry_border_width = 0
    
    # --- คำนวณสัดส่วนของขนาดและตำแหน่ง (จาก 960x540) ---
    # rel_width = 185 / 960 = 0.192
    # rel_height = 28 / 540 = 0.051
    # เราจะใช้ relwidth และ relheight เพื่อให้ช่องมันขยายตามจอด้วย
    
    username_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        textvariable=username_var # <--- ใช้ StringVar
    )
    # x=227, y=157 -> relx=0.236, rely=0.290
    username_entry.place(relx=0.236, rely=0.290, relwidth=0.192, relheight=0.051, anchor="nw")

    password_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, show="*", fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        textvariable=password_var # <--- ใช้ StringVar
    )
    # x=515, y=157 -> relx=0.536, rely=0.290
    password_entry.place(relx=0.536, rely=0.290, relwidth=0.192, relheight=0.051, anchor="nw")

    first_name_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        textvariable=first_name_var # <--- ใช้ StringVar
    )
    # x=227, y=201 -> relx=0.236, rely=0.372
    first_name_entry.place(relx=0.236, rely=0.372, relwidth=0.192, relheight=0.051, anchor="nw")

    last_name_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        textvariable=last_name_var # <--- ใช้ StringVar
    )
    # x=515, y=201 -> relx=0.536, rely=0.372
    last_name_entry.place(relx=0.536, rely=0.372, relwidth=0.192, relheight=0.051, anchor="nw")

    phone_number_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius, 
        validate="key", validatecommand=vcmd,
        textvariable=phone_number_var # <--- ใช้ StringVar
    )
    # x=360, y=250 -> relx=0.375, rely=0.463
    phone_number_entry.place(relx=0.375, rely=0.463, relwidth=0.192, relheight=0.051, anchor="nw")

    email_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        textvariable=email_var # <--- ใช้ StringVar
    )
    # x=360, y=295 -> relx=0.375, rely=0.546
    email_entry.place(relx=0.375, rely=0.546, relwidth=0.192, relheight=0.051, anchor="nw")

    birth_date_entry = customtkinter.CTkEntry(
        background_label, font=entry_font, fg_color=entry_fg_color, text_color=entry_text_color,
        border_width=entry_border_width, corner_radius=entry_corner_radius,
        textvariable=birth_date_var # <--- ใช้ StringVar
    )
    # x=360, y=340 -> relx=0.375, rely=0.630
    birth_date_entry.place(relx=0.375, rely=0.630, relwidth=0.192, relheight=0.051, anchor="nw")
    
    # --- ปุ่ม (เราจะใช้ relwidth/relheight กับปุ่มด้วย) ---
    # rel_width_btn = 145 / 960 = 0.151
    # rel_height_btn = 40 / 540 = 0.074
    
    signup_btn = customtkinter.CTkButton(
        background_label, 
        text="Sign up", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        command=handle_signup
    )
    # x=319, y=392 -> relx=0.332, rely=0.726
    signup_btn.place(relx=0.332, rely=0.726, relwidth=0.151, relheight=0.074, anchor="nw")

    back_btn = customtkinter.CTkButton(
        background_label, 
        text="Back", 
        font=("Arial", 16, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106", 
        hover_color="#a0b507", 
        border_width=0, 
        corner_radius=20,
        command=lambda: create_main_page(root, bg_images)
    )
    # x=476, y=392 -> relx=0.496, rely=0.726
    back_btn.place(relx=0.496, rely=0.726, relwidth=0.151, relheight=0.074, anchor="nw")

    # --- Nav Button (ใช้โค้ดจาก ทางเลือกที่ 2 ของผม) ---
    nav_btn = customtkinter.CTkButton(
        background_label,
        text="•\n•\n•", 
        font=("Arial", 10, "bold"), 
        text_color="#003728", 
        fg_color="#bbd106",
        hover_color="#1f8b3f", 
        border_width=0,
        corner_radius=5,
        width=24, # <--- อาจจะคงที่ขนาดไว้ดีกว่า
        height=40,
        command=lambda: create_about_page(root, bg_images, lambda: create_signup_page(root, bg_images))
    )
    # x=925, y=485 -> relx=0.963, rely=0.898
    nav_btn.place(relx=0.963, rely=0.898, anchor="nw")

# --- ส่วนหลักของโปรแกรม ---
# --- ส่วนหลักของโปรแกรม ---
if __name__ == "__main__":

    # กำหนด Path รูปภาพ 
    image_paths = {
        'main': "D:\\โปรเจ็คของใบหม่อน\\Firstpage.png",
        'login': "D:\\โปรเจ็คของใบหม่อน\\2.png",
        'signup': "D:\\โปรเจ็คของใบหม่อน\\3.png",
        'about': "D:\\โปรเจ็คของใบหม่อน\\about.png",
        'table': "D:\\โปรเจ็คของใบหม่อน\\table.png", 
        'profile': "D:\\โปรเจ็คของใบหม่อน\\profile.png", 
        'edit_profile': "D:\\โปรเจ็คของใบหม่อน\\editpf.png", 
        'forgot_password': "D:\\โปรเจ็คของใบหม่อน\\forgotpw.png", 
        'change_password': "D:\\โปรเจ็คของใบหม่อน\\changepw.png", 

        # Admin & Menu Management
        'order': "D:\\โปรเจ็คของใบหม่อน\\order.png", 
        'editdrinks': "D:\\โปรเจ็คของใบหม่อน\\edit.png",
        'addmenu': "D:\\โปรเจ็คของใบหม่อน\\addmenu.png",
        'editmenu': "D:\\โปรเจ็คของใบหม่อน\\editmenu.png",
        'menudrink': "D:\\โปรเจ็คของใบหม่อน\\menu.png",

        'default_profile_pic': "D:\\โปรเจ็คของใบหม่อน\\default_profile.png", 
        'default_profile_pic_small': "D:\\โปรเจ็คของใบหม่อน\\default_profile.png",
        'default_menu_img': "D:\\โปรเจ็คของใบหม่อน\\default_menu.png", 
    }

    initialize_db()

    root = customtkinter.CTk()
    root.bind("<F11>", toggle_fullscreen) # <--- ถูกต้องแล้ว
    root.title("Baimon Herb Cafe")
    root.geometry("960x540")
    customtkinter.set_appearance_mode("light")
    customtkinter.set_default_color_theme("green")

    # โหลดรูปภาพทั้งหมด
    # (*** นี่คือส่วนที่แก้ไข ***)
    try:
        for name, path in image_paths.items():
            if os.path.exists(path):
                # 1. เปิดรูปต้นฉบับ
                original_image = Image.open(path).convert("RGBA")

                if name not in ['default_profile_pic', 'default_profile_pic_small', 'default_menu_img']: 

                    # 2. เก็บ "ต้นฉบับ" (วัตถุดิบ) ลง Global Cache
                    original_pil_images[name] = original_image

                    # 3. สร้างรูป "ขนาดเริ่มต้น" (960x540)
                    resized_image = original_image.resize((960, 540), Image.Resampling.LANCZOS)
                    bg_images[name] = customtkinter.CTkImage(
                        light_image=resized_image, 
                        dark_image=resized_image,  
                        size=(960, 540)
                    )
                # (ส่วน else สำหรับรูป default ก็สามารถเพิ่มได้ถ้าต้องการ)

    except FileNotFoundError as e:
        messagebox.showerror("Error", f"ไม่พบไฟล์รูปภาพ: {e.filename} กรุณาตรวจสอบ path"); root.destroy(); exit()
    except Exception as e:
        messagebox.showerror("Error Loading Images", str(e)); root.destroy(); exit()
    # (*** จบส่วนที่แก้ไข ***)


    create_main_page(root, bg_images)

    root.mainloop()