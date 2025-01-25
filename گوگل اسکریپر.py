import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
import subprocess
import sys
import queue
import importlib.util

# تابع برای بررسی و نصب پیش‌نیازها
def install_requirements():
    required_libraries = ["requests", "beautifulsoup4", "pandas", "tldextract", "openpyxl"]
    for lib in required_libraries:
        if importlib.util.find_spec(lib) is None:
            print(f"نصب {lib}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                print(f"{lib} با موفقیت نصب شد.")
            except Exception as e:
                print(f"خطا در نصب {lib}: {e}")
                messagebox.showerror("خطا", f"خطا در نصب {lib}. لطفاً دستی نصب کنید.")
                sys.exit(1)  # خروج از برنامه در صورت خطا
        else:
            print(f"{lib} از قبل نصب شده است.")

# بررسی و نصب پیش‌نیازها قبل از اجرای برنامه
install_requirements()

# حالا می‌توانیم کتابخانه‌ها را ایمپورت کنیم
import requests
from bs4 import BeautifulSoup
import pandas as pd
import tldextract
from concurrent.futures import ThreadPoolExecutor, as_completed

# تابع برای انجام جستجو در گوگل
def google_search(query, num_results):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    search_url = f"https://www.google.com/search?q={query}&num={num_results + 10}"  # ۱۰ نتیجه بیشتر برای اطمینان
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # استخراج لینک‌ها و عنوان‌ها از نتایج جستجو
    results = []
    for item in soup.find_all("div", attrs={"class": "tF2Cxc"}):
        link = item.find("a")["href"]
        title = item.find("h3").text if item.find("h3") else "بدون عنوان"
        results.append({"url": link, "title": title})
    
    # فقط تعداد درخواستی را برمی‌گردانیم
    return results[:num_results]

# تابع برای استخراج نام اصلی سایت از صفحه اصلی
def get_site_name(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        site_name = soup.title.string.strip() if soup.title else None
        return site_name
    except:
        return None

# تابع برای استخراج دامنه و نام سایت
def extract_domain_and_site_name(url, page_title, progress_callback):
    extracted = tldextract.extract(url)
    domain = f"{extracted.domain}.{extracted.suffix}"
    
    # ساخت URL صفحه اصلی
    main_page_url = f"https://{domain}"
    
    # دریافت نام اصلی سایت از صفحه اصلی
    site_name = get_site_name(main_page_url)
    
    # اگر نام اصلی سایت وجود نداشت، از عنوان صفحه استفاده کن
    if not site_name:
        site_name = page_title
    
    # به‌روزرسانی پیشرفت
    progress_callback()
    
    return domain, site_name

# تابع برای انجام جستجو و ذخیره‌سازی نتایج
def perform_search():
    query = entry_query.get()
    num_results = int(entry_num_results.get())
    
    if not query or num_results <= 0:
        messagebox.showerror("خطا", "لطفاً عبارت جستجو و تعداد نتایج را به درستی وارد کنید.")
        return
    
    # غیرفعال کردن دکمه جستجو در حین اجرا
    button_search.config(state=tk.DISABLED)
    
    # اجرای عملیات جستجو در یک thread جداگانه
    threading.Thread(target=search_and_save, args=(query, num_results), daemon=True).start()

# تابع اصلی برای جستجو و ذخیره‌سازی (در thread جداگانه اجرا می‌شود)
def search_and_save(query, num_results):
    try:
        # دریافت مسیر فعلی (همان پوشه‌ای که فایل پایتون قرار دارد)
        save_path = os.getcwd()
        
        # ساخت نام فایل
        file_name = f"{query} {num_results}.xlsx"
        full_path = os.path.join(save_path, file_name)
        
        # انجام جستجو در گوگل
        search_results = google_search(query, num_results)
        
        # تنظیم نوار پیشرفت
        progress_bar["maximum"] = len(search_results)
        progress_bar["value"] = 0
        status_label.config(text="در حال بررسی... (۰ از {})".format(len(search_results)))
        app.update_idletasks()
        
        # استخراج دامنه‌ها و نام سایت‌ها به صورت موازی
        data = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for result in search_results:
                futures.append(executor.submit(
                    extract_domain_and_site_name,
                    result["url"],
                    result["title"],
                    lambda: update_progress(len(data) + 1, len(search_results))
                ))
            
            for future in as_completed(futures):
                domain, site_name = future.result()
                data.append({"Domain": domain, "Site Name": site_name})
        
        # حذف نتایج تکراری بر اساس دامنه
        unique_data = []
        seen_domains = set()
        for item in data:
            if item["Domain"] not in seen_domains:
                unique_data.append(item)
                seen_domains.add(item["Domain"])
        
        # ذخیره‌سازی نتایج در فایل اکسل
        df = pd.DataFrame(unique_data)
        df.to_excel(full_path, index=False)
        
        # ارسال پیام موفقیت به thread اصلی
        message_queue.put(("success", f"نتایج با موفقیت در فایل زیر ذخیره شدند:\n{full_path}\nتعداد دامنه‌های منحصر به فرد: {len(unique_data)}"))
    except Exception as e:
        # ارسال پیام خطا به thread اصلی
        message_queue.put(("error", f"خطایی رخ داد: {str(e)}"))
    finally:
        # ارسال پیام بازنشانی به thread اصلی
        message_queue.put(("reset", None))

# تابع برای به‌روزرسانی نوار پیشرفت و برچسب وضعیت
def update_progress(current, total):
    progress_bar["value"] = current
    status_label.config(text="در حال بررسی... ({} از {})".format(current, total))
    app.update_idletasks()

# تابع برای بررسی صف پیام‌ها و به‌روزرسانی رابط کاربری
def check_message_queue():
    try:
        while True:
            message_type, message = message_queue.get_nowait()
            if message_type == "success":
                messagebox.showinfo("موفقیت", message)
            elif message_type == "error":
                messagebox.showerror("خطا", message)
            elif message_type == "reset":
                progress_bar["value"] = 0
                status_label.config(text="آماده")
                button_search.config(state=tk.NORMAL)
    except queue.Empty:
        pass
    finally:
        # بررسی مجدد صف پس از ۱۰۰ میلی‌ثانیه
        app.after(100, check_message_queue)

# ایجاد رابط کاربری
app = tk.Tk()
app.title("جستجوگر گوگل و استخراج دامنه")

# صف پیام‌ها برای ارتباط بین thread‌ها
message_queue = queue.Queue()

# برچسب و فیلد ورودی برای عبارت جستجو
label_query = tk.Label(app, text="عبارت جستجو:")
label_query.pack(pady=5)
entry_query = tk.Entry(app, width=50)
entry_query.pack(pady=5)

# برچسب و فیلد ورودی برای تعداد نتایج
label_num_results = tk.Label(app, text="تعداد نتایج:")
label_num_results.pack(pady=5)
entry_num_results = tk.Entry(app, width=10)
entry_num_results.pack(pady=5)

# نوار پیشرفت
progress_bar = ttk.Progressbar(app, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=10)

# برچسب وضعیت
status_label = tk.Label(app, text="آماده")
status_label.pack(pady=5)

# دکمه برای شروع جستجو
button_search = tk.Button(app, text="جستجو و ذخیره نتایج", command=perform_search)
button_search.pack(pady=20)

# شروع بررسی صف پیام‌ها
app.after(100, check_message_queue)

# اجرای برنامه
app.mainloop()
