import requests
import time
import sys

def test_health():
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Health Check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health Check Failed: {e}")

def test_translation_flow():
    try:
        # 1. Upload
        print("Uploading file...")
        files = {'file': ('test.txt', 'This is a test content for translation.')}
        response = requests.post(
            "http://localhost:8000/api/v1/translation/upload",
            params={"target_lang": "FR"},
            files=files
        )
        print(f"Upload Response: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
            return

        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"Job ID: {job_id}")

        # 2. Poll Status
        print("Polling status...")
        for _ in range(30):  # Wait up to 30 seconds
            status_res = requests.get(f"http://localhost:8000/api/v1/translation/jobs/{job_id}")
            if status_res.status_code != 200:
                print(f"Status Check Failed: {status_res.status_code}")
                break
            
            status_data = status_res.json()
            status = status_data["status"]
            print(f"Status: {status}")
            
            if status == "completed":
                print(f"Translation Completed! Output: {status_data.get('output_location')}")
                return
            elif status == "failed":
                print(f"Translation Failed: {status_data.get('error')}")
                return
            
            time.sleep(1)
        
        print("Timeout waiting for translation.")

    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    test_health()
    test_translation_flow()
