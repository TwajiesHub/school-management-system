import customtkinter as ctk
import os
import threading
import sys
import subprocess
import tkinter.messagebox

# IMPORT MODULES
import config_manager
# import school_setup  <-- DELETE or IGNORE this import, we don't need it anymore
import excel_worker
import worker
import auditor
import pc_receiver
import auth_manager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BASE_DIR = config_manager.BASE_DIR

class ZionwolDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("950x700")
        self.title("Zionwol Digital System V5 - LOCKED")
        
        # Initialize User Database
        auth_manager.init_db()
        
        # Decide: Show Sign Up (if new) or Login
        if auth_manager.get_user_count() == 0:
            self.show_signup_screen(first_time=True)
        else:
            self.show_login_screen()

    # --- 1. LOGIN SCREEN ---
    def show_login_screen(self):
        self.clear_window()
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(fill="both", expand=True)

        box = ctk.CTkFrame(self.login_frame, width=350, height=400)
        box.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(box, text="🔒 SYSTEM LOCKED", font=("Arial", 22, "bold")).pack(pady=30)
        
        self.user_entry = ctk.CTkEntry(box, placeholder_text="Username", width=220)
        self.user_entry.pack(pady=10)
        
        self.pass_entry = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=220)
        self.pass_entry.pack(pady=10)
        self.pass_entry.bind("<Return>", self.attempt_login)
        
        ctk.CTkButton(box, text="UNLOCK", command=self.attempt_login, width=220, fg_color="#3b8ed0").pack(pady=20)
        
        ctk.CTkButton(box, text="Create New Admin", command=lambda: self.show_signup_screen(False), 
                      fg_color="transparent", text_color="gray", hover_color="#202020").pack(pady=5)

    # --- 2. SIGN UP SCREEN ---
    def show_signup_screen(self, first_time=False):
        self.clear_window()
        self.signup_frame = ctk.CTkFrame(self)
        self.signup_frame.pack(fill="both", expand=True)

        box = ctk.CTkFrame(self.signup_frame, width=400, height=500)
        box.place(relx=0.5, rely=0.5, anchor="center")
        
        title = "🚀 WELCOME SETUP" if first_time else "REGISTER NEW ADMIN"
        ctk.CTkLabel(box, text=title, font=("Arial", 20, "bold")).pack(pady=25)
        
        self.reg_school = ctk.CTkEntry(box, placeholder_text="School Name (e.g. Zionwol Int.)", width=250)
        self.reg_school.pack(pady=10)
        
        self.reg_user = ctk.CTkEntry(box, placeholder_text="New Username", width=250)
        self.reg_user.pack(pady=10)
        
        self.reg_pass = ctk.CTkEntry(box, placeholder_text="New Password", show="*", width=250)
        self.reg_pass.pack(pady=10)
        
        self.reg_confirm = ctk.CTkEntry(box, placeholder_text="Confirm Password", show="*", width=250)
        self.reg_confirm.pack(pady=10)
        
        ctk.CTkButton(box, text="CREATE ACCOUNT", command=self.attempt_signup, width=250, fg_color="#10b981").pack(pady=20)
        
        if not first_time:
            ctk.CTkButton(box, text="< Back to Login", command=self.show_login_screen, fg_color="transparent").pack(pady=5)

    # --- AUTH LOGIC ---
    def attempt_login(self, event=None):
        u = self.user_entry.get()
        p = self.pass_entry.get()
        
        if auth_manager.verify_user(u, p):
            self.start_main_app()
        else:
            tkinter.messagebox.showerror("Access Denied", "Invalid Username or Password.")

    def attempt_signup(self):
        school = self.reg_school.get()
        u = self.reg_user.get()
        p = self.reg_pass.get()
        c = self.reg_confirm.get()
        
        if not u or not p or not school:
            tkinter.messagebox.showwarning("Missing Info", "Please fill all fields.")
            return
            
        if p != c:
            tkinter.messagebox.showerror("Error", "Passwords do not match!")
            return
            
        success, msg = auth_manager.create_user(u, p, school)
        if success:
            cfg = config_manager.load_config()
            cfg["school_name"] = school
            config_manager.save_config(cfg)
            
            tkinter.messagebox.showinfo("Success", "Account Created! Please Login.")
            self.show_login_screen()
        else:
            tkinter.messagebox.showerror("Error", msg)

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def start_main_app(self):
        self.clear_window()
        self.title("Zionwol Digital System V5 - ADMIN ACCESS")
        
        self.config = config_manager.load_config()
        self.classes = list(self.config.get("class_maps", {}).keys())
        self.current_class = None
        self.broadsheet_path = None 
        
        self.setup_main_ui()
        self.check_files_loop()

    # --- 3. MAIN DASHBOARD UI ---
    def setup_main_ui(self):
        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(self.sidebar, text=f"ZIONWOL\nSYSTEM", font=("Arial", 20, "bold")).pack(pady=30)
        
        # SETUP BUTTON
        self.btn_setup = ctk.CTkButton(self.sidebar, text="⚙️ School Setup", command=self.launch_setup, fg_color="transparent", border_width=1)
        self.btn_setup.pack(pady=10, padx=20, fill="x")

        # SERVER BUTTON
        self.btn_server = ctk.CTkButton(self.sidebar, text="📡 Start Receiver", command=self.toggle_server, fg_color="#ea580c")
        self.btn_server.pack(pady=10, padx=20, fill="x")
        
        self.server_status = ctk.CTkLabel(self.sidebar, text="Server: OFFLINE", text_color="gray", font=("Arial", 11), wraplength=180)
        self.server_status.pack(pady=10)
        
        ctk.CTkButton(self.sidebar, text="🔒 Logout", command=self.show_login_screen, fg_color="#ef4444", height=30).pack(side="bottom", pady=20, padx=20, fill="x")

        # --- MAIN AREA ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Header
        head_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        head_frame.pack(fill="x")
        ctk.CTkLabel(head_frame, text="Active Class Dashboard", font=("Arial", 24, "bold")).pack(side="left")
        
        # Class Selector
        self.class_dropdown = ctk.CTkComboBox(self.main_area, values=self.classes, command=self.change_class, width=250)
        self.class_dropdown.set("Select Class...")
        self.class_dropdown.pack(pady=10, anchor="w")
        
        # Status Bar
        self.status_frame = ctk.CTkFrame(self.main_area, height=80)
        self.status_frame.pack(fill="x", pady=10)
        
        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Select a class to begin.", font=("Arial", 16))
        self.lbl_status.pack(pady=10, padx=10)
        self.lbl_file_count = ctk.CTkLabel(self.status_frame, text="", font=("Arial", 12), text_color="gray")
        self.lbl_file_count.pack()
        
        # Actions Area
        self.action_frame = ctk.CTkFrame(self.main_area)
        self.action_frame.pack(fill="both", expand=True, pady=10)
        
        # 1. REPORTS PANEL
        excel_box = ctk.CTkFrame(self.action_frame)
        excel_box.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(excel_box, text="📊 REPORTS CENTER", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.btn_excel = ctk.CTkButton(excel_box, text="⚡ Generate New Excel", command=self.run_excel, state="disabled", fg_color="#10b981")
        self.btn_excel.pack(pady=15)
        
        ttk_sep = ctk.CTkFrame(excel_box, height=2, fg_color="#404040")
        ttk_sep.pack(fill="x", padx=20, pady=10)
        
        self.lbl_open = ctk.CTkLabel(excel_box, text="Available Files:", font=("Arial", 12, "bold"))
        self.lbl_open.pack(pady=5)
        
        self.btn_open_excel = ctk.CTkButton(excel_box, text="📂 Open Broadsheet", command=self.open_current_excel, state="disabled", fg_color="transparent", border_width=1, text_color="white")
        self.btn_open_excel.pack(pady=5)

        # 2. ROBOT PANEL
        robot_box = ctk.CTkFrame(self.action_frame)
        robot_box.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(robot_box, text="🤖 AUTOMATION", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.btn_score = ctk.CTkButton(robot_box, text="Type Scores", command=lambda: self.run_robot("score"), state="disabled", fg_color="#3b8ed0")
        self.btn_score.pack(pady=5)
        
        self.btn_att = ctk.CTkButton(robot_box, text="Type Attendance", command=lambda: self.run_robot("attendance"), state="disabled", fg_color="#8b5cf6")
        self.btn_att.pack(pady=5)

        self.btn_assess = ctk.CTkButton(robot_box, text="Type Assessment", command=lambda: self.run_robot("assessment"), state="disabled", fg_color="#f97316")
        self.btn_assess.pack(pady=5)
        
        self.btn_audit = ctk.CTkButton(robot_box, text="🕵️ Run Audit", command=self.run_audit, state="disabled", fg_color="#eab308")
        self.btn_audit.pack(pady=10)

    # --- LOGIC METHODS ---
    def update_server_log(self, message):
        if "LINK ACTIVE" in message:
             self.server_status.configure(text=message, text_color="#10b981")
        elif "Error" in message or "❌" in message:
             self.server_status.configure(text=message, text_color="red")
        else:
             self.lbl_status.configure(text=message, text_color="#3b8ed0")
             self.server_status.configure(text=message, text_color="white")

    def toggle_server(self):
        self.btn_server.configure(state="disabled", text="Starting...")
        pc_receiver.start_server_thread(callback_func=self.update_server_log)

    def launch_setup(self):
        # ⚠️ CRITICAL FIX: Run as Separate Process ⚠️
        # This prevents the Dashboard from stealing the "Focus" of the Setup window variables
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "python", "school_setup.py"], shell=True)
            else:
                subprocess.Popen([sys.executable, "school_setup.py"])
        except Exception as e:
            tkinter.messagebox.showerror("Launcher Error", f"Could not open Setup:\n{e}")

    def change_class(self, choice):
        self.current_class = choice
        safe_class = self.current_class.replace(" ", "_")
        self.class_dir = os.path.join(BASE_DIR, safe_class)
        self.broadsheet_path = os.path.join(self.class_dir, f"{safe_class}_Broadsheet.xlsx")
        
        self.refresh_file_count()
        self.check_available_reports()
        
        self.btn_excel.configure(state="normal")
        self.btn_score.configure(state="normal")
        self.btn_att.configure(state="normal")
        self.btn_assess.configure(state="normal")
        self.btn_audit.configure(state="normal")

    def check_available_reports(self):
        if self.broadsheet_path and os.path.exists(self.broadsheet_path):
            self.btn_open_excel.configure(state="normal", text=f"📂 Open {self.current_class} Excel", fg_color="#059669")
        else:
            self.btn_open_excel.configure(state="disabled", text="No Report Found", fg_color="transparent")

    def open_current_excel(self):
        if self.broadsheet_path and os.path.exists(self.broadsheet_path):
            os.startfile(self.broadsheet_path)
        else:
            tkinter.messagebox.showerror("Error", "File not found!")

    def refresh_file_count(self):
        if not self.current_class: return
        safe_class = self.current_class.replace(" ", "_")
        subfolder = os.path.join(BASE_DIR, safe_class, "Scores")
        target_dir = subfolder if os.path.exists(subfolder) else os.path.join(BASE_DIR, safe_class)
            
        count = 0
        if os.path.exists(target_dir):
            count = len([f for f in os.listdir(target_dir) if f.endswith(".json") and "attendance" not in f.lower()])
            
        current_text = self.lbl_status.cget("text")
        if "Received" not in current_text and "Saved" not in current_text:
            self.lbl_status.configure(text=f"Active: {self.current_class}", text_color="white")
            self.lbl_file_count.configure(text=f"Files Collected: {count}")

    def check_files_loop(self):
        # We periodically reload config to check for new classes added by Setup
        if not self.current_class:
            reloaded_config = config_manager.load_config()
            new_classes = list(reloaded_config.get("class_maps", {}).keys())
            if len(new_classes) != len(self.classes):
                self.classes = new_classes
                self.class_dropdown.configure(values=self.classes)

        if self.current_class: 
            self.refresh_file_count()
            self.check_available_reports() 
        self.after(3000, self.check_files_loop)

    def run_excel(self):
        msg = excel_worker.generate_report(self.current_class)
        tkinter.messagebox.showinfo("Excel Generator", msg)
        self.check_available_reports() 

    def run_robot(self, mode):
        # Launcher Mode = Main Thread Call
        safe_class = self.current_class.replace(" ", "_")
        folder = os.path.join(BASE_DIR, safe_class)
        
        if mode == "attendance":
            worker.run_attendance_entry(folder)
        elif mode == "assessment":
            worker.run_assessment_entry(folder)
        else:
            is_preschool = any(x in self.current_class for x in ["KG", "Nursery"])
            if is_preschool:
                worker.run_preschool_entry(folder)
            else:
                worker.run_standard_entry(folder)

    def run_audit(self):
        safe_class = self.current_class.replace(" ", "_")
        folder = os.path.join(BASE_DIR, safe_class)
        threading.Thread(target=auditor.run_full_audit, args=(folder,)).start()

if __name__ == "__main__":
    app = ZionwolDashboard()
    app.mainloop()











# import customtkinter as ctk
# import os
# import threading
# import sys
# import subprocess
# import tkinter.messagebox
# 
# # IMPORT MODULES
# import config_manager
# import school_setup
# import excel_worker
# import worker
# import auditor
# import pc_receiver
# import auth_manager
# 
# ctk.set_appearance_mode("dark")
# ctk.set_default_color_theme("blue")
# 
# BASE_DIR = config_manager.BASE_DIR
# 
# class ZionwolDashboard(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         self.geometry("950x700")
#         self.title("Zionwol Digital System V5 - LOCKED")
#         
#         # Initialize User Database
#         auth_manager.init_db()
#         
#         if auth_manager.get_user_count() == 0:
#             self.show_signup_screen(first_time=True)
#         else:
#             self.show_login_screen()
# 
#     # --- 1. LOGIN SCREEN ---
#     def show_login_screen(self):
#         self.clear_window()
#         self.login_frame = ctk.CTkFrame(self)
#         self.login_frame.pack(fill="both", expand=True)
# 
#         box = ctk.CTkFrame(self.login_frame, width=350, height=400)
#         box.place(relx=0.5, rely=0.5, anchor="center")
#         
#         ctk.CTkLabel(box, text="🔒 SYSTEM LOCKED", font=("Arial", 22, "bold")).pack(pady=30)
#         
#         self.user_entry = ctk.CTkEntry(box, placeholder_text="Username", width=220)
#         self.user_entry.pack(pady=10)
#         
#         self.pass_entry = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=220)
#         self.pass_entry.pack(pady=10)
#         self.pass_entry.bind("<Return>", self.attempt_login)
#         
#         ctk.CTkButton(box, text="UNLOCK", command=self.attempt_login, width=220, fg_color="#3b8ed0").pack(pady=20)
#         
#         ctk.CTkButton(box, text="Create New Admin", command=lambda: self.show_signup_screen(False), 
#                       fg_color="transparent", text_color="gray", hover_color="#202020").pack(pady=5)
# 
#     # --- 2. SIGN UP SCREEN ---
#     def show_signup_screen(self, first_time=False):
#         self.clear_window()
#         self.signup_frame = ctk.CTkFrame(self)
#         self.signup_frame.pack(fill="both", expand=True)
# 
#         box = ctk.CTkFrame(self.signup_frame, width=400, height=500)
#         box.place(relx=0.5, rely=0.5, anchor="center")
#         
#         title = "🚀 WELCOME SETUP" if first_time else "REGISTER NEW ADMIN"
#         ctk.CTkLabel(box, text=title, font=("Arial", 20, "bold")).pack(pady=25)
#         
#         self.reg_school = ctk.CTkEntry(box, placeholder_text="School Name (e.g. Zionwol Int.)", width=250)
#         self.reg_school.pack(pady=10)
#         
#         self.reg_user = ctk.CTkEntry(box, placeholder_text="New Username", width=250)
#         self.reg_user.pack(pady=10)
#         
#         self.reg_pass = ctk.CTkEntry(box, placeholder_text="New Password", show="*", width=250)
#         self.reg_pass.pack(pady=10)
#         
#         self.reg_confirm = ctk.CTkEntry(box, placeholder_text="Confirm Password", show="*", width=250)
#         self.reg_confirm.pack(pady=10)
#         
#         ctk.CTkButton(box, text="CREATE ACCOUNT", command=self.attempt_signup, width=250, fg_color="#10b981").pack(pady=20)
#         
#         if not first_time:
#             ctk.CTkButton(box, text="< Back to Login", command=self.show_login_screen, fg_color="transparent").pack(pady=5)
# 
#     # --- AUTH LOGIC ---
#     def attempt_login(self, event=None):
#         u = self.user_entry.get()
#         p = self.pass_entry.get()
#         
#         if auth_manager.verify_user(u, p):
#             self.start_main_app()
#         else:
#             tkinter.messagebox.showerror("Access Denied", "Invalid Username or Password.")
# 
#     def attempt_signup(self):
#         school = self.reg_school.get()
#         u = self.reg_user.get()
#         p = self.reg_pass.get()
#         c = self.reg_confirm.get()
#         
#         if not u or not p or not school:
#             tkinter.messagebox.showwarning("Missing Info", "Please fill all fields.")
#             return
#             
#         if p != c:
#             tkinter.messagebox.showerror("Error", "Passwords do not match!")
#             return
#             
#         success, msg = auth_manager.create_user(u, p, school)
#         if success:
#             cfg = config_manager.load_config()
#             cfg["school_name"] = school
#             config_manager.save_config(cfg)
#             
#             tkinter.messagebox.showinfo("Success", "Account Created! Please Login.")
#             self.show_login_screen()
#         else:
#             tkinter.messagebox.showerror("Error", msg)
# 
#     def clear_window(self):
#         for widget in self.winfo_children():
#             widget.destroy()
# 
#     def start_main_app(self):
#         self.clear_window()
#         self.title("Zionwol Digital System V5 - ADMIN ACCESS")
#         
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.current_class = None
#         self.broadsheet_path = None # Store path to current excel
#         
#         self.setup_main_ui()
#         self.check_files_loop()
# 
#     # --- 3. MAIN DASHBOARD UI ---
#     def setup_main_ui(self):
#         # --- SIDEBAR ---
#         self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
#         self.sidebar.pack(side="left", fill="y")
#         
#         ctk.CTkLabel(self.sidebar, text=f"ZIONWOL\nSYSTEM", font=("Arial", 20, "bold")).pack(pady=30)
#         
#         self.btn_setup = ctk.CTkButton(self.sidebar, text="⚙️ School Setup", command=self.launch_setup, fg_color="transparent", border_width=1)
#         self.btn_setup.pack(pady=10, padx=20, fill="x")
# 
#         self.btn_server = ctk.CTkButton(self.sidebar, text="📡 Start Receiver", command=self.toggle_server, fg_color="#ea580c")
#         self.btn_server.pack(pady=10, padx=20, fill="x")
#         
#         self.server_status = ctk.CTkLabel(self.sidebar, text="Server: OFFLINE", text_color="gray", font=("Arial", 11), wraplength=180)
#         self.server_status.pack(pady=10)
#         
#         ctk.CTkButton(self.sidebar, text="🔒 Logout", command=self.show_login_screen, fg_color="#ef4444", height=30).pack(side="bottom", pady=20, padx=20, fill="x")
# 
#         # --- MAIN AREA ---
#         self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
#         self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
#         
#         # Header
#         head_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
#         head_frame.pack(fill="x")
#         ctk.CTkLabel(head_frame, text="Active Class Dashboard", font=("Arial", 24, "bold")).pack(side="left")
#         
#         # Class Selector
#         self.class_dropdown = ctk.CTkComboBox(self.main_area, values=self.classes, command=self.change_class, width=250)
#         self.class_dropdown.set("Select Class...")
#         self.class_dropdown.pack(pady=10, anchor="w")
#         
#         # Status Bar
#         self.status_frame = ctk.CTkFrame(self.main_area, height=80)
#         self.status_frame.pack(fill="x", pady=10)
#         
#         self.lbl_status = ctk.CTkLabel(self.status_frame, text="Select a class to begin.", font=("Arial", 16))
#         self.lbl_status.pack(pady=10, padx=10)
#         self.lbl_file_count = ctk.CTkLabel(self.status_frame, text="", font=("Arial", 12), text_color="gray")
#         self.lbl_file_count.pack()
#         
#         # Actions Area
#         self.action_frame = ctk.CTkFrame(self.main_area)
#         self.action_frame.pack(fill="both", expand=True, pady=10)
#         
#         # 1. REPORTS PANEL (UPDATED)
#         excel_box = ctk.CTkFrame(self.action_frame)
#         excel_box.pack(side="left", fill="both", expand=True, padx=10, pady=10)
#         
#         ctk.CTkLabel(excel_box, text="📊 REPORTS CENTER", font=("Arial", 16, "bold")).pack(pady=10)
#         
#         # Generate Button
#         self.btn_excel = ctk.CTkButton(excel_box, text="⚡ Generate New Excel", command=self.run_excel, state="disabled", fg_color="#10b981")
#         self.btn_excel.pack(pady=15)
#         
#         # Divider
#         ttk_sep = ctk.CTkFrame(excel_box, height=2, fg_color="#404040")
#         ttk_sep.pack(fill="x", padx=20, pady=10)
#         
#         # Open File Button (Dynamic)
#         self.lbl_open = ctk.CTkLabel(excel_box, text="Available Files:", font=("Arial", 12, "bold"))
#         self.lbl_open.pack(pady=5)
#         
#         self.btn_open_excel = ctk.CTkButton(excel_box, text="📂 Open Broadsheet", command=self.open_current_excel, state="disabled", fg_color="transparent", border_width=1, text_color="white")
#         self.btn_open_excel.pack(pady=5)
# 
#         self.btn_open_folder = ctk.CTkButton(excel_box, text="📂 Open Class Folder", command=self.open_class_folder, state="disabled", fg_color="transparent", text_color="gray")
#         self.btn_open_folder.pack(pady=5)
# 
#         # 2. ROBOT PANEL
#         robot_box = ctk.CTkFrame(self.action_frame)
#         robot_box.pack(side="right", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(robot_box, text="🤖 AUTOMATION", font=("Arial", 16, "bold")).pack(pady=10)
#         
#         self.btn_score = ctk.CTkButton(robot_box, text="Type Scores", command=lambda: self.run_robot("score"), state="disabled", fg_color="#3b8ed0")
#         self.btn_score.pack(pady=10)
#         
#         self.btn_att = ctk.CTkButton(robot_box, text="Type Attendance", command=lambda: self.run_robot("attendance"), state="disabled", fg_color="#8b5cf6")
#         self.btn_att.pack(pady=10)
#         
#         self.btn_audit = ctk.CTkButton(robot_box, text="🕵️ Run Audit", command=self.run_audit, state="disabled", fg_color="#eab308")
#         self.btn_audit.pack(pady=10)
# 
#     # --- LOGIC METHODS ---
#     def update_server_log(self, message):
#         if "LINK ACTIVE" in message:
#              self.server_status.configure(text=message, text_color="#10b981")
#         elif "Error" in message or "❌" in message:
#              self.server_status.configure(text=message, text_color="red")
#         else:
#              self.lbl_status.configure(text=message, text_color="#3b8ed0")
#              self.server_status.configure(text=message, text_color="white")
# 
#     def toggle_server(self):
#         self.btn_server.configure(state="disabled", text="Starting...")
#         pc_receiver.start_server_thread(callback_func=self.update_server_log)
# 
#     def launch_setup(self):
#         school_setup.ModernSetupApp()
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.class_dropdown.configure(values=self.classes)
# 
#     def change_class(self, choice):
#         self.current_class = choice
#         
#         # Determine paths
#         safe_class = self.current_class.replace(" ", "_")
#         self.class_dir = os.path.join(BASE_DIR, safe_class)
#         self.broadsheet_path = os.path.join(self.class_dir, f"{safe_class}_Broadsheet.xlsx")
#         
#         # Update UI state
#         self.refresh_file_count()
#         self.check_available_reports()
#         
#         # Enable Buttons
#         self.btn_excel.configure(state="normal")
#         self.btn_score.configure(state="normal")
#         self.btn_att.configure(state="normal")
#         self.btn_audit.configure(state="normal")
#         self.btn_open_folder.configure(state="normal")
# 
#     def check_available_reports(self):
#         """Checks if Excel exists and updates the Open button"""
#         if self.broadsheet_path and os.path.exists(self.broadsheet_path):
#             self.btn_open_excel.configure(state="normal", text=f"📂 Open {self.current_class} Excel", fg_color="#059669")
#         else:
#             self.btn_open_excel.configure(state="disabled", text="No Report Found", fg_color="transparent")
# 
#     def open_current_excel(self):
#         if self.broadsheet_path and os.path.exists(self.broadsheet_path):
#             os.startfile(self.broadsheet_path) # Windows Only
#         else:
#             tkinter.messagebox.showerror("Error", "File not found!")
# 
#     def open_class_folder(self):
#         if hasattr(self, 'class_dir') and os.path.exists(self.class_dir):
#             os.startfile(self.class_dir)
#         else:
#             tkinter.messagebox.showerror("Error", "Folder does not exist yet.")
# 
#     def refresh_file_count(self):
#         if not self.current_class: return
#         
#         # Logic to find files
#         safe_class = self.current_class.replace(" ", "_")
#         subfolder = os.path.join(BASE_DIR, safe_class, "Scores")
#         target_dir = subfolder if os.path.exists(subfolder) else os.path.join(BASE_DIR, safe_class)
#             
#         count = 0
#         if os.path.exists(target_dir):
#             count = len([f for f in os.listdir(target_dir) if f.endswith(".json") and "attendance" not in f.lower()])
#             
#         current_text = self.lbl_status.cget("text")
#         # Only update text if it's not showing a server message
#         if "Received" not in current_text and "Saved" not in current_text:
#             self.lbl_status.configure(text=f"Active: {self.current_class}", text_color="white")
#             self.lbl_file_count.configure(text=f"Files Collected: {count}")
# 
#     def check_files_loop(self):
#         if self.current_class: 
#             self.refresh_file_count()
#             self.check_available_reports() # Keep checking if Excel appeared
#         self.after(3000, self.check_files_loop)
# 
#     def run_excel(self):
#         msg = excel_worker.generate_report(self.current_class)
#         tkinter.messagebox.showinfo("Excel Generator", msg)
#         self.check_available_reports() # Update button immediately
# 
#     def run_robot(self, mode):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class)
#         if mode == "attendance":
#             threading.Thread(target=worker.run_attendance_entry, args=(folder,)).start()
#         else:
#             is_preschool = any(x in self.current_class for x in ["KG", "Nursery"])
#             if is_preschool:
#                 threading.Thread(target=worker.run_preschool_entry, args=(folder,)).start()
#             else:
#                 threading.Thread(target=worker.run_standard_entry, args=(folder,)).start()
# 
#     def run_audit(self):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class)
#         threading.Thread(target=auditor.run_full_audit, args=(folder,)).start()
# 
# if __name__ == "__main__":
#     app = ZionwolDashboard()
#     app.mainloop()















# import customtkinter as ctk
# import os
# import threading
# import sys
# import tkinter.messagebox
# 
# # IMPORT MODULES
# import config_manager
# import school_setup
# import excel_worker
# import worker
# import auditor
# import pc_receiver
# import auth_manager  # <--- NEW SECURITY MODULE
# 
# ctk.set_appearance_mode("dark")
# ctk.set_default_color_theme("blue")
# 
# BASE_DIR = config_manager.BASE_DIR
# 
# class ZionwolDashboard(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         self.geometry("900x700")
#         self.title("Zionwol Digital System V5 - LOCKED")
#         
#         # Initialize User Database
#         auth_manager.init_db()
#         
#         # Decide: Login or Sign Up?
#         if auth_manager.get_user_count() == 0:
#             self.show_signup_screen(first_time=True)
#         else:
#             self.show_login_screen()
# 
#     # --- 1. LOGIN SCREEN ---
#     def show_login_screen(self):
#         self.clear_window()
#         
#         self.login_frame = ctk.CTkFrame(self)
#         self.login_frame.pack(fill="both", expand=True)
# 
#         box = ctk.CTkFrame(self.login_frame, width=350, height=400)
#         box.place(relx=0.5, rely=0.5, anchor="center")
#         
#         ctk.CTkLabel(box, text="🔒 SYSTEM LOCKED", font=("Arial", 22, "bold")).pack(pady=30)
#         
#         self.user_entry = ctk.CTkEntry(box, placeholder_text="Username", width=220)
#         self.user_entry.pack(pady=10)
#         
#         self.pass_entry = ctk.CTkEntry(box, placeholder_text="Password", show="*", width=220)
#         self.pass_entry.pack(pady=10)
#         self.pass_entry.bind("<Return>", self.attempt_login)
#         
#         ctk.CTkButton(box, text="UNLOCK", command=self.attempt_login, width=220, fg_color="#3b8ed0").pack(pady=20)
#         
#         # Sign Up Link
#         ctk.CTkButton(box, text="Create New Admin", command=lambda: self.show_signup_screen(False), 
#                       fg_color="transparent", text_color="gray", hover_color="#202020").pack(pady=5)
# 
#     # --- 2. SIGN UP SCREEN ---
#     def show_signup_screen(self, first_time=False):
#         self.clear_window()
#         
#         self.signup_frame = ctk.CTkFrame(self)
#         self.signup_frame.pack(fill="both", expand=True)
# 
#         box = ctk.CTkFrame(self.signup_frame, width=400, height=500)
#         box.place(relx=0.5, rely=0.5, anchor="center")
#         
#         title = "🚀 WELCOME SETUP" if first_time else "REGISTER NEW ADMIN"
#         ctk.CTkLabel(box, text=title, font=("Arial", 20, "bold")).pack(pady=25)
#         
#         self.reg_school = ctk.CTkEntry(box, placeholder_text="School Name (e.g. Zionwol Int.)", width=250)
#         self.reg_school.pack(pady=10)
#         
#         self.reg_user = ctk.CTkEntry(box, placeholder_text="New Username", width=250)
#         self.reg_user.pack(pady=10)
#         
#         self.reg_pass = ctk.CTkEntry(box, placeholder_text="New Password", show="*", width=250)
#         self.reg_pass.pack(pady=10)
#         
#         self.reg_confirm = ctk.CTkEntry(box, placeholder_text="Confirm Password", show="*", width=250)
#         self.reg_confirm.pack(pady=10)
#         
#         ctk.CTkButton(box, text="CREATE ACCOUNT", command=self.attempt_signup, width=250, fg_color="#10b981").pack(pady=20)
#         
#         if not first_time:
#             ctk.CTkButton(box, text="< Back to Login", command=self.show_login_screen, fg_color="transparent").pack(pady=5)
# 
#     # --- AUTH LOGIC ---
#     def attempt_login(self, event=None):
#         u = self.user_entry.get()
#         p = self.pass_entry.get()
#         
#         if auth_manager.verify_user(u, p):
#             self.start_main_app()
#         else:
#             tkinter.messagebox.showerror("Access Denied", "Invalid Username or Password.")
# 
#     def attempt_signup(self):
#         school = self.reg_school.get()
#         u = self.reg_user.get()
#         p = self.reg_pass.get()
#         c = self.reg_confirm.get()
#         
#         if not u or not p or not school:
#             tkinter.messagebox.showwarning("Missing Info", "Please fill all fields.")
#             return
#             
#         if p != c:
#             tkinter.messagebox.showerror("Error", "Passwords do not match!")
#             return
#             
#         success, msg = auth_manager.create_user(u, p, school)
#         if success:
#             # Update School Name in Config
#             cfg = config_manager.load_config()
#             cfg["school_name"] = school
#             config_manager.save_config(cfg)
#             
#             tkinter.messagebox.showinfo("Success", "Account Created! Please Login.")
#             self.show_login_screen()
#         else:
#             tkinter.messagebox.showerror("Error", msg)
# 
#     def clear_window(self):
#         for widget in self.winfo_children():
#             widget.destroy()
# 
#     def start_main_app(self):
#         self.clear_window()
#         self.title("Zionwol Digital System V5 - ADMIN ACCESS")
#         
#         # Load Config
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.current_class = None
#         
#         self.setup_main_ui()
#         self.check_files_loop()
# 
#     # --- 3. MAIN DASHBOARD UI ---
#     def setup_main_ui(self):
#         # --- SIDEBAR (Navigation) ---
#         self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
#         self.sidebar.pack(side="left", fill="y")
#         
#         ctk.CTkLabel(self.sidebar, text=f"ZIONWOL\nSYSTEM", font=("Arial", 20, "bold")).pack(pady=30)
#         
#         self.btn_setup = ctk.CTkButton(self.sidebar, text="⚙️ School Setup", command=self.launch_setup, fg_color="transparent", border_width=1)
#         self.btn_setup.pack(pady=10, padx=20, fill="x")
# 
#         self.btn_server = ctk.CTkButton(self.sidebar, text="📡 Start Receiver", command=self.toggle_server, fg_color="#ea580c")
#         self.btn_server.pack(pady=10, padx=20, fill="x")
#         
#         self.server_status = ctk.CTkLabel(self.sidebar, text="Server: OFFLINE", text_color="gray", font=("Arial", 11), wraplength=180)
#         self.server_status.pack(pady=10)
#         
#         # Logout Button
#         ctk.CTkButton(self.sidebar, text="🔒 Logout", command=self.show_login_screen, fg_color="#ef4444", height=30).pack(side="bottom", pady=20, padx=20, fill="x")
# 
#         # --- MAIN AREA ---
#         self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
#         self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
#         
#         ctk.CTkLabel(self.main_area, text="Active Class Dashboard", font=("Arial", 24, "bold")).pack(anchor="w")
#         
#         self.class_dropdown = ctk.CTkComboBox(self.main_area, values=self.classes, command=self.change_class, width=250)
#         self.class_dropdown.set("Select Class...")
#         self.class_dropdown.pack(pady=10, anchor="w")
#         
#         self.status_frame = ctk.CTkFrame(self.main_area, height=100)
#         self.status_frame.pack(fill="x", pady=10)
#         
#         self.lbl_status = ctk.CTkLabel(self.status_frame, text="Select a class to see files.", font=("Arial", 16))
#         self.lbl_status.pack(pady=15, padx=10)
#         
#         self.action_frame = ctk.CTkFrame(self.main_area)
#         self.action_frame.pack(fill="both", expand=True, pady=10)
#         
#         excel_box = ctk.CTkFrame(self.action_frame)
#         excel_box.pack(side="left", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(excel_box, text="📊 REPORTS", font=("Arial", 16, "bold")).pack(pady=10)
#         ctk.CTkLabel(excel_box, text="Merge JSONs into Excel Broadsheet", font=("Arial", 12)).pack()
#         self.btn_excel = ctk.CTkButton(excel_box, text="Generate Excel", command=self.run_excel, state="disabled", fg_color="#10b981")
#         self.btn_excel.pack(pady=20)
# 
#         robot_box = ctk.CTkFrame(self.action_frame)
#         robot_box.pack(side="right", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(robot_box, text="🤖 AUTO-TYPING", font=("Arial", 16, "bold")).pack(pady=10)
#         self.btn_score = ctk.CTkButton(robot_box, text="Type Scores", command=lambda: self.run_robot("score"), state="disabled", fg_color="#3b8ed0")
#         self.btn_score.pack(pady=10)
#         self.btn_att = ctk.CTkButton(robot_box, text="Type Attendance", command=lambda: self.run_robot("attendance"), state="disabled", fg_color="#8b5cf6")
#         self.btn_att.pack(pady=10)
#         self.btn_audit = ctk.CTkButton(robot_box, text="🕵️ Run Audit", command=self.run_audit, state="disabled", fg_color="#eab308")
#         self.btn_audit.pack(pady=10)
# 
#     # --- LOGIC METHODS ---
#     def update_server_log(self, message):
#         if "LINK ACTIVE" in message:
#              self.server_status.configure(text=message, text_color="#10b981")
#         elif "Error" in message or "❌" in message:
#              self.server_status.configure(text=message, text_color="red")
#         else:
#              self.lbl_status.configure(text=message, text_color="#3b8ed0")
#              self.server_status.configure(text=message, text_color="white")
# 
#     def toggle_server(self):
#         self.btn_server.configure(state="disabled", text="Starting...")
#         pc_receiver.start_server_thread(callback_func=self.update_server_log)
# 
#     def launch_setup(self):
#         school_setup.ModernSetupApp()
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.class_dropdown.configure(values=self.classes)
# 
#     def change_class(self, choice):
#         self.current_class = choice
#         self.refresh_file_count()
#         self.btn_excel.configure(state="normal")
#         self.btn_score.configure(state="normal")
#         self.btn_att.configure(state="normal")
#         self.btn_audit.configure(state="normal")
# 
#     def refresh_file_count(self):
#         if not self.current_class: return
#         safe_class = self.current_class.replace(" ", "_")
#         # Check subfolder first as per new logic
#         subfolder = os.path.join(BASE_DIR, safe_class, "Scores")
#         if os.path.exists(subfolder):
#             class_dir = subfolder
#         else:
#             class_dir = os.path.join(BASE_DIR, safe_class)
#             
#         count = 0
#         if os.path.exists(class_dir):
#             count = len([f for f in os.listdir(class_dir) if f.endswith(".json") and "attendance" not in f.lower()])
#             
#         current_text = self.lbl_status.cget("text")
#         if "Received" not in current_text and "Saved" not in current_text:
#             self.lbl_status.configure(text=f"Selected: {self.current_class}  |  Files: {count}", text_color="white")
# 
#     def check_files_loop(self):
#         if self.current_class: self.refresh_file_count()
#         self.after(3000, self.check_files_loop)
# 
#     def run_excel(self):
#         msg = excel_worker.generate_report(self.current_class)
#         tkinter.messagebox.showinfo("Excel Generator", msg)
# 
#     def run_robot(self, mode):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class)
#         if mode == "attendance":
#             threading.Thread(target=worker.run_attendance_entry, args=(folder,)).start()
#         else:
#             is_preschool = any(x in self.current_class for x in ["KG", "Nursery"])
#             if is_preschool:
#                 threading.Thread(target=worker.run_preschool_entry, args=(folder,)).start()
#             else:
#                 threading.Thread(target=worker.run_standard_entry, args=(folder,)).start()
# 
#     def run_audit(self):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class)
#         threading.Thread(target=auditor.run_full_audit, args=(folder,)).start()
# 
# if __name__ == "__main__":
#     app = ZionwolDashboard()
#     app.mainloop()











# import customtkinter as ctk
# import os
# import threading
# import sys
# import tkinter.messagebox
# 
# # IMPORT YOUR MODULES
# import config_manager
# import school_setup
# import excel_worker
# import worker
# import auditor
# import pc_receiver 
# 
# # --- SETUP ---
# ctk.set_appearance_mode("dark")
# ctk.set_default_color_theme("blue")
# 
# BASE_DIR = config_manager.BASE_DIR
# 
# class ZionwolDashboard(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         self.geometry("900x700")
#         self.title("Zionwol Digital System V5")
#         
#         # Load Config
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.current_class = None
#         
#         self.setup_ui()
#         
#         # Start the Auto-Refresh Loop
#         self.check_files_loop()
#         
#     def setup_ui(self):
#         # --- SIDEBAR (Navigation) ---
#         self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
#         self.sidebar.pack(side="left", fill="y")
#         
#         ctk.CTkLabel(self.sidebar, text="ZIONWOL\nSYSTEM", font=("Arial", 20, "bold")).pack(pady=30)
#         
#         self.btn_setup = ctk.CTkButton(self.sidebar, text="⚙️ School Setup", command=self.launch_setup, fg_color="transparent", border_width=1)
#         self.btn_setup.pack(pady=10, padx=20, fill="x")
# 
#         self.btn_server = ctk.CTkButton(self.sidebar, text="📡 Start Receiver", command=self.toggle_server, fg_color="#ea580c")
#         self.btn_server.pack(pady=10, padx=20, fill="x")
#         
#         # Server Status Label (Updates with logs)
#         self.server_status = ctk.CTkLabel(self.sidebar, text="Server: OFFLINE", text_color="gray", font=("Arial", 11), wraplength=180)
#         self.server_status.pack(pady=10)
#         
#         # --- MAIN AREA ---
#         self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
#         self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
#         
#         # 1. CLASS SELECTION
#         ctk.CTkLabel(self.main_area, text="Active Class Dashboard", font=("Arial", 24, "bold")).pack(anchor="w")
#         
#         self.class_dropdown = ctk.CTkComboBox(self.main_area, values=self.classes, command=self.change_class, width=250)
#         self.class_dropdown.set("Select Class...")
#         self.class_dropdown.pack(pady=10, anchor="w")
#         
#         # Status Frame (Shows logs and file counts)
#         self.status_frame = ctk.CTkFrame(self.main_area, height=100)
#         self.status_frame.pack(fill="x", pady=10)
#         
#         self.lbl_status = ctk.CTkLabel(self.status_frame, text="Select a class to see files.", font=("Arial", 16))
#         self.lbl_status.pack(pady=15, padx=10)
#         
#         # 2. ACTIONS (Excel & Robot)
#         self.action_frame = ctk.CTkFrame(self.main_area)
#         self.action_frame.pack(fill="both", expand=True, pady=10)
#         
#         # --- EXCEL SECTION ---
#         excel_box = ctk.CTkFrame(self.action_frame)
#         excel_box.pack(side="left", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(excel_box, text="📊 REPORTS", font=("Arial", 16, "bold")).pack(pady=10)
#         ctk.CTkLabel(excel_box, text="Merge JSONs into Excel Broadsheet", font=("Arial", 12)).pack()
#         
#         self.btn_excel = ctk.CTkButton(excel_box, text="Generate Excel", command=self.run_excel, state="disabled", fg_color="#10b981")
#         self.btn_excel.pack(pady=20)
# 
#         # --- ROBOT SECTION ---
#         robot_box = ctk.CTkFrame(self.action_frame)
#         robot_box.pack(side="right", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(robot_box, text="🤖 AUTO-TYPING", font=("Arial", 16, "bold")).pack(pady=10)
#         
#         self.btn_score = ctk.CTkButton(robot_box, text="Type Scores", command=lambda: self.run_robot("score"), state="disabled", fg_color="#3b8ed0")
#         self.btn_score.pack(pady=10)
#         
#         self.btn_att = ctk.CTkButton(robot_box, text="Type Attendance", command=lambda: self.run_robot("attendance"), state="disabled", fg_color="#8b5cf6")
#         self.btn_att.pack(pady=10)
# 
#         self.btn_audit = ctk.CTkButton(robot_box, text="🕵️ Run Audit", command=self.run_audit, state="disabled", fg_color="#eab308")
#         self.btn_audit.pack(pady=10)
# 
#     # --- SERVER LOGIC ---
#     def update_server_log(self, message):
#         """Called by pc_receiver to update the UI text"""
#         # If it's a "Link" message, show it clearly
#         if "LINK ACTIVE" in message:
#              self.server_status.configure(text=message, text_color="#10b981") # Green
#         elif "Error" in message or "❌" in message:
#              self.server_status.configure(text=message, text_color="red")
#         else:
#              # For normal "Received" messages, update the MAIN Status Label
#              self.lbl_status.configure(text=message, text_color="#3b8ed0") # Blue
#              
#              # Also update sidebar briefly
#              self.server_status.configure(text=message, text_color="white")
# 
#     def toggle_server(self):
#         # Start Server AND Ngrok (pass our update function)
#         self.btn_server.configure(state="disabled", text="Starting...")
#         pc_receiver.start_server_thread(callback_func=self.update_server_log)
# 
#     # --- UI LOGIC ---
#     def launch_setup(self):
#         school_setup.ModernSetupApp()
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.class_dropdown.configure(values=self.classes)
# 
#     def change_class(self, choice):
#         self.current_class = choice
#         self.refresh_file_count() # Check immediately
#         
#         # Enable Buttons
#         self.btn_excel.configure(state="normal")
#         self.btn_score.configure(state="normal")
#         self.btn_att.configure(state="normal")
#         self.btn_audit.configure(state="normal")
# 
#     def refresh_file_count(self):
#         """Counts files in the folder and updates UI"""
#         if not self.current_class: return
# 
#         safe_class = self.current_class.replace(" ", "_")
#         class_dir = os.path.join(BASE_DIR, safe_class, "Scores")
#         
#         count = 0
#         if os.path.exists(class_dir):
#             count = len([f for f in os.listdir(class_dir) if f.endswith(".json")])
#         
#         # Only update if we aren't showing a "Received" message
#         current_text = self.lbl_status.cget("text")
#         if "Received" not in current_text and "Saved" not in current_text:
#             self.lbl_status.configure(text=f"Selected: {self.current_class}  |  Files: {count}", text_color="white")
# 
#     def check_files_loop(self):
#         """Runs every 3 seconds to keep counts updated"""
#         self.refresh_file_count()
#         self.after(3000, self.check_files_loop)
# 
#     def run_excel(self):
#         msg = excel_worker.generate_report(self.current_class)
#         tkinter.messagebox.showinfo("Excel Generator", msg)
# 
#     def run_robot(self, mode):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class)
#         
#         if mode == "attendance":
#             threading.Thread(target=worker.run_attendance_entry, args=(folder,)).start()
#         else:
#             is_preschool = any(x in self.current_class for x in ["KG", "Nursery"])
#             if is_preschool:
#                 threading.Thread(target=worker.run_preschool_entry, args=(folder,)).start()
#             else:
#                 threading.Thread(target=worker.run_standard_entry, args=(folder,)).start()
# 
#     def run_audit(self):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class, "Scores")
#         threading.Thread(target=auditor.run_full_audit, args=(folder,)).start()
# 
# if __name__ == "__main__":
#     app = ZionwolDashboard()
#     app.mainloop()








# import customtkinter as ctk
# import os
# import threading
# import sys
# import webbrowser
# 
# # IMPORT YOUR MODULES
# import config_manager
# import school_setup
# import excel_worker
# import worker
# import auditor
# import pc_receiver  # Ensure you added the start_server_thread function above
# 
# # --- SETUP ---
# ctk.set_appearance_mode("dark")
# ctk.set_default_color_theme("blue")
# 
# BASE_DIR = config_manager.BASE_DIR # "School_Data"
# 
# class ZionwolDashboard(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         self.geometry("900x700")
#         self.title("Zionwol Digital System V5")
#         
#         # Load Config
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.current_class = None
#         
#         self.setup_ui()
#         
#     def setup_ui(self):
#         # --- SIDEBAR (Navigation) ---
#         self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
#         self.sidebar.pack(side="left", fill="y")
#         
#         ctk.CTkLabel(self.sidebar, text="ZIONWOL\nSYSTEM", font=("Arial", 20, "bold")).pack(pady=30)
#         
#         self.btn_setup = ctk.CTkButton(self.sidebar, text="⚙️ School Setup", command=self.launch_setup, fg_color="transparent", border_width=1)
#         self.btn_setup.pack(pady=10, padx=20, fill="x")
# 
#         self.btn_server = ctk.CTkButton(self.sidebar, text="📡 Start Receiver", command=self.toggle_server, fg_color="#ea580c")
#         self.btn_server.pack(pady=10, padx=20, fill="x")
#         self.server_status = ctk.CTkLabel(self.sidebar, text="Server: OFFLINE", text_color="red", font=("Arial", 10))
#         self.server_status.pack(pady=0)
#         
#         # --- MAIN AREA ---
#         self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
#         self.main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
#         
#         # 1. CLASS SELECTION
#         ctk.CTkLabel(self.main_area, text="Active Class Dashboard", font=("Arial", 24, "bold")).pack(anchor="w")
#         
#         self.class_dropdown = ctk.CTkComboBox(self.main_area, values=self.classes, command=self.change_class, width=250)
#         self.class_dropdown.set("Select Class...")
#         self.class_dropdown.pack(pady=10, anchor="w")
#         
#         self.status_frame = ctk.CTkFrame(self.main_area, height=100)
#         self.status_frame.pack(fill="x", pady=10)
#         self.lbl_status = ctk.CTkLabel(self.status_frame, text="No Class Selected", font=("Arial", 14))
#         self.lbl_status.pack(pady=10, padx=10)
# 
#         # 2. ACTIONS (Excel & Robot)
#         self.action_frame = ctk.CTkFrame(self.main_area)
#         self.action_frame.pack(fill="both", expand=True, pady=10)
#         
#         # --- EXCEL SECTION ---
#         excel_box = ctk.CTkFrame(self.action_frame)
#         excel_box.pack(side="left", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(excel_box, text="📊 REPORTS", font=("Arial", 16, "bold")).pack(pady=10)
#         ctk.CTkLabel(excel_box, text="Merge JSONs into Excel Broadsheet", font=("Arial", 12)).pack()
#         
#         self.btn_excel = ctk.CTkButton(excel_box, text="Generate Excel", command=self.run_excel, state="disabled", fg_color="#10b981")
#         self.btn_excel.pack(pady=20)
# 
#         # --- ROBOT SECTION ---
#         robot_box = ctk.CTkFrame(self.action_frame)
#         robot_box.pack(side="right", fill="both", expand=True, padx=10, pady=10)
#         ctk.CTkLabel(robot_box, text="🤖 AUTO-TYPING", font=("Arial", 16, "bold")).pack(pady=10)
#         
#         self.btn_score = ctk.CTkButton(robot_box, text="Type Scores", command=lambda: self.run_robot("score"), state="disabled", fg_color="#3b8ed0")
#         self.btn_score.pack(pady=10)
#         
#         self.btn_att = ctk.CTkButton(robot_box, text="Type Attendance", command=lambda: self.run_robot("attendance"), state="disabled", fg_color="#8b5cf6")
#         self.btn_att.pack(pady=10)
# 
#         self.btn_audit = ctk.CTkButton(robot_box, text="🕵️ Run Audit", command=self.run_audit, state="disabled", fg_color="#eab308")
#         self.btn_audit.pack(pady=10)
# 
#     # --- LOGIC ---
#     def launch_setup(self):
#         # Open the setup window
#         school_setup.ModernSetupApp()
#         # Reload config after setup closes
#         self.config = config_manager.load_config()
#         self.classes = list(self.config.get("class_maps", {}).keys())
#         self.class_dropdown.configure(values=self.classes)
# 
#     def toggle_server(self):
#         # Start Flask in a background thread
#         pc_receiver.start_server_thread()
#         self.btn_server.configure(state="disabled", text="Running...")
#         self.server_status.configure(text="Server: ONLINE (Port 5000)", text_color="#10b981")
#         # Optional: Open Ngrok instructions
#         # webbrowser.open("http://localhost:4040") 
# 
#     def change_class(self, choice):
#         self.current_class = choice
#         
#         # Check files
#         safe_class = choice.replace(" ", "_")
#         class_dir = os.path.join(BASE_DIR, safe_class, "Scores")
#         
#         count = 0
#         if os.path.exists(class_dir):
#             count = len([f for f in os.listdir(class_dir) if f.endswith(".json")])
#             
#         self.lbl_status.configure(text=f"Selected: {choice}  |  Files Received: {count}")
#         
#         # Enable Buttons
#         self.btn_excel.configure(state="normal")
#         self.btn_score.configure(state="normal")
#         self.btn_att.configure(state="normal")
#         self.btn_audit.configure(state="normal")
# 
#     def run_excel(self):
#         msg = excel_worker.generate_report(self.current_class)
#         # Using a simple popup logic (ctk doesn't have native messagebox yet, using print/label is safer or tk messagebox)
#         import tkinter.messagebox
#         tkinter.messagebox.showinfo("Excel Generator", msg)
# 
#     def run_robot(self, mode):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class)
#         
#         if mode == "attendance":
#             threading.Thread(target=worker.run_attendance_entry, args=(folder,)).start()
#         else:
#             # Check for Preschool
#             is_preschool = any(x in self.current_class for x in ["KG", "Nursery"])
#             if is_preschool:
#                 threading.Thread(target=worker.run_preschool_entry, args=(folder,)).start()
#             else:
#                 threading.Thread(target=worker.run_standard_entry, args=(folder,)).start()
# 
#     def run_audit(self):
#         safe_class = self.current_class.replace(" ", "_")
#         folder = os.path.join(BASE_DIR, safe_class, "Scores") # Audit looks at scores
#         threading.Thread(target=auditor.run_full_audit, args=(folder,)).start()
# 
# if __name__ == "__main__":
#     app = ZionwolDashboard()
#     app.mainloop()