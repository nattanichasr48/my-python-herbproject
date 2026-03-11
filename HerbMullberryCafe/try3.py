import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import tkinter as tk 

# --- การตั้งค่าเริ่มต้นของ CustomTkinter ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
# ----------------------------------------

# --- ฟังก์ชันสำหรับหน้า About (หน้าใหม่) ---

def create_about_page(root: ctk.CTk, bg_images, prev_page_func):
    for widget in root.winfo_children():
        widget.destroy()

    if 'about' not in bg_images:
        messagebox.showerror("Error", "ไม่พบรูปภาพ 'about' โปรดตรวจสอบ key และ path ในโค้ดหลัก")
        return
    
    background_label = tk.Label(root, image=bg_images['about'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # 🟢 แก้ไข: เพิ่ม border_color และเพิ่ม border_width
    ctk.CTkButton(root, 
                text="Back", 
                font=("Arial", 18, "bold"), 
                text_color="#003728",
                fg_color="#bbd106",
                hover_color="#a0b507",
                border_width=5,           # ต้องมี border_width > 0
                border_color="#bbd106",   # <<< ขอบสีเดียวกับปุ่ม
                corner_radius=15,
                width=145, 
                height=38, 
                command=prev_page_func
    ).place(x=408, y=478)


# --- ฟังก์ชันสำหรับปุ่มจุดสามจุด (ปุ่มทั่วไป) ---

def create_nav_button(root: ctk.CTk, bg_images, current_page_func):
    
    # 🟢 แก้ไข: เพิ่ม border_color และเพิ่ม border_width
    ctk.CTkButton(root,
                  text="•\n•\n•",
                  font=("Arial", 10, "bold"),
                  text_color="#003728",
                  fg_color="#bbd106",
                  hover_color="#1f8b3f",
                  border_width=3,            # ใช้ border_width น้อยลงสำหรับปุ่มเล็ก
                  border_color="#bbd106",    # <<< ขอบสีเดียวกับปุ่ม
                  corner_radius=10,
                  width=24,
                  height=40,
                  command=lambda: create_about_page(root, bg_images, current_page_func)
    ).place(x=925, y=487) 


# --- ปรับปรุงฟังก์ชันเปลี่ยนหน้าทั้งหมด ---

def create_login_page(root: ctk.CTk, bg_images):
    for widget in root.winfo_children():
        widget.destroy()
    background_label = tk.Label(root, image=bg_images['login'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    def handle_submit():
        username = username_entry.get()
        password = password_entry.get()
        if username and password:
            messagebox.showinfo("Login Status", "เข้าสู่ระบบสำเร็จ!")
            if 'table' in bg_images:
                create_table_page(root, bg_images)
            else:
                messagebox.showwarning("Warning", "ไม่พบหน้า Table (ขาดรูปภาพ 'table')")
                create_main_page(root, bg_images)
        else:
            messagebox.showerror("Login Failed", "กรุณากรอก Username และ Password")
            
    # ctk.CTkEntry (Entry ไม่ได้มีปัญหาเรื่องขอบดำ)
    entry_settings = {"font": ("Arial", 20), "fg_color": "#ebf3c7", "text_color": "#000000", "border_width": 0, "corner_radius": 10, "width": 300, "height": 42}
    username_entry = ctk.CTkEntry(root, **entry_settings)
    username_entry.place(x=330, y=210)
    password_entry = ctk.CTkEntry(root, show="*", **entry_settings)
    password_entry.place(x=330, y=270)
    
    # 🟢 แก้ไข: เพิ่ม border_color
    button_settings = {
        "font": ("Arial", 18, "bold"), 
        "text_color": "#003728", 
        "fg_color": "#bbd106", 
        "hover_color": "#a0b507", 
        "border_width": 5, 
        "border_color": "#bbd106", # <<< ขอบสีเดียวกับปุ่ม
        "corner_radius": 15, 
        "width": 200, 
        "height": 45
    }
    ctk.CTkButton(root, text="Submit", command=handle_submit, **button_settings).place(x=380, y=340)
    ctk.CTkButton(root, text="Back", command=lambda: create_main_page(root, bg_images), **button_settings).place(x=380, y=400)
    
    create_nav_button(root, bg_images, lambda: create_login_page(root, bg_images))


def create_signup_page(root: ctk.CTk, bg_images):
    for widget in root.winfo_children():
        widget.destroy()
    background_label = tk.Label(root, image=bg_images['signup'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    def validate_phone_number(P):
        if P.isdigit() or P == "":
            return True
        else:
            return False
            
    def handle_signup():
        username = username_entry.get()
        password = password_entry.get()
        first_name = first_name_entry.get()
        last_name = last_name_entry.get()
        phone_number = phone_number_entry.get()
        email = email_entry.get()
        birth_date = birth_date_entry.get()

        if len(phone_number) != 10:
            messagebox.showerror("Sign Up Failed", "กรุณากรอกเบอร์โทรศัพท์ให้ครบ 10 หลัก")
        elif username and password and first_name and last_name:
            messagebox.showinfo("Sign Up Success", "สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")
            create_login_page(root, bg_images)
        else:
            messagebox.showerror("Sign Up Failed", "กรุณากรอกข้อมูลให้ครบถ้วน")

    vcmd = (root.register(validate_phone_number), '%P')
    
    entry_settings_small = {"font": ("Arial", 16), "fg_color": "#ebf3c7", "text_color": "#000000", "border_width": 0, "corner_radius": 10, "width": 173, "height": 28}
    
    username_entry = ctk.CTkEntry(root, **entry_settings_small)
    username_entry.place(x=230, y=157)
    password_entry = ctk.CTkEntry(root, show="*", **entry_settings_small)
    password_entry.place(x=513, y=157)
    first_name_entry = ctk.CTkEntry(root, **entry_settings_small)
    first_name_entry.place(x=230, y=202)
    last_name_entry = ctk.CTkEntry(root, **entry_settings_small)
    last_name_entry.place(x=513, y=202)
    phone_number_entry = ctk.CTkEntry(root, validate="key", validatecommand=vcmd, **entry_settings_small)
    phone_number_entry.place(x=360, y=250)
    email_entry = ctk.CTkEntry(root, **entry_settings_small)
    email_entry.place(x=360, y=295)
    birth_date_entry = ctk.CTkEntry(root, **entry_settings_small)
    birth_date_entry.place(x=360, y=340)

    # 🟢 แก้ไข: เพิ่ม border_color
    button_settings = {
        "font": ("Arial", 16, "bold"), 
        "text_color": "#003728", 
        "fg_color": "#bbd106", 
        "hover_color": "#a0b507", 
        "border_width": 5,
        "border_color": "#bbd106", # <<< ขอบสีเดียวกับปุ่ม
        "corner_radius": 15, 
        "width": 145, 
        "height": 40
    }
    ctk.CTkButton(root, text="Sign up", command=handle_signup, **button_settings).place(x=319, y=392)
    ctk.CTkButton(root, text="Back", command=lambda: create_main_page(root, bg_images), **button_settings).place(x=476, y=392)

    create_nav_button(root, bg_images, lambda: create_signup_page(root, bg_images))

def create_table_page(root: ctk.CTk, bg_images):
    for widget in root.winfo_children():
        widget.destroy()
    
    if 'table' in bg_images:
        background_label = tk.Label(root, image=bg_images['table'])
        background_label.place(x=0, y=0, relwidth=1, relheight=1)
    else:
        ctk.CTkFrame(root, fg_color=root._fg_color).place(x=0, y=0, relwidth=1, relheight=1)
        ctk.CTkLabel(root, text="Page 'Table' is missing image file.", text_color="red").place(relx=0.5, rely=0.5, anchor="center")

    messagebox.showinfo("Baimon Herb Cafe", "เข้าสู่หน้าเลือกโต๊ะ")
    
    create_nav_button(root, bg_images, lambda: create_table_page(root, bg_images))


def create_main_page(root: ctk.CTk, bg_images):
    for widget in root.winfo_children():
        widget.destroy()
    background_label = tk.Label(root, image=bg_images['main'])
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # 🟢 แก้ไข: กำหนด width/height และเพิ่ม border_color
    button_settings = {
        "font": ("Arial", 16,"bold"), 
        "text_color": "#003728", 
        "fg_color": "#bbd106", 
        "hover_color": "#bbd106", 
        "border_width": 5,
        "border_color": "#bbd106", # <<< ขอบสีเดียวกับปุ่ม
        "corner_radius": 15,
        "width": 120,
        "height": 45
    }
    ctk.CTkButton(root, text="Log In", command=lambda: create_login_page(root, bg_images), **button_settings).place(x=110, y=330)
    ctk.CTkButton(root, text="Sign Up", command=lambda: create_signup_page(root, bg_images), **button_settings).place(x=255, y=330)
                             
    create_nav_button(root, bg_images, lambda: create_main_page(root, bg_images))


# --- ส่วนหลักของโปรแกรม ---
if __name__ == "__main__":
    root = ctk.CTk() 
    root.title("Baimon Herb Cafe")
    # 💡 แก้ไขขนาดหน้าต่างให้สอดคล้องกับขนาดรูปภาพด้านล่าง
    root.geometry("960x540") 

    # โหลดรูปภาพทั้งหมดตั้งแต่ต้น
    bg_images = {}
    try:
        image_paths = {
            'main': "D:\\โปรเจ็คของใบหม่อน\\Firstpage.png",
            'login': "D:\\โปรเจ็คของใบหม่อน\\2.png",
            'signup': "D:\\โปรเจ็คของใบหม่อน\\3.png",
            'about': "D:\\โปรเจ็คของใบหม่อน\\about.png",
            'table': "D:\\โปรเจ็คของใบหม่อน\\table.png" # 💡 เพิ่ม path ที่ใช้งานจริง
        }
        for name, path in image_paths.items():
            original_image = Image.open(path)
            # 💡 แก้ไขขนาดรูปภาพให้ตรงกับ root.geometry
            resized_image = original_image.resize((1200, 690), Image.Resampling.LANCZOS)
            bg_images[name] = ImageTk.PhotoImage(resized_image)

    except FileNotFoundError as e:
        messagebox.showerror("Error", f"ไม่พบไฟล์รูปภาพ: {e.filename}")
        root.destroy()
        exit()

    create_main_page(root, bg_images)
    root.mainloop()