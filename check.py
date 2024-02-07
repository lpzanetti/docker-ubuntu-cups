import time
import os
import requests
import subprocess
import cups
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Define the folder to monitor and the API URL
folder_to_watch = "/var/spool/cups-pdf/ANONYMOUS"  # Replace with your folder path

# Define the path for the lock file
lock_file_path = "/pdfinfo_script2.lock"  # Adjust the path as needed

# Variables to track script termination
terminate_requested = False

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(".pdf"):
            pdf_filename = os.path.basename(event.src_path)
            time.sleep(10)
            pdf_pages = get_pdf_page_count(event.src_path)
            max_pages = get_max_pages_from_api()

            print(f"PDF File: {pdf_filename}")
            print(f"Number of Pages: {pdf_pages}")
            print(f"Max Pages from API: {max_pages}")

            if pdf_pages <= max_pages:
                print("PDF pages are within the allowed limit.")
                data = action_from_api("http://sistemas.fca.unesp.br/sistemas/imprime/api.php?local=1&at=2&pags="+str(pdf_pages))
                if data['status'] == 'ok':
                    cups_server = cups.Connection()
                    cups_server.printFile('Mono',folder_to_watch+'/'+pdf_filename,'',{})
                    print("OK "+pdf_filename)
                    #clear_folder_contents(folder_to_watch)
                    #terminate_script()
                    mainscript()
            else:
                print("PDF pages exceed the allowed limit.")
                clear_folder_contents(folder_to_watch)
                data = action_from_api("http://sistemas.fca.unesp.br/sistemas/imprime/api.php?local=1&at=4&msg=4")
                if data['status'] == 'ok':
                    mainscript()
def wait_for_file_stable(pdf_file, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        initial_mtime = os.path.getmtime(pdf_file)
        time.sleep(1)  # Wait for 1 second
        current_mtime = os.path.getmtime(pdf_file)
        if current_mtime == initial_mtime:
            return True
    return False

def get_pdf_page_count(pdf_file):
    if wait_for_file_stable(pdf_file):
        try:
            resbytes = subprocess.check_output(["pdfinfo", pdf_file], stderr=subprocess.STDOUT)
            result = resbytes.decode('utf-8')
            page_count_line = [line for line in result.split('\n') if line.startswith("Pages:")]
            if page_count_line:
                page_count = int(page_count_line[0].split(":")[1].strip())
                return page_count
            else:
                print("Page count information not found in pdfinfo output.")
                return None
        except subprocess.CalledProcessError as e:
            print(f"Error running pdfinfo: {e}")
            return None
    else:
        print("PDF file did not stabilize within the specified timeout.")
        return None

def get_max_pages_from_api():
    response = requests.get("http://sistemas.fca.unesp.br/sistemas/imprime/api.php?local=1&at=1")
    if response.status_code == 200:
        data = response.json()
        if 'pags' in data and data['pags']:
            return data['pags']
        else:
            mainscript()
    else:
        mainscript()

def action_from_api(url):
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data
        else:
            mainscript()
    else:
        mainscript()

def clear_folder_contents(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error while deleting file: {e}")

def check_lock_file():
    if os.path.exists(lock_file_path):
        return True
    return False

def create_lock_file():
    with open(lock_file_path, "w") as lock_file:
        lock_file.write("Lock")

def remove_lock_file():
    if os.path.exists(lock_file_path):
        os.remove(lock_file_path)

def terminate_script():
    global terminate_requested
    terminate_requested = True

def mainscript():
    print("Iniciando Cota")
    #create_lock_file()
    clear_folder_contents(folder_to_watch)  # Clear existing files in the folder
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, path=folder_to_watch, recursive=False)
    observer.start()

    try:
        while not terminate_requested:
            time.sleep(5)  # Check every 5 seconds for new PDF files
    except KeyboardInterrupt:
        pass  # Allow script termination via Ctrl+C
    finally:
        pass
        #remove_lock_file()

if __name__ == "__main__":
    mainscript()
        