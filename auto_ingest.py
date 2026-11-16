import time
import re
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.pdf'):
            return
            
        pdf_path = event.src_path
        print(f"New PDF detected: {pdf_path}")
        
        # Example: Extract metadata from a strict naming convention 
        # File format expectation: "Vol1_SecB_ITT.pdf"
        match = re.search(r'Vol(\d+)_Sec([A-Z0-9_a-z]+)', pdf_path)
        
        if match:
            volume = match.group(1)
            section = match.group(2)
            title = f"Auto-ingested Section {section}"
            
            print(f"Triggering pipeline for Volume {volume}, Section {section}...")
            
            # Dynamically fire your CLI command
            subprocess.run([
                "bmrcl-pipeline", "process",
                "--pdf", pdf_path,
                "--volume", volume,
                "--section", section,
                "--title", title
            ])
        else:
            print(f"Filename {pdf_path} does not match expected VolX_SecY convention. Skipping.")

if __name__ == "__main__":
    folder_to_watch = "data/BMRCL_TenderData"
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()
    
    print(f"Listening for new PDFs in {folder_to_watch}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()