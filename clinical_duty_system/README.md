# Clinical Duty Scheduling and Patient Case Assignment System

This Django web application is based on your System Analysis and Design document:

- Role-based users: Admin, Clinical Instructor, Student
- Duty schedule management
- Patient case assignment
- Clinical area management
- Notification feed
- Duty history and case exposure tracking
- MySQL database support for XAMPP

## 1. Software to install

1. Python 3.11+
2. XAMPP (Apache + MySQL)
3. VS Code or any code editor
4. pip

## 2. Create the MySQL database in XAMPP

1. Start **Apache** and **MySQL** in XAMPP Control Panel.
2. Open **phpMyAdmin**.
3. Create a database named:

```sql
CREATE DATABASE clinical_duty_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 3. Create virtual environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Install dependencies

```bash
pip install -r requirements.txt
```

If `mysqlclient` fails on Windows, install:

```bash
pip install mysqlclient
```

If that still fails, install Microsoft C++ Build Tools or use:

```bash
pip install PyMySQL
```

Then add this at the top of `clinical_duty_system/__init__.py`:

```python
import pymysql
pymysql.install_as_MySQLdb()
```

## 5. Configure environment variables

Copy `.env.example` to `.env` and update values if needed.

Example:

```env
DJANGO_SECRET_KEY=super-secret-key
DJANGO_DEBUG=True
MYSQL_DATABASE=clinical_duty_db
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

## 6. Run migrations

```bash
python manage.py makemigrations accounts scheduling
python manage.py migrate
```

## 7. Create admin account

```bash
python manage.py createsuperuser
```

## 8. Run the server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## 9. Suggested first data setup

1. Log in as superuser
2. Open `/admin/`
3. Create users for instructors and students
4. Edit each user's Profile and assign roles
5. Create Clinical Areas
6. Log in as Instructor and create schedules
7. Assign patient cases

## 10. Main features included

### Admin
- Manage users through Django admin
- Manage clinical areas
- View dashboard summary

### Instructor
- Create and update duty schedules
- Assign patient cases
- Generate notifications for students
- Automatically add case exposure to duty history

### Student
- View personal schedules
- View assigned patient cases
- View notifications
- Update own profile

## 11. Important notes

- This is a **good thesis/demo starter system**.
- For production use, add stronger validation, audit logs, email notifications, REST APIs, and better permissions.
- You can improve the UI using Bootstrap later if your professor allows it.

## 12. Possible next upgrades

- Search and filter schedules
- Export duty reports to PDF
- SMS or email alerts
- Attendance checking
- Instructor approval workflow
- Charts for case exposure analytics
