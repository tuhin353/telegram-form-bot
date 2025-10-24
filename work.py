import telebot
import re
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime

# ======== CONFIG ========
BOT_TOKEN = "8473799166:AAFvNq_TsV-su4-72whOLu0Z6z19cL_YDoI"
CHROMEDRIVER_PATH = r"C:\Users\TUHIN\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSebxwdOEoN7eGcQt5B5zRemgJvmykyIliE6Q3GxgpuDz_1rEw/viewform"
# =========================

bot = telebot.TeleBot(BOT_TOKEN)
submitted_orders = set()


def parse_message(text):
    data = {"order_number": "", "address": "", "cost": "", "km": ""}
    parts = re.split(r'[\n,]+', text)
    for p in parts:
        if ':' in p:
            k, v = p.split(':', 1)
            k = k.strip().lower()
            v = v.strip()
            if 'order' in k:
                data['order_number'] = v
            elif 'address' in k:
                data['address'] = v
            elif 'cost' in k:
                data['cost'] = v
            elif 'km' in k:
                km = re.findall(r'\d+', v)
                data['km'] = km[0] if km else v
    return data


def force_click_dropdown(driver, label_text, option_text):
    try:
        question_block = driver.find_element(By.XPATH, f"//*[contains(text(), '{label_text}')]/ancestor::div[@role='listitem']")
        dropdown_area = question_block.find_element(By.XPATH, ".//div[@role='listbox']")
        ActionChains(driver).move_to_element(dropdown_area).click().perform()
        time.sleep(1)
        opts = driver.find_elements(By.XPATH, "//div[@role='option']")
        for o in opts:
            if option_text.lower() in o.text.lower():
                ActionChains(driver).move_to_element(o).click().perform()
                time.sleep(0.5)
                return True
        print(f"[❗] Option '{option_text}' not found for '{label_text}'")
        return False
    except Exception as e:
        print(f"[Dropdown ERROR] {label_text}: {e}")
        return False


def fill_and_submit(form_url, parsed):
    options = Options()
    options.add_argument("--start-maximized")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(form_url)
    time.sleep(3)

    # ==== Dropdown select ====
    force_click_dropdown(driver, "Outlet Code", "C013")
    force_click_dropdown(driver, "Outlet Name", "Cumilla badurtola")

    # ==== Fill inputs ====
    inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="date"], textarea')

    def safe_fill(idx, val):
        try:
            if idx < len(inputs):
                el = inputs[idx]
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                el.click()
                el.clear()
                el.send_keys(val)
                return True
        except Exception as e:
            print("Fill error:", e)
        return False

    # ==== Date in mm/dd/yy format ====
    order_date = datetime.now().strftime("%m/%d/%y")
    order_number = parsed['order_number']
    address = parsed['address']
    cost = parsed['cost']
    km = parsed['km']
    reason = f"E.Com delivery point is {km} km far from outlet" if km else ""

    # ==== Fill fields ====
    try:
        date_field = driver.find_element(By.XPATH, "//input[@type='date']")
        date_field.send_keys(order_date)
    except:
        try:
            date_field = driver.find_element(By.XPATH, "(//input[contains(@aria-label,'Date') or contains(@aria-label,'তারিখ')])[1]")
            driver.execute_script("arguments[0].value = arguments[1];", date_field, order_date)
        except:
            print("⚠️ Could not fill date")

    safe_fill(1, order_number)
    safe_fill(2, address)
    safe_fill(3, cost)
    safe_fill(4, reason)
    safe_fill(5, "")

    # ==== Vehicle Type ====
    force_click_dropdown(driver, "Vehicle Type", "Rickshaw")

    # ==== Scroll down to ensure Note/Remarks field loads ====
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # ==== Note / Remarks - IMPROVED DETECTION ====
    try:
        note_field = None
        
        # Method 1: Find by aria-label
        try:
            note_field = driver.find_element(By.XPATH, "//textarea[contains(@aria-label, 'Note') or contains(@aria-label, 'Remarks') or contains(@aria-label, 'নোট') or contains(@aria-label, 'মন্তব্য')]")
        except:
            pass
        
        # Method 2: Find by parent label text
        if not note_field:
            try:
                note_field = driver.find_element(By.XPATH, "//div[contains(text(), 'Note') or contains(text(), 'Remarks') or contains(text(), 'নোট') or contains(text(), 'মন্তব্য')]/ancestor::div[@role='listitem']//textarea")
            except:
                pass
        
        # Method 3: Find all textareas and check their labels
        if not note_field:
            all_textareas = driver.find_elements(By.XPATH, "//textarea")
            for textarea in all_textareas:
                parent = textarea.find_element(By.XPATH, "./ancestor::div[@role='listitem']")
                label_text = parent.text.lower()
                if any(x in label_text for x in ["note", "remarks", "নোট", "মন্তব্য"]):
                    note_field = textarea
                    break

        if note_field:
            driver.execute_script("arguments[0].scrollIntoView(true);", note_field)
            time.sleep(1)
            
            # Click and clear
            note_field.click()
            time.sleep(0.3)
            note_field.clear()
            time.sleep(0.3)
            
            # Fill with text
            note_text = f"{km} km distance confirmed."
            note_field.send_keys(note_text)
            time.sleep(0.5)
            
            print("✅ Note/Remarks filled successfully.")
        else:
            print("⚠️ Note/Remarks field not found on the form.")

    except Exception as e:
        print("⚠️ Note/Remarks fill error:", e)

    # ==== Auto Submit ====
    try:
        time.sleep(2)
        submit_button = driver.find_element(
            By.XPATH, "//span[contains(text(),'Submit') or contains(text(),'জমা দিন') or contains(text(),'Send')]/ancestor::div[@role='button']"
        )
        ActionChains(driver).move_to_element(submit_button).click().perform()
        print("✅ Form submitted successfully!")
    except Exception as e:
        print("⚠️ Submit error:", e)

    # ==== Screenshot save ====
    time.sleep(2)
    ss_path = os.path.join(os.getcwd(), f"form_submit_{order_number}.png")
    driver.save_screenshot(ss_path)
    driver.quit()
    return ss_path


@bot.message_handler(commands=['start', 'help'])
def help_msg(message):
    bot.reply_to(message,
        "📤 উদাহরণ:\n"
        "Order: 12345, Address: Cumilla sadar, Cost: 120, KM: 5\n\n"
        "আমি অটো ফর্ম ফিল করে সাবমিট করব।"
    )


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    parsed = parse_message(message.text)
    order_id = parsed.get('order_number')

    if not order_id:
        bot.reply_to(message, "⚠️ Order number দিতে ভুলে গেছো।")
        return

    if order_id in submitted_orders:
        bot.reply_to(message, f"⚠️ Order {order_id} আগেই সাবমিট হয়েছে!")
        return

    msg = bot.reply_to(message, "⏳ ফর্ম সাবমিট হচ্ছে...")

    try:
        screenshot = fill_and_submit(FORM_URL, parsed)
        submitted_orders.add(order_id)
        with open(screenshot, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption=f"✅ Order {order_id} সফলভাবে সাবমিট হয়েছে।")
        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        bot.delete_message(message.chat.id, msg.message_id)
        bot.reply_to(message, f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Bot running...")
    bot.polling(none_stop=True)
