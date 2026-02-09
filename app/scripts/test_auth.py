# scripts/test_auth.py
import requests
import json

BASE_URL = "http://localhost:8000"


def test_auth_endpoints():
    """تست endpoints احراز هویت."""

    print("🧪 تست Authentication API")
    print("=" * 50)

    # ۱. تست ثبت نام
    print("\n1. تست ثبت نام:")
    register_data = {
        "first_name": "نمونه",
        "last_name": "کاربر",
        "student_number": "4001234567",
        "national_code": "0123456789",
        "phone_number": "09123456789",
        "gender": "sister",
        "address": "تهران"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

    # ۲. تست ورود
    print("\n2. تست ورود:")
    login_data = {
        "username": "0123456789",
        "password": "4001234567"
    }

    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"   ✅ ورود موفق - توکن دریافت شد")
        # ذخیره توکن برای تست‌های بعدی
        headers = {"Authorization": f"Bearer {token}"}

        # ۳. تست دریافت اطلاعات کاربر
        print("\n3. تست دریافت اطلاعات کاربر:")
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   User Info: {response.json()}")

        # ۴. تست بررسی شماره دانشجویی
        print("\n4. تست بررسی شماره دانشجویی:")
        response = requests.get(f"{BASE_URL}/auth/check/4001234567")
        print(f"   Available: {response.json()['available']}")

    else:
        print(f"   ❌ ورود ناموفق: {response.json()}")


if __name__ == "__main__":
    test_auth_endpoints()