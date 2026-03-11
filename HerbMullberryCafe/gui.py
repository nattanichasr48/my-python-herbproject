from tkinter import *
#ก่รสร้างหน้าต่าง
root = Tk()
root.title("My GUI")

#ใส่ข้อความในหน้าจอ
mylabel = Label(text="Hello World",fg="blue",font=50,bg="yellow").pack()
#กำหนดขนาดหน้าจอ ตำแหน่งหน้าจอ
root.geometry("960x540+300+190")
root.mainloop()