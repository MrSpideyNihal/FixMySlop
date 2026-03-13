"""
Test bait — maximum AI slop for FixMySlop testing.
Every bad pattern known to mankind.
"""
import os
import sys
import pickle
import hashlib
import sqlite3
import subprocess
import requests
import json
import threading
import time

# ❌ Hardcoded secrets everywhere
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "admin123"
SECRET_TOKEN = "ghp_realtoken123456"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA2a2rwplBQLF29amygykEMmYz0+Iqb"

# ❌ Global mutable state
users_cache = []
admin_sessions = {}
db_connection = None

class UserManager:
    def __init__(self):
        # ❌ Hardcoded DB path, no error handling
        self.conn = sqlite3.connect("C:\\users\\admin\\secret.db")
        self.cursor = self.conn.cursor()

    def get_user(self, user_id):
        # ❌ SQL injection — string concatenation in query
        query = "SELECT * FROM users WHERE id = " + user_id
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def login(self, username, password):
        # ❌ Plaintext password comparison
        # ❌ SQL injection
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        self.cursor.execute(query)
        user = self.cursor.fetchone()
        # ❌ Returns True even if user is None
        return True

    def delete_user(self, username):
        # ❌ No authentication check before delete
        # ❌ SQL injection
        self.cursor.execute("DELETE FROM users WHERE username = '" + username + "'")
        self.conn.commit()

    def update_password(self, user_id, new_password):
        # ❌ MD5 hashing (broken)
        # ❌ No salt
        hashed = hashlib.md5(new_password.encode()).hexdigest()
        self.cursor.execute(f"UPDATE users SET password='{hashed}' WHERE id={user_id}")

    def get_all_users(self):
        # ❌ Returns entire table including passwords
        self.cursor.execute("SELECT * FROM users")
        return self.cursor.fetchall()


class FileManager:
    def read_file(self, path):
        # ❌ No encoding specified
        # ❌ File never closed
        # ❌ No error handling
        f = open(path)
        return f.read()

    def write_file(self, path, data):
        # ❌ File never closed
        # ❌ Overwrites without backup
        f = open(path, "w")
        f.write(data)

    def delete_file(self, path):
        # ❌ No confirmation, no backup
        # ❌ Shell injection possible
        os.system("del " + path)

    def execute_file(self, path):
        # ❌ Arbitrary code execution
        # ❌ shell=True is dangerous
        subprocess.run(path, shell=True)

    def load_config(self, path):
        # ❌ Unsafe pickle load from file
        with open(path, "rb") as f:
            return pickle.load(f)

    def save_config(self, path, data):
        # ❌ Unsafe pickle dump
        with open(path, "wb") as f:
            pickle.dump(data, f)


class NetworkManager:
    def fetch(self, url):
        # ❌ SSL verification disabled
        # ❌ No timeout
        # ❌ No error handling
        response = requests.get(url, verify=False)
        return response.json()

    def post_data(self, url, data):
        # ❌ Sensitive data in URL params
        # ❌ No error handling
        # ❌ SSL disabled
        requests.post(
            url + "?api_key=" + API_KEY + "&token=" + SECRET_TOKEN,
            data=data,
            verify=False
        )

    def download(self, url, path):
        # ❌ No validation of downloaded content
        # ❌ Path traversal possible
        # ❌ No size limit
        response = requests.get(url, verify=False)
        open(path, "wb").write(response.content)

    def send_email(self, to, subject, body):
        # ❌ Hardcoded SMTP credentials
        import smtplib
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.login("admin@company.com", "supersecretpassword123")
        server.sendmail("admin@company.com", to, body)


class DataProcessor:
    def process(self, data):
        # ❌ Unsafe eval on user input
        result = eval(data)
        return result

    def execute_command(self, cmd):
        # ❌ Direct OS command execution
        # ❌ No sanitization
        return os.system(cmd)

    def deserialize(self, data):
        # ❌ Unsafe pickle deserialization
        return pickle.loads(data)

    def parse_xml(self, xml_string):
        # ❌ XXE injection vulnerability
        import xml.etree.ElementTree as ET
        return ET.fromstring(xml_string)

    def run_query(self, user_input):
        # ❌ Direct eval of user input as Python
        # ❌ SQL injection
        conn = sqlite3.connect(":memory:")
        conn.execute("SELECT * FROM data WHERE value = '" + user_input + "'")

    def process_users(self, users):
        # ❌ O(n³) — triple nested loop
        result = []
        for a in users:
            for b in users:
                for c in users:
                    if a["id"] != b["id"] != c["id"]:
                        result.append((a, b, c))
        return result

    def load_and_process(self, file_path):
        # ❌ No error handling on file or json
        data = open(file_path).read()
        parsed = json.loads(data)
        # ❌ No validation of parsed data
        return eval(parsed["command"])


class ThreadingNightmare:
    def __init__(self):
        # ❌ Shared mutable state with no locks
        self.counter = 0
        self.data = []

    def increment(self):
        # ❌ Race condition — not thread safe
        temp = self.counter
        time.sleep(0)
        self.counter = temp + 1

    def add_data(self, item):
        # ❌ Race condition on list
        self.data.append(item)

    def run_all(self, tasks):
        # ❌ Unlimited threads — resource exhaustion
        threads = []
        for task in tasks:
            t = threading.Thread(target=task)
            t.start()
            threads.append(t)
        # ❌ No join — threads abandoned


class ErrorHandlingNightmare:
    def divide(self, a, b):
        # ❌ Division by zero not handled
        return a / b

    def get_item(self, lst, index):
        # ❌ Index out of bounds not handled
        return lst[index]

    def parse_int(self, value):
        # ❌ Bare except swallows all errors
        try:
            return int(value)
        except:
            pass

    def connect_db(self):
        # ❌ Exception ignored silently
        try:
            conn = sqlite3.connect("production.db")
            return conn
        except Exception:
            return None

    def read_config(self):
        # ❌ Catches and ignores ALL exceptions
        # ❌ Returns hardcoded fallback with secrets
        try:
            with open("config.json") as f:
                return json.load(f)
        except:
            return {"api_key": "sk-fallback-hardcoded-key", "debug": True}


# ❌ Massive function doing 10 things
def do_everything(user_input, file_path, url, db_path):
    os.system("echo " + user_input)
    conn = sqlite3.connect(db_path)
    conn.execute("SELECT * FROM users WHERE name='" + user_input + "'")
    data = pickle.load(open(file_path, "rb"))
    result = eval(user_input)
    response = requests.get(url, verify=False)
    hashed = hashlib.md5(user_input.encode()).hexdigest()
    subprocess.run(user_input, shell=True)
    open(file_path).read()
    return result, data, response, hashed


# ❌ Dead code graveyard
def unused_one(): pass
def unused_two(): pass
def unused_three(): pass
def unused_four(): pass

def almost_used():
    x = 1
    y = 2
    z = 3
    w = 4
    # None of these are returned or used
    result = x + y